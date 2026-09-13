#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression coverage for payout-pipeline audit findings reported in #16471."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewGateClaimReadTests(unittest.TestCase):
    def test_initial_claim_read_is_strict_and_cannot_green_noop(self):
        gate = load_module("pr_review_gate_16471", "scripts/pr_review_gate.py")
        gate.NUM = "123"
        gate.REPO = "Scottcjn/rustchain-bounties"
        calls = []

        def fake_api(path, method="GET", data=None, strict=False):
            calls.append((path, method, strict))
            if path == "/repos/Scottcjn/rustchain-bounties/issues/123":
                if strict:
                    raise gate.ApiError("simulated 403 on claim read")
                return None
            self.fail(f"gate advanced after failed claim read: {method} {path}")

        gate.api = fake_api
        with self.assertRaises(gate.ApiError):
            gate.main()

        self.assertEqual(
            calls,
            [("/repos/Scottcjn/rustchain-bounties/issues/123", "GET", True)],
        )


class DocstringGateOwnershipTests(unittest.TestCase):
    def test_claimant_cannot_collect_for_someone_elses_merged_pr(self):
        gate = load_module("docstring_gate_16471", "scripts/docstring_gate.py")
        gate.NUM = "456"
        gate.REPO = "Scottcjn/rustchain-bounties"
        labels = []
        comments = []
        diff_reads = []

        issue = {
            "title": "Docstring bounty claim",
            "body": (
                "PR: https://github.com/Scottcjn/Rustchain/pull/77\n"
                "Functions documented: 1"
            ),
            "labels": [],
            "author": {"login": "alice"},
            "state": "OPEN",
        }
        pr = {
            "state": "MERGED",
            "author": {"login": "bob"},
            "mergedAt": "2026-09-13T00:00:00Z",
            "files": [],
            "additions": 1,
            "deletions": 0,
        }

        def fake_gh(args, default=None, strict=False):
            if args[:2] == ["issue", "view"]:
                return issue
            if args[:2] == ["pr", "view"]:
                return pr
            if args[:2] == ["issue", "comment"]:
                comments.append(args[-1])
                return default
            self.fail(f"unexpected gh call before ownership hold: {args}")

        def fake_raw(args):
            diff_reads.append(args)
            self.fail("the gate must bind claimant to PR author before reading/counting the diff")

        def fake_labels(*names):
            labels.extend(names)
            return True

        gate.gh = fake_gh
        gate.gh_raw = fake_raw
        gate.add_labels = fake_labels

        self.assertEqual(gate.main(), 0)
        self.assertEqual(diff_reads, [])
        self.assertIn("needs-human", labels)
        self.assertNotIn("bounty-eligible", labels)
        self.assertTrue(any("work ownership needs human review" in c.lower() for c in comments))
        self.assertTrue(any("@bob" in c and "@alice" in c for c in comments))


if __name__ == "__main__":
    unittest.main()
