#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression tests for atomic-ish docstring payable-state publication."""
import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("GITHUB_TOKEN", "dummy")
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "docstring_gate.py"
spec = importlib.util.spec_from_file_location("docstring_gate_payable_state", SCRIPT)
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)


class AdjudicatedStateTests(unittest.TestCase):
    def test_complete_payable_state_is_terminal(self):
        self.assertTrue(
            dg.is_already_adjudicated({"bounty-eligible", "docstring-verified"})
        )

    def test_partial_payable_state_remains_retryable(self):
        self.assertFalse(dg.is_already_adjudicated({"bounty-eligible"}))
        self.assertFalse(dg.is_already_adjudicated({"docstring-verified"}))
        self.assertFalse(dg.is_already_adjudicated({"needs-human"}))

    def test_legacy_gate_processed_state_remains_terminal(self):
        self.assertTrue(dg.is_already_adjudicated({"gate-processed"}))


class AddLabelsTests(unittest.TestCase):
    def setUp(self):
        self._run = dg.subprocess.run
        self._num = dg.NUM
        dg.NUM = "123"

    def tearDown(self):
        dg.subprocess.run = self._run
        dg.NUM = self._num

    def test_multiple_labels_share_one_rest_request(self):
        calls = []

        def fake_run(args, **_kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0, stderr="")

        dg.subprocess.run = fake_run

        self.assertTrue(dg.add_labels("bounty-eligible", "docstring-verified"))
        self.assertEqual(len(calls), 1)
        self.assertIn("labels[]=bounty-eligible", calls[0])
        self.assertIn("labels[]=docstring-verified", calls[0])


class CommitPayableStateTests(unittest.TestCase):
    def setUp(self):
        self._gh_raw = dg.gh_raw
        self._add_labels = dg.add_labels
        self._num = dg.NUM
        dg.NUM = "123"

    def tearDown(self):
        dg.gh_raw = self._gh_raw
        dg.add_labels = self._add_labels
        dg.NUM = self._num

    def test_marker_failure_never_applies_payable_labels(self):
        label_calls = []

        def fail_marker(_args):
            raise dg.GhError("comment write failed")

        def record_labels(*names):
            label_calls.append(names)
            return True

        dg.gh_raw = fail_marker
        dg.add_labels = record_labels

        self.assertFalse(dg.commit_payable_state(4.5))
        self.assertEqual(label_calls, [])

    def test_marker_is_published_before_payable_labels(self):
        events = []

        def record_marker(args):
            events.append(("marker", args[-1]))
            return "ok"

        def record_labels(*names):
            events.append(("labels", names))
            return True

        dg.gh_raw = record_marker
        dg.add_labels = record_labels

        self.assertTrue(dg.commit_payable_state(7.5))
        self.assertEqual(
            events,
            [
                ("marker", "<!-- rtc-payout-amount: 7.5 -->"),
                ("labels", ("bounty-eligible", "docstring-verified")),
            ],
        )

    def test_label_failure_holds_state_for_retry_without_hold_label(self):
        events = []

        def record_marker(args):
            events.append(("marker", args[-1]))
            return "ok"

        def fail_payable_labels(*names):
            events.append(("labels", names))
            return False

        dg.gh_raw = record_marker
        dg.add_labels = fail_payable_labels

        self.assertFalse(dg.commit_payable_state(2.0))
        self.assertEqual(
            events,
            [
                ("marker", "<!-- rtc-payout-amount: 2.0 -->"),
                ("labels", ("bounty-eligible", "docstring-verified")),
            ],
        )


if __name__ == "__main__":
    unittest.main()
