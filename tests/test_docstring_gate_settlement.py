#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression tests for docstring gate payout-state commit ordering."""
import importlib.util
import os
import unittest
from pathlib import Path

os.environ.setdefault("GITHUB_TOKEN", "dummy")
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "docstring_gate.py"
spec = importlib.util.spec_from_file_location("docstring_gate_settlement_under_test", SCRIPT)
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)


class SettlementOrderingTests(unittest.TestCase):
    def setUp(self):
        self.old_num = dg.NUM
        self.old_repo = dg.REPO
        self.old_gh = dg.gh
        self.old_gh_raw = dg.gh_raw
        self.old_add_labels = dg.add_labels
        self.old_week = dg.docstring_rtc_this_week
        dg.NUM = "123"
        dg.REPO = "Scottcjn/rustchain-bounties"
        dg.gh_raw = lambda args: (
            "diff --git a/pkg.py b/pkg.py\n"
            "--- a/pkg.py\n"
            "+++ b/pkg.py\n"
            "@@ -1 +1,2 @@\n"
            "+    \"\"\"Documented.\"\"\"\n"
        )
        dg.docstring_rtc_this_week = lambda author: 0.0

    def tearDown(self):
        dg.NUM = self.old_num
        dg.REPO = self.old_repo
        dg.gh = self.old_gh
        dg.gh_raw = self.old_gh_raw
        dg.add_labels = self.old_add_labels
        dg.docstring_rtc_this_week = self.old_week

    @staticmethod
    def _base_response(args, default=None):
        if args[:2] == ["issue", "view"]:
            return {
                "title": "Bounty claim: docstring batch",
                "body": "PR: https://github.com/example/project/pull/7",
                "labels": [],
                "author": {"login": "claimant"},
                "state": "OPEN",
            }
        if args[:2] == ["pr", "view"]:
            return {"state": "MERGED"}
        return default

    def test_marker_write_failure_prevents_terminal_labels(self):
        label_calls = []

        def fake_gh(args, default=None, strict=False):
            base = self._base_response(args, default)
            if base is not default:
                return base
            if args[:2] == ["issue", "comment"]:
                body = args[args.index("--body") + 1]
                if "rtc-payout-amount" in body:
                    self.assertTrue(strict, "money marker write must be strict")
                    raise dg.GhError("simulated comment outage")
                return default
            return default

        dg.gh = fake_gh
        dg.add_labels = lambda *names: label_calls.append(names) or True

        self.assertEqual(dg.main(), 1)
        self.assertEqual(label_calls, [], "terminal labels must not precede the amount marker")

    def test_amount_marker_is_durable_before_payable_labels(self):
        events = []

        def fake_gh(args, default=None, strict=False):
            base = self._base_response(args, default)
            if base is not default:
                return base
            if args[:2] == ["issue", "comment"]:
                body = args[args.index("--body") + 1]
                if "rtc-payout-amount" in body:
                    self.assertTrue(strict, "money marker write must be strict")
                    events.append("marker")
                else:
                    events.append("informational-comment")
                return default
            return default

        def fake_add_labels(*names):
            events.append("labels")
            return True

        dg.gh = fake_gh
        dg.add_labels = fake_add_labels

        self.assertEqual(dg.main(), 0)
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[:2], ["marker", "labels"])


if __name__ == "__main__":
    unittest.main()
