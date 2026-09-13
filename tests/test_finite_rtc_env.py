#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression coverage for fail-closed RTC monetary configuration."""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
GUARD = SCRIPTS / "_rtc_money_config.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("_rtc_money_config_under_test", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load_guard()


class MoneyConfigUnitTests(unittest.TestCase):
    def test_valid_defaults_are_finite(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                guard.validate_payout_config(),
                {"RATE_RTC": 3.0, "MAX_CLAIM_RTC": 25.0},
            )
            self.assertEqual(
                guard.validate_docstring_config(),
                {
                    "RATE_PER_FUNC": 0.01,
                    "MAX_RTC": 25.0,
                    "MAX_RTC_PER_WEEK": 40.0,
                },
            )

    def test_payout_rejects_nonfinite_values(self):
        for name in ("RATE_RTC", "MAX_CLAIM_RTC"):
            for value in ("nan", "inf", "-inf"):
                with self.subTest(name=name, value=value):
                    with mock.patch.dict(os.environ, {name: value}, clear=True):
                        with self.assertRaises(guard.MoneyConfigError):
                            guard.validate_payout_config()

    def test_docstring_gate_rejects_nonfinite_values(self):
        for name in ("RATE_PER_FUNC", "MAX_RTC", "MAX_RTC_PER_WEEK"):
            for value in ("nan", "inf", "-inf"):
                with self.subTest(name=name, value=value):
                    with mock.patch.dict(os.environ, {name: value}, clear=True):
                        with self.assertRaises(guard.MoneyConfigError):
                            guard.validate_docstring_config()

    def test_negative_ceilings_are_rejected(self):
        for validator, name in (
            (guard.validate_payout_config, "MAX_CLAIM_RTC"),
            (guard.validate_docstring_config, "MAX_RTC"),
            (guard.validate_docstring_config, "MAX_RTC_PER_WEEK"),
        ):
            with self.subTest(name=name):
                with mock.patch.dict(os.environ, {name: "-0.01"}, clear=True):
                    with self.assertRaises(guard.MoneyConfigError):
                        validator()

    def test_zero_or_negative_rates_are_rejected(self):
        for validator, name in (
            (guard.validate_payout_config, "RATE_RTC"),
            (guard.validate_docstring_config, "RATE_PER_FUNC"),
        ):
            for value in ("0", "-1"):
                with self.subTest(name=name, value=value):
                    with mock.patch.dict(os.environ, {name: value}, clear=True):
                        with self.assertRaises(guard.MoneyConfigError):
                            validator()

    def test_flat_review_rate_cannot_bypass_hard_claim_cap(self):
        with mock.patch.dict(
            os.environ,
            {"RATE_RTC": "26", "MAX_CLAIM_RTC": "25"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                guard.MoneyConfigError, "must not exceed MAX_CLAIM_RTC"
            ):
                guard.validate_payout_config()


class EntrypointOrderingTests(unittest.TestCase):
    @staticmethod
    def _run(script_name, overrides):
        env = os.environ.copy()
        env.pop("GITHUB_TOKEN", None)
        env.pop("RTC_ADMIN_KEY", None)
        env.update(overrides)
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script_name)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_payout_fails_on_bad_money_config_before_secret_reads(self):
        result = self._run("bounty_payout.py", {"MAX_CLAIM_RTC": "nan"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MAX_CLAIM_RTC must be finite", result.stderr)
        self.assertNotIn("GITHUB_TOKEN", result.stderr)

    def test_docstring_gate_fails_on_bad_money_config_before_adjudication(self):
        result = self._run("docstring_gate.py", {"MAX_RTC_PER_WEEK": "inf"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MAX_RTC_PER_WEEK must be finite", result.stderr)
        self.assertNotIn("ISSUE_NUMBER not set", result.stderr)


if __name__ == "__main__":
    unittest.main()
