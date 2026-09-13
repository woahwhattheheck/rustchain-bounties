#!/usr/bin/env python3
"""Zero-network reproducer for #16471 non-finite money configuration."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import math
from pathlib import Path


def strict_positive_finite_float(raw: str, field: str) -> float:
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field}: expected finite positive amount") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{field}: expected finite positive amount")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{field}: outside finite float range")
    return result


def expect_reject(raw: str) -> None:
    try:
        strict_positive_finite_float(raw, "TEST")
    except ValueError:
        return
    raise AssertionError(f"accepted invalid money configuration: {raw!r}")


def main() -> None:
    # Current vulnerable comparison shape: NaN disables an ordered ceiling.
    cap = float("NaN")
    assert not (100.0 > cap)
    assert not (1000.0 + 25.0 > cap)

    # Pin the exact vulnerable source forms when run from the repository root.
    payout = Path("scripts/bounty_payout.py")
    gate = Path("scripts/docstring_gate.py")
    if payout.exists() and gate.exists():
        p = payout.read_text(encoding="utf-8")
        g = gate.read_text(encoding="utf-8")
        assert 'MAX_CLAIM_RTC=float(os.environ.get("MAX_CLAIM_RTC","25"))' in p
        assert 'MAX_RTC = float(os.environ.get("MAX_RTC", "25"))' in g
        assert 'MAX_RTC_PER_WEEK = float(os.environ.get("MAX_RTC_PER_WEEK", "40"))' in g

    for raw in ("NaN", "sNaN", "Infinity", "-Infinity", "0", "-1", "wat", "1e10000"):
        expect_reject(raw)

    assert strict_positive_finite_float("25", "TEST") == 25.0
    assert strict_positive_finite_float("0.01", "TEST") == 0.01
    assert strict_positive_finite_float("1e2", "TEST") == 100.0
    print("PASS: NaN bypass reproduced; strict finite-positive parser rejects hostile configs")


if __name__ == "__main__":
    main()
