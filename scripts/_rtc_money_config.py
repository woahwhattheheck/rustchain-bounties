#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed validation for RTC-valued environment configuration."""

from __future__ import annotations

import math
import os


class MoneyConfigError(RuntimeError):
    """Raised when money-moving configuration is malformed or unsafe."""


def _finite_float(name: str, default: str) -> float:
    raw = os.environ.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise MoneyConfigError(
            f"{name} must be a finite numeric value; got {raw!r}"
        ) from exc
    if not math.isfinite(value):
        raise MoneyConfigError(
            f"{name} must be finite; got {raw!r}"
        )
    return value


def _positive(name: str, default: str) -> float:
    value = _finite_float(name, default)
    if value <= 0:
        raise MoneyConfigError(
            f"{name} must be > 0; got {value!r}"
        )
    return value


def _nonnegative(name: str, default: str) -> float:
    value = _finite_float(name, default)
    if value < 0:
        raise MoneyConfigError(
            f"{name} must be >= 0; got {value!r}"
        )
    return value


def validate_payout_config() -> dict[str, float]:
    """Validate every RTC-valued control consumed by bounty_payout.py."""
    rate = _positive("RATE_RTC", "3")
    hard_cap = _nonnegative("MAX_CLAIM_RTC", "25")
    if rate > hard_cap:
        raise MoneyConfigError(
            "RATE_RTC must not exceed MAX_CLAIM_RTC "
            f"(rate={rate:g}, cap={hard_cap:g})"
        )
    return {"RATE_RTC": rate, "MAX_CLAIM_RTC": hard_cap}


def validate_docstring_config() -> dict[str, float]:
    """Validate every RTC-valued control consumed by docstring_gate.py."""
    rate = _positive("RATE_PER_FUNC", "0.01")
    per_claim = _nonnegative("MAX_RTC", "25")
    per_week = _nonnegative("MAX_RTC_PER_WEEK", "40")
    return {
        "RATE_PER_FUNC": rate,
        "MAX_RTC": per_claim,
        "MAX_RTC_PER_WEEK": per_week,
    }
