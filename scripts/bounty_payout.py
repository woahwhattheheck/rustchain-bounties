#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed money-configuration boundary for the bounty payout runner.

The implementation remains byte-for-byte in ``bounty_payout_impl.py``.  This
entry point validates RTC-valued environment controls *before* the implementation
can enumerate claims or attempt a transfer.
"""

import importlib.util
from pathlib import Path


def _load_money_guard():
    path = Path(__file__).with_name("_rtc_money_config.py")
    spec = importlib.util.spec_from_file_location("_rtc_money_config", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load money configuration guard: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_load_money_guard().validate_payout_config()

_impl = Path(__file__).with_name("bounty_payout_impl.py")
exec(compile(_impl.read_bytes(), str(_impl), "exec"), globals(), globals())
