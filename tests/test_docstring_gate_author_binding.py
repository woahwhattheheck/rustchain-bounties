#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression tests for docstring claim-author / merged-PR-author binding."""
import importlib.util
import os
import unittest
from pathlib import Path

os.environ.setdefault("GITHUB_TOKEN", "dummy")
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "docstring_gate.py"
spec = importlib.util.spec_from_file_location("docstring_gate_author_binding", SCRIPT)
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)


class ReachedDiff(RuntimeError):
    """Sentinel proving the identity fence allowed execution to reach PR diff work."""


class ClaimAuthorBindingTests(unittest.TestCase):
    def setUp(self):
        self._gh = dg.gh
        self._gh_raw = dg.gh_raw
        self._add_labels = dg.add_labels
        self._num = dg.NUM
        dg.NUM = "123"
        self.events = []

    def tearDown(self):
        dg.gh = self._gh
        dg.gh_raw = self._gh_raw
        dg.add_labels = self._add_labels
        dg.NUM = self._num

    def _run_case(self, claim_author, pr_author):
        issue = {
            "title": "Docstring batch 99",
            "body": "Documented 1 function in https://github.com/acme/repo/pull/9",
            "labels": [],
            "author": claim_author,
            "state": "OPEN",
        }
        pr = {
            "state": "MERGED",
            "additions": 1,
            "deletions": 0,
            "files": [{"path": "src/example.py"}],
            "author": pr_author,
            "mergedAt": "2026-09-13T00:00:00Z",
        }

        def fake_gh(args, default=None, strict=False):
            del default, strict
            if args[:2] == ["issue", "view"]:
                return issue
            if args[:2] == ["pr", "view"]:
                return pr
            if args[:2] == ["issue", "comment"]:
                self.events.append(("comment", args[-1]))
                return {}
            self.fail(f"unexpected gh call: {args}")

        def fake_add_labels(*names):
            self.events.append(("labels", names))
            return True

        def stop_at_diff(args):
            self.events.append(("diff", tuple(args)))
            raise ReachedDiff("identity gate passed")

        dg.gh = fake_gh
        dg.add_labels = fake_add_labels
        dg.gh_raw = stop_at_diff
        return dg.main()

    def test_mismatched_claimant_never_reaches_diff_or_payable_path(self):
        rc = self._run_case({"login": "claimant"}, {"login": "other-author"})

        self.assertEqual(rc, 0)
        self.assertFalse(any(event[0] == "diff" for event in self.events))
        self.assertEqual(
            [event for event in self.events if event[0] == "labels"],
            [("labels", ("needs-human",))],
        )
        comments = [event[1] for event in self.events if event[0] == "comment"]
        self.assertEqual(len(comments), 1)
        self.assertIn("@claimant", comments[0])
        self.assertIn("@other-author", comments[0])

    def test_missing_claim_author_fails_closed_before_diff(self):
        rc = self._run_case({}, {"login": "author"})

        self.assertEqual(rc, 0)
        self.assertFalse(any(event[0] == "diff" for event in self.events))
        self.assertIn(("labels", ("needs-human",)), self.events)

    def test_missing_pr_author_fails_closed_before_diff(self):
        rc = self._run_case({"login": "claimant"}, None)

        self.assertEqual(rc, 0)
        self.assertFalse(any(event[0] == "diff" for event in self.events))
        self.assertIn(("labels", ("needs-human",)), self.events)

    def test_malformed_login_fails_closed_before_diff(self):
        rc = self._run_case({"login": 123}, {"login": "author"})

        self.assertEqual(rc, 0)
        self.assertFalse(any(event[0] == "diff" for event in self.events))
        self.assertIn(("labels", ("needs-human",)), self.events)

    def test_same_author_is_case_insensitive_and_reaches_existing_diff_path(self):
        with self.assertRaises(ReachedDiff):
            self._run_case(
                {"login": "WoahWhatTheHeck"},
                {"login": "woahwhattheheck"},
            )

        self.assertTrue(any(event[0] == "diff" for event in self.events))
        self.assertFalse(any(event[0] == "labels" for event in self.events))
        self.assertFalse(any(event[0] == "comment" for event in self.events))


if __name__ == "__main__":
    unittest.main()
