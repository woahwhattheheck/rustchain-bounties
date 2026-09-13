#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression tests for claimant-level bot exclusion in bounty payouts."""
import importlib.util
import os
import subprocess
import unittest
from pathlib import Path

os.environ.setdefault("GITHUB_TOKEN", "dummy")
os.environ.setdefault("RTC_ADMIN_KEY", "dummy")
os.environ.setdefault("RTC_VPS_HOST", "127.0.0.1")
os.environ.setdefault("GH_REPO", "owner/repo")
os.environ.setdefault("RATE_RTC", "3")
os.environ.setdefault("MAX_PER_RUN", "40")

_orig_run = subprocess.run


def _stub_run(*args, **kwargs):
    class _Result:
        stdout = "[]"
        stderr = ""
        returncode = 0
    return _Result()


subprocess.run = _stub_run
try:
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "bounty_payout.py"
    spec = importlib.util.spec_from_file_location("bounty_payout_bot_test", script)
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
finally:
    subprocess.run = _orig_run


NATIVE_WALLET = "RTC" + "a" * 40


class BotClaimantResolutionTests(unittest.TestCase):
    def test_known_bot_cannot_bypass_exclusion_with_native_wallet(self):
        wallet, source = bp.resolve_wallet(
            f"Wallet: {NATIVE_WALLET}", [], claimant_login="dependabot[bot]"
        )
        self.assertIsNone(wallet)
        self.assertIsNone(source)

    def test_known_bot_cannot_bypass_exclusion_with_body_handle(self):
        wallet, source = bp.resolve_wallet(
            "Wallet: payout-destination", [], claimant_login="github-actions"
        )
        self.assertIsNone(wallet)
        self.assertIsNone(source)

    def test_known_bot_cannot_receive_canonical_wallet(self):
        original = bp.CANONICAL_WALLETS
        try:
            bp.CANONICAL_WALLETS = {"dependabot": NATIVE_WALLET}
            wallet, source = bp.resolve_wallet(
                "", [], claimant_login="dependabot"
            )
        finally:
            bp.CANONICAL_WALLETS = original
        self.assertIsNone(wallet)
        self.assertIsNone(source)

    def test_human_claimant_still_resolves_native_wallet(self):
        wallet, source = bp.resolve_wallet(
            f"Wallet: {NATIVE_WALLET}", [], claimant_login="human-contributor"
        )
        self.assertEqual(wallet, NATIVE_WALLET)
        self.assertEqual(source, "native")


if __name__ == "__main__":
    unittest.main()
