#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for prose_repo() and prose-repo authority in pr_review_gate.py.

Claims that name their repo in prose rather than as a full PR URL resolve to
(None, N). The named repo is part of the claimant's statement, so it must bind
the lookup before the default TARGET_REPO is consulted. Otherwise an unrelated
same-number PR in TARGET_REPO can supply the evidence for the wrong claim.

The risk in fixing it is over-matching: a resolver that grabs "this PR #12"
would redirect valid claims to a nonexistent repo. These tests pin both
directions and the end-to-end lookup order.
"""
import importlib.util
import os
import unittest
from pathlib import Path

os.environ.setdefault("GITHUB_TOKEN", "dummy")
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "pr_review_gate.py"
spec = importlib.util.spec_from_file_location("gate_under_test", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ProseRepoMatches(unittest.TestCase):
    def test_bare_repo_then_pr(self):
        self.assertEqual(
            gate.prose_repo("[CLAIM] Code review bounty #73 for rustchain-bounties PR #13434", ""),
            "rustchain-bounties")

    def test_owner_qualified_with_pr(self):
        self.assertEqual(
            gate.prose_repo("[Bounty Claim] Code Review - Scottcjn/rustchain-dialup PR #4", ""),
            "rustchain-dialup")

    def test_owner_qualified_hash_form(self):
        self.assertEqual(
            gate.prose_repo("Bounty claim: review Scottcjn/Rustchain#5358", ""),
            "Rustchain")

    def test_found_in_body_when_absent_from_title(self):
        self.assertEqual(
            gate.prose_repo("[Bounty Claim] Code Review", "Reviewed bottube PR #1622 today."),
            "bottube")

    def test_product_prefix_without_hyphen(self):
        self.assertEqual(gate.prose_repo("review of bottube PR #900", ""), "bottube")


class ProseRepoRejects(unittest.TestCase):
    """Over-matching would redirect valid claims at a repo that does not exist."""

    def test_plain_pr_reference_is_not_a_repo(self):
        self.assertIsNone(gate.prose_repo("[Bounty Claim] PR Review - PR #5536 (Bounty #73)", ""))

    def test_common_words_are_not_repos(self):
        for t in ["I reviewed this PR #12", "the PR #4944 was fine",
                  "Claim: PR Review #4944 - missing SPDX gate failure"]:
            self.assertIsNone(gate.prose_repo(t, ""), t)

    def test_empty_inputs(self):
        self.assertIsNone(gate.prose_repo("", ""))
        self.assertIsNone(gate.prose_repo("", None))


class PrRefUnchanged(unittest.TestCase):
    """The existing resolver must keep its current behaviour exactly."""

    def test_full_url_still_wins(self):
        r, n = gate.pr_ref("", "https://github.com/Scottcjn/Rustchain/pull/5395 reviewed")
        self.assertEqual((r, n), ("Scottcjn/Rustchain", "5395"))

    def test_bounty_number_not_mistaken_for_pr(self):
        r, n = gate.pr_ref("Bounty #1009 claim: review of PR #1396", "")
        self.assertEqual(n, "1396")

    def test_prose_repo_does_not_change_pr_number(self):
        title = "[CLAIM] Code review bounty #73 for rustchain-bounties PR #13434"
        _, n = gate.pr_ref(title, "")
        self.assertEqual(n, "13434")


class ProseRepoLookupAuthority(unittest.TestCase):
    """A claimant-named repo wins even when TARGET has the same PR number."""

    def setUp(self):
        self.old = (gate.api, gate.NUM, gate.REPO, gate.TARGET, gate.CAP, gate.RATE)
        gate.NUM = "9001"
        gate.REPO = "Scottcjn/rustchain-bounties"
        gate.TARGET = "Scottcjn/Rustchain"
        gate.CAP = 15
        gate.RATE = "3"
        self.addCleanup(self.restore)

    def restore(self):
        gate.api, gate.NUM, gate.REPO, gate.TARGET, gate.CAP, gate.RATE = self.old

    @staticmethod
    def claim():
        return {
            "state": "open",
            "labels": [],
            "title": "Code review bounty #73 for rustchain-rips PR #10",
            "body": "RTC" + "a" * 40,
            "user": {"login": "alice"},
        }

    @staticmethod
    def review(login):
        return {
            "submitted_at": "2026-09-13T00:00:00Z",
            "body": "Finding: " + "x" * 130,
            "user": {"login": login},
        }

    def test_named_repo_is_queried_before_same_number_default(self):
        calls = []
        writes = []

        def fake_api(path, method="GET", data=None, strict=False):
            calls.append((path, method))
            if path == "/repos/Scottcjn/rustchain-bounties/issues/9001" and method == "GET":
                return self.claim()
            if path == "/repos/Scottcjn/rustchain-rips/pulls/10/reviews":
                return [self.review("alice")]
            if path == "/repos/Scottcjn/Rustchain/pulls/10/reviews":
                return [self.review("bob")]
            if path == "/repos/Scottcjn/rustchain-rips/pulls/10/comments?per_page=100":
                return []
            if path.startswith("/search/issues?"):
                return {"total_count": 0}
            if method in {"POST", "PATCH"}:
                writes.append((path, method, data))
                return {}
            raise AssertionError(f"unexpected API call: {method} {path}")

        gate.api = fake_api
        gate.main()

        self.assertIn(("/repos/Scottcjn/rustchain-rips/pulls/10/reviews", "GET"), calls)
        self.assertNotIn(("/repos/Scottcjn/Rustchain/pulls/10/reviews", "GET"), calls)
        self.assertTrue(any(
            path.endswith("/labels") and data == {"labels": ["bounty-eligible"]}
            for path, method, data in writes if method == "POST"
        ))

    def test_missing_named_repo_fails_human_without_default_fallback(self):
        calls = []
        writes = []

        def fake_api(path, method="GET", data=None, strict=False):
            calls.append((path, method))
            if path == "/repos/Scottcjn/rustchain-bounties/issues/9001" and method == "GET":
                return self.claim()
            if path == "/repos/Scottcjn/rustchain-rips/pulls/10/reviews":
                return None
            if path == "/repos/Scottcjn/Rustchain/pulls/10/reviews":
                raise AssertionError("default repo must not be probed after claimant names a repo")
            if method in {"POST", "PATCH"}:
                writes.append((path, method, data))
                return {}
            raise AssertionError(f"unexpected API call: {method} {path}")

        gate.api = fake_api
        gate.main()

        self.assertNotIn(("/repos/Scottcjn/Rustchain/pulls/10/reviews", "GET"), calls)
        self.assertTrue(any(
            path.endswith("/labels") and data == {"labels": ["needs-human"]}
            for path, method, data in writes if method == "POST"
        ))
        self.assertFalse(any(
            path.endswith("/labels") and data == {"labels": ["bounty-eligible"]}
            for path, method, data in writes if method == "POST"
        ))


if __name__ == "__main__":
    unittest.main()
