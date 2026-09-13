import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from rustchain_mcp import server


MCP_ROOT = Path(__file__).resolve().parents[1]


class TransferAmountTests(unittest.TestCase):
    def test_invalid_transfer_amounts_fail_before_wallet_post(self):
        client = server.RustChainClient("https://example.invalid")
        arguments = {
            "from_wallet": "source",
            "to_wallet": "destination",
            "admin_key": "test-key",
        }
        with patch.object(client, "_post") as post, patch.object(server, "_client", client):
            for amount in (float("nan"), float("inf"), float("-inf"), 0, -1, True, "1"):
                with self.subTest(amount=amount):
                    result = server.handle_tool("rustchain_transfer", {**arguments, "amount": amount})
                    self.assertFalse(result["ok"])
                    self.assertIn("finite positive number", result["error"])
            post.assert_not_called()

    def test_positive_finite_transfer_amount_reaches_wallet_post_unchanged(self):
        client = server.RustChainClient("https://example.invalid")
        with patch.object(client, "_post", return_value={"ok": True}) as post, patch.object(server, "_client", client):
            result = server.handle_tool("rustchain_transfer", {
                "from_wallet": "source",
                "to_wallet": "destination",
                "amount": 1.25,
                "admin_key": "test-key",
            })
        self.assertEqual({"ok": True}, result)
        post.assert_called_once_with("/wallet/send", {
            "from_wallet": "source",
            "to_wallet": "destination",
            "amount": 1.25,
            "admin_key": "test-key",
        })

    def test_huge_positive_integer_reaches_wallet_post_unchanged(self):
        client = server.RustChainClient("https://example.invalid")
        amount = 10 ** 400
        with patch.object(client, "_post", return_value={"ok": True}) as post, patch.object(server, "_client", client):
            result = server.handle_tool("rustchain_transfer", {
                "from_wallet": "source",
                "to_wallet": "destination",
                "amount": amount,
                "admin_key": "test-key",
            })
        self.assertEqual({"ok": True}, result)
        post.assert_called_once_with("/wallet/send", {
            "from_wallet": "source",
            "to_wallet": "destination",
            "amount": amount,
            "admin_key": "test-key",
        })


class QueryArgumentValidationTests(unittest.TestCase):
    def test_schema_declares_query_argument_constraints(self):
        tools = {tool["name"]: tool for tool in server.MCP_TOOL_SCHEMA["tools"]}
        self.assertEqual(
            1,
            tools["rustchain_miners"]["inputSchema"]["properties"]["limit"]["minimum"],
        )
        bounty_properties = tools["rustchain_bounties"]["inputSchema"]["properties"]
        self.assertEqual(1, bounty_properties["limit"]["minimum"])
        self.assertEqual(["open", "closed", "all"], bounty_properties["status"]["enum"])

    def test_invalid_miner_limits_fail_before_get(self):
        client = server.RustChainClient("https://example.invalid")
        with patch.object(client, "_get") as get, patch.object(server, "_client", client):
            for limit in (0, -1, True, 1.5, "2", None):
                with self.subTest(limit=limit):
                    result = server.handle_tool("rustchain_miners", {"limit": limit})
                    self.assertFalse(result["ok"])
                    self.assertIn("positive integer", result["error"])
            get.assert_not_called()

    def test_invalid_bounty_status_or_limit_fails_before_get(self):
        client = server.RustChainClient("https://example.invalid")
        cases = (
            {"status": "pending", "limit": 20},
            {"status": 7, "limit": 20},
            {"status": "open", "limit": 0},
            {"status": "all", "limit": True},
        )
        with patch.object(client, "_get") as get, patch.object(server, "_client", client):
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    result = server.handle_tool("rustchain_bounties", arguments)
                    self.assertFalse(result["ok"])
            get.assert_not_called()

    def test_valid_query_arguments_reach_get_unchanged(self):
        client = server.RustChainClient("https://example.invalid")
        with patch.object(client, "_get", return_value={"ok": True}) as get, patch.object(server, "_client", client):
            self.assertEqual({"ok": True}, server.handle_tool("rustchain_miners", {"limit": 7}))
            get.assert_called_once_with("/miners/list", {"limit": 7})
            get.reset_mock()
            self.assertEqual(
                {"ok": True},
                server.handle_tool("rustchain_bounties", {"status": "closed", "limit": 9}),
            )
            get.assert_called_once_with("/bounties/list", {"status": "closed", "limit": 9})


class StdioProtocolTests(unittest.TestCase):
    def test_server_is_silent_until_client_sends_request(self):
        process = subprocess.Popen(
            [sys.executable, "-m", "rustchain_mcp.server"],
            cwd=MCP_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            time.sleep(0.2)
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)

        self.assertEqual("", stdout)
        self.assertEqual("", stderr)

    def test_initialize_emits_one_response_with_exact_request_id(self):
        request = {
            "jsonrpc": "2.0",
            "id": "initialize-17",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "offline-regression", "version": "1"},
            },
        }
        completed = subprocess.run(
            [sys.executable, "-m", "rustchain_mcp.server"],
            cwd=MCP_ROOT,
            input=json.dumps(request) + "\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        lines = completed.stdout.splitlines()
        self.assertEqual(1, len(lines), completed.stdout)
        response = json.loads(lines[0])
        self.assertEqual("2.0", response["jsonrpc"])
        self.assertEqual("initialize-17", response["id"])
        self.assertEqual("2024-11-05", response["result"]["protocolVersion"])
        self.assertEqual("rustchain-mcp", response["result"]["serverInfo"]["name"])
        self.assertEqual("", completed.stderr)

    def test_malformed_frame_does_not_reuse_previous_request_id(self):
        first = {
            "jsonrpc": "2.0",
            "id": "first-request",
            "method": "initialize",
            "params": {},
        }
        completed = subprocess.run(
            [sys.executable, "-m", "rustchain_mcp.server"],
            cwd=MCP_ROOT,
            input=json.dumps(first) + "\n{not-json\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        lines = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(2, len(lines), completed.stdout)
        self.assertEqual("first-request", lines[0]["id"])
        self.assertIsNone(lines[1]["id"])
        self.assertEqual(-32700, lines[1]["error"]["code"])
        self.assertEqual("Parse error", lines[1]["error"]["message"])
        self.assertEqual("", completed.stderr)

    def test_invalid_request_shapes_get_invalid_request_errors(self):
        invalid_frames = [
            "[]",
            "{}",
            json.dumps({"jsonrpc": "1.0", "id": 7, "method": "initialize"}),
            json.dumps({"jsonrpc": "2.0", "id": 8, "method": 17}),
        ]
        completed = subprocess.run(
            [sys.executable, "-m", "rustchain_mcp.server"],
            cwd=MCP_ROOT,
            input="\n".join(invalid_frames) + "\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        lines = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(4, len(lines), completed.stdout)
        for response in lines:
            self.assertIsNone(response["id"])
            self.assertEqual(-32600, response["error"]["code"])
            self.assertEqual("Invalid Request", response["error"]["message"])
        self.assertEqual("", completed.stderr)

    def test_known_method_notification_is_processed_without_response(self):
        notification = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
        }
        completed = subprocess.run(
            [sys.executable, "-m", "rustchain_mcp.server"],
            cwd=MCP_ROOT,
            input=json.dumps(notification) + "\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        self.assertEqual("", completed.stdout)
        self.assertEqual("", completed.stderr)

    def test_null_request_id_is_not_treated_as_notification(self):
        request = {
            "jsonrpc": "2.0",
            "id": None,
            "method": "initialize",
            "params": {},
        }
        completed = subprocess.run(
            [sys.executable, "-m", "rustchain_mcp.server"],
            cwd=MCP_ROOT,
            input=json.dumps(request) + "\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        lines = completed.stdout.splitlines()
        self.assertEqual(1, len(lines), completed.stdout)
        response = json.loads(lines[0])
        self.assertIn("id", response)
        self.assertIsNone(response["id"])
        self.assertIn("result", response)

    def test_unknown_request_gets_method_not_found_but_notification_stays_silent(self):
        request = {"jsonrpc": "2.0", "id": 17, "method": "unknown/method"}
        notification = {"jsonrpc": "2.0", "method": "unknown/method"}
        completed = subprocess.run(
            [sys.executable, "-m", "rustchain_mcp.server"],
            cwd=MCP_ROOT,
            input=json.dumps(request) + "\n" + json.dumps(notification) + "\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        lines = completed.stdout.splitlines()
        self.assertEqual(1, len(lines), completed.stdout)
        response = json.loads(lines[0])
        self.assertEqual(17, response["id"])
        self.assertEqual(-32601, response["error"]["code"])
        self.assertEqual("", completed.stderr)


if __name__ == "__main__":
    unittest.main()
