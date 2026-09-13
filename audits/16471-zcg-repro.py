#!/usr/bin/env python3
"""Offline reproducer for ZCG-M7Q5 payout-audit findings under #16471.

No network calls, wallet access, secrets, or production mutations. This models
only the decision logic present on upstream main@9cabad7f0849d88581f0716e08422fce2b05f88e
plus the proposed fail-closed aggregate-money repair.
"""
from __future__ import annotations

import datetime as dt
import unittest
from decimal import Decimal, InvalidOperation


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


def parse_positive_rtc_budget(raw, field="MAX_PER_RUN"):
    """Model the proposed exact finite-positive config parser."""
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise SystemExit(
            f"invalid {field}: expected a finite positive RTC amount"
        ) from exc
    if not value.is_finite() or value <= 0:
        raise SystemExit(f"invalid {field}: expected a finite positive RTC amount")
    return value


def fixed_run_cap(amounts, max_run_rtc="40", transfer=None):
    """Proposed aggregate-money semantics with config validation before transfer.

    `transfer` is an optional zero-network callback used only to prove invalid
    configuration cannot reach the money-moving boundary.
    """
    budget = parse_positive_rtc_budget(str(max_run_rtc))
    paid = 0
    total = Decimal("0")
    deferred = []
    transfer = transfer or (lambda amount: None)
    for amount in amounts:
        try:
            amount_rtc = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            deferred.append(amount)
            continue
        if not amount_rtc.is_finite() or amount_rtc <= 0:
            deferred.append(amount)
            continue
        if total + amount_rtc > budget:
            deferred.append(amount)
            continue
        transfer(amount)
        paid += 1
        total += amount_rtc
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
        paid, total, deferred = fixed_run_cap(
            [25.0, 25.0, 3.0, 10.0], "40"
        )
        self.assertEqual(total, Decimal("38.0"))
        self.assertEqual(paid, 3)
        self.assertEqual(deferred, [25.0])
        self.assertLessEqual(total, Decimal("40"))

    def test_exact_decimal_boundary_pays_exactly_to_cap_and_defers_next(self):
        calls = []
        paid, total, deferred = fixed_run_cap(
            ["25.00", "15.00", "0.01"],
            "40.00",
            transfer=calls.append,
        )
        self.assertEqual(paid, 2)
        self.assertEqual(total, Decimal("40.00"))
        self.assertEqual(deferred, ["0.01"])
        self.assertEqual(calls, ["25.00", "15.00"])

    def test_binary_float_inputs_use_exact_textual_decimal_accounting(self):
        paid, total, deferred = fixed_run_cap([0.1, 0.2, 0.01], "0.3")
        self.assertEqual(paid, 2)
        self.assertEqual(total, Decimal("0.3"))
        self.assertEqual(deferred, [0.01])

    def test_invalid_budget_config_fails_before_transfer(self):
        for raw in (
            "NaN",
            "nan",
            "Infinity",
            "+Infinity",
            "-Infinity",
            "0",
            "0.0",
            "-1",
            "-0.0001",
            "garbage",
            "",
        ):
            with self.subTest(raw=raw):
                calls = []
                with self.assertRaises(SystemExit):
                    fixed_run_cap([1, 2, 3], raw, transfer=calls.append)
                self.assertEqual(
                    calls,
                    [],
                    f"invalid budget {raw!r} reached transfer boundary",
                )

    def test_valid_scientific_budget_is_finite_positive_and_exact(self):
        calls = []
        paid, total, deferred = fixed_run_cap(
            ["0.0005", "0.0005", "0.0001"],
            "1e-3",
            transfer=calls.append,
        )
        self.assertEqual(paid, 2)
        self.assertEqual(total, Decimal("0.0010"))
        self.assertEqual(deferred, ["0.0001"])
        self.assertEqual(calls, ["0.0005", "0.0005"])

    def test_nonfinite_or_nonpositive_candidate_amount_never_reaches_transfer(self):
        calls = []
        paid, total, deferred = fixed_run_cap(
            ["NaN", "Infinity", "-1", "0", "3"],
            "40",
            transfer=calls.append,
        )
        self.assertEqual(paid, 1)
        self.assertEqual(total, Decimal("3"))
        self.assertEqual(deferred, ["NaN", "Infinity", "-1", "0"])
        self.assertEqual(calls, ["3"])

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
