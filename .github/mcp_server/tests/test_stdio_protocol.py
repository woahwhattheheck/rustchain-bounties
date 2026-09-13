import json
import subprocess
import sys
import time
import unittest
from pathlib import Path


MCP_ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
