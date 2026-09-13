#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "confirm-pending.yml"
RUN_MARKER = "        run: |\n"


def workflow_script() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    if text.count(RUN_MARKER) != 1:
        raise AssertionError("expected exactly one run block in confirm-pending workflow")
    return textwrap.dedent(text.split(RUN_MARKER, 1)[1])


_FAKE_CURL = r'''#!/usr/bin/env python3
import json
import os
import pathlib
import sys

args = sys.argv[1:]
try:
    output = args[args.index("-o") + 1]
except (ValueError, IndexError):
    raise SystemExit("fake curl requires -o <path>")
responses = json.loads(pathlib.Path(os.environ["FAKE_RESPONSES"]).read_text())
state = pathlib.Path(os.environ["FAKE_STATE"])
index = int(state.read_text()) if state.exists() else 0
response = responses[index] if index < len(responses) else responses[-1]
pathlib.Path(output).write_text(json.dumps(response))
state.write_text(str(index + 1))
print(os.environ.get("FAKE_HTTP", "200"), end="")
'''


class ConfirmPendingWorkflowTests(unittest.TestCase):
    def _run(self, responses: list[dict], *, http: str = "200") -> subprocess.CompletedProcess[str]:
        script = workflow_script()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            curl = fake_bin / "curl"
            curl.write_text(_FAKE_CURL, encoding="utf-8")
            curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
            responses_path = root / "responses.json"
            responses_path.write_text(json.dumps(responses), encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
                    "RTC_VPS_HOST": "example.invalid",
                    "RTC_ADMIN_KEY": "test-only",
                    "FAKE_RESPONSES": str(responses_path),
                    "FAKE_STATE": str(root / "state"),
                    "FAKE_HTTP": http,
                }
            )
            return subprocess.run(
                ["bash", "-c", script],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )

    def test_run_block_is_valid_bash(self) -> None:
        result = subprocess.run(
            ["bash", "-n"],
            input=workflow_script(),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_already_drained_queue_is_green(self) -> None:
        result = self._run(
            [{"overdue_stats_measured": True, "confirmed_count": 0, "stale_pending_count": 0}]
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("queue drained", result.stdout)
        self.assertIn("confirmed 0 transfer(s) this run", result.stdout)

    def test_progress_then_drain_is_green(self) -> None:
        result = self._run(
            [
                {"overdue_stats_measured": True, "confirmed_count": 2, "stale_pending_count": 3},
                {"overdue_stats_measured": True, "confirmed_count": 3, "stale_pending_count": 0},
            ]
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("confirmed 5 transfer(s) this run", result.stdout)

    def test_measured_stale_with_zero_progress_is_red(self) -> None:
        result = self._run(
            [{"overdue_stats_measured": True, "confirmed_count": 0, "stale_pending_count": 7}]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pending queue stalled", result.stdout)
        self.assertNotIn("confirmed 0 transfer(s) this run", result.stdout)

    def test_unmeasurable_queue_is_red(self) -> None:
        result = self._run(
            [{"overdue_stats_measured": False, "confirmed_count": 0, "stale_pending_count": None}]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pending queue not measurable", result.stdout)

    def test_malformed_or_negative_counts_are_red(self) -> None:
        for response in (
            {"overdue_stats_measured": True, "confirmed_count": "0", "stale_pending_count": 7},
            {"overdue_stats_measured": True, "confirmed_count": 1, "stale_pending_count": -1},
        ):
            with self.subTest(response=response):
                result = self._run([response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Pending queue response invalid", result.stdout)

    def test_http_failure_is_red(self) -> None:
        result = self._run(
            [{"overdue_stats_measured": True, "confirmed_count": 0, "stale_pending_count": 0}],
            http="503",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("confirm HTTP 503", result.stdout)

    def test_safety_cap_with_stale_backlog_is_red(self) -> None:
        result = self._run(
            [{"overdue_stats_measured": True, "confirmed_count": 1, "stale_pending_count": 1}]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("iter 60:", result.stdout)
        self.assertIn("Pending queue safety cap reached", result.stdout)
        self.assertNotIn("confirmed 60 transfer(s) this run", result.stdout)


if __name__ == "__main__":
    unittest.main()
