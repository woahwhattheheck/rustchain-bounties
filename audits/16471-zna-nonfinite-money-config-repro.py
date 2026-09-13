# SPDX-License-Identifier: MIT
"""Zero-network regression proof for RustChain #16471 non-finite money config."""

import math
import re
import unittest

MARKER_RE = re.compile(r"<!--\s*rtc-payout-amount:\s*([\d.]+)\s*-->")


def current_docstring_gate(rate, max_rtc, max_rtc_per_week, *, doc_count=500, already=0.0):
    """Model only the source-visible money decisions at upstream ea011e8."""
    amount = round(doc_count * rate, 2)
    if already + amount > max_rtc_per_week:
        return {"state": "weekly-cap", "amount": amount, "labels": False, "marker": None}
    if amount > max_rtc:
        return {"state": "needs-human", "amount": amount, "labels": False, "marker": None}
    marker = f"<!-- rtc-payout-amount: {amount} -->"
    return {
        "state": "verified-green",
        "amount": amount,
        "labels": True,
        "marker": marker,
        "payer_parses_marker": bool(MARKER_RE.search(marker)),
        "rerun_skips_as_adjudicated": True,
    }


def positive_finite(name, raw):
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite positive number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


class NonFiniteMoneyConfigProof(unittest.TestCase):
    def test_rate_nan_terminally_verifies_unpayable_marker(self):
        out = current_docstring_gate(float("nan"), 25.0, 40.0)
        self.assertEqual(out["state"], "verified-green")
        self.assertTrue(out["labels"])
        self.assertTrue(math.isnan(out["amount"]))
        self.assertFalse(out["payer_parses_marker"])
        self.assertTrue(out["rerun_skips_as_adjudicated"])

    def test_nan_caps_fail_open_comparisons(self):
        self.assertFalse(30.0 > float("nan"))
        self.assertFalse(41.0 > float("nan"))

    def test_infinite_caps_disable_upper_bounds(self):
        self.assertFalse(30.0 > float("inf"))
        self.assertFalse(41.0 > float("inf"))

    def test_proposed_parser_accepts_only_finite_positive(self):
        self.assertEqual(positive_finite("MAX_RTC", "25"), 25.0)
        self.assertEqual(positive_finite("RATE_PER_FUNC", "0.01"), 0.01)
        for raw in ("nan", "NaN", "inf", "Infinity", "-Infinity", "0", "-1", "garbage"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    positive_finite("MONEY_LIMIT", raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
