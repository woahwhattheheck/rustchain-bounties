#!/usr/bin/env python3
"""Offline reproducer for ZCG-M7Q5 payout-audit findings under #16471.

No network calls, wallet access, secrets, or production mutations. This models
only the decision logic present on upstream main@9cabad7f0849d88581f0716e08422fce2b05f88e.
"""
from __future__ import annotations

import datetime as dt
import unittest


def current_run_cap(amounts, max_per_run=40):
    """Current bounty_payout.py semantics: MAX_PER_RUN bounds claim count."""
    paid = 0
    total = 0.0
    for amount in amounts:
        if paid >= max_per_run:
            break
        paid += 1
        total += amount
    return paid, total


def fixed_run_cap(amounts, max_run_rtc=40.0):
    """Proposed semantics: aggregate money cannot exceed the configured cap."""
    paid = 0
    total = 0.0
    deferred = []
    for amount in amounts:
        if total + amount > max_run_rtc:
            deferred.append(amount)
            continue
        paid += 1
        total += amount
    return paid, total, deferred


def current_week_total(claims, now):
    """Current docstring gate: issue creation time determines the 7d window."""
    cutoff = now - dt.timedelta(days=7)
    return sum(c["amount"] for c in claims if c["issue_created"] > cutoff)


def fixed_week_total(claims, now):
    """Proposed gate: trusted amount-marker grant time determines the window."""
    cutoff = now - dt.timedelta(days=7)
    return sum(c["amount"] for c in claims if c["marker_created"] >= cutoff)


class Audit16471Repro(unittest.TestCase):
    def test_current_run_cap_greenly_exceeds_40_rtc_after_two_25_rtc_claims(self):
        paid, total = current_run_cap([25.0, 25.0], max_per_run=40)
        self.assertEqual(paid, 2)
        self.assertEqual(total, 50.0)
        self.assertGreater(total, 40.0)

    def test_current_run_cap_allows_1000_rtc_in_worst_permitted_shape(self):
        paid, total = current_run_cap([25.0] * 40, max_per_run=40)
        self.assertEqual(paid, 40)
        self.assertEqual(total, 1000.0)

    def test_proposed_run_cap_never_exceeds_money_ceiling(self):
        paid, total, deferred = fixed_run_cap([25.0, 25.0, 3.0, 10.0], 40.0)
        self.assertEqual(total, 38.0)
        self.assertEqual(paid, 3)
        self.assertEqual(deferred, [25.0])
        self.assertLessEqual(total, 40.0)

    def test_old_issue_granted_today_is_invisible_to_current_week_logic(self):
        now = dt.datetime(2026, 9, 13, 12, 0, tzinfo=dt.timezone.utc)
        claims = [{
            "issue_created": now - dt.timedelta(days=10),
            "marker_created": now - dt.timedelta(hours=1),
            "amount": 25.0,
        }]
        self.assertEqual(current_week_total(claims, now), 0)
        self.assertEqual(fixed_week_total(claims, now), 25.0)

    def test_old_issue_plus_new_claim_can_greenly_cross_40_rtc_under_current_logic(self):
        now = dt.datetime(2026, 9, 13, 12, 0, tzinfo=dt.timezone.utc)
        prior = [{
            "issue_created": now - dt.timedelta(days=10),
            "marker_created": now - dt.timedelta(hours=1),
            "amount": 25.0,
        }]
        new_amount = 25.0
        self.assertLessEqual(current_week_total(prior, now) + new_amount, 40.0)
        self.assertGreater(fixed_week_total(prior, now) + new_amount, 40.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
