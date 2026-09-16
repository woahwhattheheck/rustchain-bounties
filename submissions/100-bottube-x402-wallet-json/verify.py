#!/usr/bin/env python3
"""Verify the byte-frozen BoTTube x402 wallet-JSON bounty carrier.

This verifier proves only the local evidence packet's internal consistency. It
does not prove sponsor acceptance, an RTC award, or payment.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "rustchain-bounty-evidence/v1"
PATCH_NAME = "bottube-x402-wallet-json.patch"
RECEIPT_NAME = "receipt.json"
EXPECTED_PATHS = (
    "bottube_x402.py",
    "tests/test_bottube_x402_init_app_registration.py",
)
EXPECTED_BASE = "6af6b63f7a5a87353a30cd4552dc5c0e183a96af"
EXPECTED_HEAD = "1e684920bf36f8fdfdded84f2ebf10028ca15269"
EXPECTED_PATCH_SHA256 = "5876bb4019c8585b2588e93736e9dfa7393da4a15024e89e28bb6cd2c63514fb"
EXPECTED_SOURCE_PR = "https://github.com/woahwhattheheck/bottube/pull/17"
EXPECTED_BOUNTY = "https://github.com/Scottcjn/rustchain-bounties/issues/100"

_REQUIRED_PATCH_FRAGMENTS = (
    'if not isinstance(data, dict):',
    'return _jsonify({"error": "JSON object required"}), 400',
    'if manual_address is not None and not isinstance(manual_address, str):',
    'return _jsonify({"error": "coinbase_address must be a string"}), 400',
    '("not-object", "JSON object required")',
    '(["not", "object"], "JSON object required")',
    '({"coinbase_address": ["0x123"]}, "coinbase_address must be a string")',
    'assert resp.status_code == 400',
)


class VerificationError(ValueError):
    """The packet is malformed, contradictory, or exceeds its authority."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise VerificationError(f"non-finite JSON number: {value}")


def _load_receipt(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot read strict receipt: {exc}") from exc
    if type(value) is not dict:
        raise VerificationError("receipt root must be an object")
    return value


def _expect_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise VerificationError(
            f"{label} keys differ: expected {sorted(expected)}, got {sorted(value)}"
        )


def _expect_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise VerificationError(f"{label} must be exactly {expected}")


def verify(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    receipt = _load_receipt(base / RECEIPT_NAME)

    _expect_exact_keys(
        receipt,
        {"schema", "bounty", "target", "artifact", "authority", "attribution"},
        "receipt",
    )
    if receipt["schema"] != SCHEMA:
        raise VerificationError("unsupported schema")

    bounty = receipt["bounty"]
    if type(bounty) is not dict:
        raise VerificationError("bounty must be an object")
    _expect_exact_keys(
        bounty,
        {"url", "issue", "advertised_improvement_tier_rtc", "award_claimed", "payment_claimed"},
        "bounty",
    )
    if bounty["url"] != EXPECTED_BOUNTY or bounty["issue"] != 100:
        raise VerificationError("wrong bounty identity")
    if type(bounty["advertised_improvement_tier_rtc"]) is not int or bounty[
        "advertised_improvement_tier_rtc"
    ] != 10:
        raise VerificationError("advertised tier must be integer 10 RTC")
    _expect_bool(bounty["award_claimed"], False, "bounty.award_claimed")
    _expect_bool(bounty["payment_claimed"], False, "bounty.payment_claimed")

    target = receipt["target"]
    if type(target) is not dict:
        raise VerificationError("target must be an object")
    _expect_exact_keys(
        target,
        {
            "repository",
            "upstream_base",
            "source_pr",
            "head",
            "changed_files",
            "additions",
            "deletions",
        },
        "target",
    )
    if target["repository"] != "Scottcjn/bottube":
        raise VerificationError("wrong target repository")
    if target["upstream_base"] != EXPECTED_BASE:
        raise VerificationError("wrong upstream base")
    if target["source_pr"] != EXPECTED_SOURCE_PR or target["head"] != EXPECTED_HEAD:
        raise VerificationError("wrong source PR generation")
    if target["changed_files"] != list(EXPECTED_PATHS):
        raise VerificationError("changed-file manifest mismatch")
    if (
        type(target["additions"]) is not int
        or type(target["deletions"]) is not int
        or target["additions"] != 29
        or target["deletions"] != 1
    ):
        raise VerificationError("diff statistics mismatch")

    artifact = receipt["artifact"]
    if type(artifact) is not dict:
        raise VerificationError("artifact must be an object")
    _expect_exact_keys(artifact, {"path", "sha256", "format"}, "artifact")
    if artifact != {
        "path": PATCH_NAME,
        "sha256": EXPECTED_PATCH_SHA256,
        "format": "git-format-patch/2-commits",
    }:
        raise VerificationError("artifact binding mismatch")

    authority = receipt["authority"]
    if type(authority) is not dict:
        raise VerificationError("authority must be an object")
    _expect_exact_keys(
        authority,
        {
            "source_patch_published",
            "sponsor_contact_performed_by_this_carrier",
            "sponsor_acceptance_observed",
            "award_observed",
            "payment_observed",
        },
        "authority",
    )
    _expect_bool(authority["source_patch_published"], True, "authority.source_patch_published")
    for name in (
        "sponsor_contact_performed_by_this_carrier",
        "sponsor_acceptance_observed",
        "award_observed",
        "payment_observed",
    ):
        _expect_bool(authority[name], False, f"authority.{name}")

    attribution = receipt["attribution"]
    if type(attribution) is not dict:
        raise VerificationError("attribution must be an object")
    _expect_exact_keys(attribution, {"source_owner", "carrier_owner"}, "attribution")
    if attribution["source_owner"] != "original paid-result seat":
        raise VerificationError("source attribution changed")
    if attribution["carrier_owner"] != "ZTL-P8V4":
        raise VerificationError("carrier attribution mismatch")

    try:
        patch = (base / PATCH_NAME).read_bytes()
    except OSError as exc:
        raise VerificationError(f"cannot read patch: {exc}") from exc
    digest = hashlib.sha256(patch).hexdigest()
    if digest != EXPECTED_PATCH_SHA256:
        raise VerificationError(f"patch digest mismatch: {digest}")
    try:
        text = patch.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("patch is not UTF-8") from exc

    commits = re.findall(r"^From ([0-9a-f]{40}) Mon Sep 17 00:00:00 2001$", text, re.MULTILINE)
    if commits != ["2e835d427c68eaf9b9a849b8cc2245a6daa20364", EXPECTED_HEAD]:
        raise VerificationError("patch commit sequence mismatch")
    paths = tuple(
        match.group(1)
        for match in re.finditer(r"^diff --git a/(.+?) b/\1$", text, re.MULTILINE)
    )
    if paths != EXPECTED_PATHS:
        raise VerificationError(f"patch path set/order mismatch: {paths!r}")
    if text.count("diff --git ") != len(EXPECTED_PATHS):
        raise VerificationError("unexpected additional diff sections")
    for fragment in _REQUIRED_PATCH_FRAGMENTS:
        if text.count(fragment) != 1:
            raise VerificationError(f"required patch fragment count is not one: {fragment}")

    result = {
        "ok": True,
        "schema": SCHEMA,
        "source_pr": EXPECTED_SOURCE_PR,
        "head": EXPECTED_HEAD,
        "patch_sha256": digest,
        "changed_files": list(EXPECTED_PATHS),
        "authority": {
            "sponsor_acceptance_observed": False,
            "award_observed": False,
            "payment_observed": False,
        },
    }
    return result


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]) if args else Path(__file__).resolve().parent
    try:
        result = verify(root)
    except VerificationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
