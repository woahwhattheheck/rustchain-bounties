#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import contextlib
import importlib.util
import io
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "bounty_payout_checked.py"
spec = importlib.util.spec_from_file_location("bounty_payout_checked_test", SCRIPT)
checked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checked)


class _FakeProcess:
    def __init__(self, lines, status):
        self.stdout = iter(lines)
        self._status = status

    def wait(self):
        return self._status


class CheckedPayoutRunnerTests(unittest.TestCase):
    def _run(self, lines, status=0):
        calls = []

        def fake_popen(command, **kwargs):
            calls.append((command, kwargs))
            return _FakeProcess(lines, status)

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            result = checked.run_checked(["python", "fake-payout.py"], popen=fake_popen)
        return result, stream.getvalue(), calls

    def test_clean_sweep_stays_green(self):
        result, output, calls = self._run([
            "bounty-payout: 0 candidate issues (0 label-eligible, 0 from recent window)\n",
            "bounty-payout: paid 0 claims = 0 RTC this run\n",
        ])
        self.assertEqual(result, 0)
        self.assertNotIn("::error::bounty payout", output)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["stderr"], subprocess.STDOUT)

    def test_detected_transfer_failure_fails_only_after_sweep(self):
        result, output, _ = self._run([
            "::warning::pay failed #101: server_declined:{'ok': False}\n",
            "paid later independent claim #102\n",
            "bounty-payout: paid 1 claims = 3 RTC this run\n",
        ])
        self.assertEqual(result, 1)
        self.assertIn("paid later independent claim #102", output)
        self.assertIn("1 failed transfer(s): #101", output)

    def test_multiple_failures_are_retained_and_deduplicated(self):
        result, output, _ = self._run([
            "::warning::pay failed #9: timeout\n",
            "::warning::pay failed #11: refused\n",
            "::warning::pay failed #9: timeout\n",
        ])
        self.assertEqual(result, 1)
        self.assertIn("2 failed transfer(s): #9, #11", output)

    def test_existing_child_failure_is_preserved(self):
        result, output, _ = self._run([
            "::error::GitHub discovery failed\n",
        ], status=7)
        self.assertEqual(result, 7)
        self.assertNotIn("failed transfer(s)", output)


if __name__ == "__main__":
    unittest.main()
