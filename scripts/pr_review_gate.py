#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed executable boundary for the PR-review bounty gate.

The historical implementation remains byte-for-byte in
``pr_review_gate_core.py``.  This entrypoint preserves its import surface while
closing one money-path ambiguity: failure to read the claim itself must never
look like a successful adjudication to ``pr_review_gate_backfill.py``.

For an open review claim that was not already terminal, exit 0 now means the
core produced an authoritative verdict (bounty-eligible, needs-human, or
closed).  A silent/no-op return exits nonzero instead.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Callable

_CORE_PATH = Path(__file__).with_name("pr_review_gate_core.py")
_spec = importlib.util.spec_from_file_location("_pr_review_gate_core", _CORE_PATH)
if _spec is None or _spec.loader is None:  # pragma: no cover - import machinery guard
    raise ImportError(f"could not load {_CORE_PATH}")
_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)

# Preserve the legacy import surface, including underscored helpers used by
# existing zero-network tests.  Module identity fields stay owned by this
# wrapper so direct execution still reaches the hardened main() below.
_SKIP_EXPORTS = {
    "__name__", "__file__", "__package__", "__loader__", "__spec__",
    "__builtins__", "main",
}
for _name in dir(_core):
    if _name not in _SKIP_EXPORTS:
        globals()[_name] = getattr(_core, _name)

_RUNTIME_CONFIG = ("TOKEN", "REPO", "TARGET", "NUM", "CAP", "RATE", "API")
_VERDICT_LABELS = frozenset({"bounty-eligible", "needs-human"})


def _sync_runtime_config() -> None:
    """Propagate caller/test overrides from this compatibility module."""
    for name in _RUNTIME_CONFIG:
        if name in globals():
            setattr(_core, name, globals()[name])


def _label_names(issue: dict[str, Any]) -> set[str]:
    raw = issue.get("labels")
    if not isinstance(raw, list):
        raise ApiError("claim detail labels must be a list")
    labels: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ApiError("claim detail contains malformed label metadata")
        labels.add(item["name"])
    return labels


def _read_claim_strict(provider: Callable[..., Any]) -> tuple[dict[str, Any], str]:
    """Read and shape-check the authoritative claim detail."""
    claim_path = f"/repos/{REPO}/issues/{NUM}"
    try:
        issue = provider(claim_path, strict=True)
    except Exception as exc:
        if isinstance(exc, ApiError):
            raise
        raise ApiError(
            f"authoritative claim read failed: {exc.__class__.__name__}: {exc}"
        ) from exc
    if not isinstance(issue, dict):
        raise ApiError("authoritative claim read returned no issue object")
    if issue.get("state") not in {"open", "closed"}:
        raise ApiError("claim detail has invalid or missing state")
    if not isinstance(issue.get("title"), str):
        raise ApiError("claim detail has invalid or missing title")
    _label_names(issue)
    return issue, claim_path


def main() -> int:
    _sync_runtime_config()
    provider = globals()["api"]

    try:
        issue, claim_path = _read_claim_strict(provider)
    except ApiError as exc:
        print(f"gate preflight failed closed: {exc}", file=sys.stderr)
        return 1

    if issue["state"] != "open":
        return 0
    if not is_review_claim(issue["title"]):
        return 0

    initial_labels = _label_names(issue)
    retry_needs_human = os.environ.get("RETRY_NEEDS_HUMAN", "") == "1"
    if "bounty-eligible" in initial_labels or "gate-processed" in initial_labels:
        return 0
    if "needs-human" in initial_labels and not retry_needs_human:
        return 0

    replayed_claim = False
    verdict_seen = False
    original_core_api = _core.api

    def tracked_api(path, method="GET", data=None, strict=False):
        nonlocal replayed_claim, verdict_seen

        # The strict preflight is the authoritative first claim read.  Replay
        # it exactly once so the preserved core cannot perform the old
        # non-strict GET that collapsed 403/429 into None.
        if (
            not replayed_claim
            and method == "GET"
            and data is None
            and path == claim_path
        ):
            replayed_claim = True
            return issue

        result = provider(path, method=method, data=data, strict=strict)

        # Count a verdict only after the mutation call has returned
        # successfully.  `gate-processed` alone is intentionally insufficient:
        # the core applies it before the final verdict.
        if (
            method == "POST"
            and path == f"{claim_path}/labels"
            and isinstance(data, dict)
            and isinstance(data.get("labels"), list)
            and _VERDICT_LABELS.intersection(data["labels"])
        ):
            verdict_seen = True
        elif (
            method == "PATCH"
            and path == claim_path
            and isinstance(data, dict)
            and data.get("state") == "closed"
        ):
            verdict_seen = True
        return result

    _sync_runtime_config()
    _core.api = tracked_api
    try:
        result = _core.main()
    except Exception as exc:
        print(
            f"gate adjudication failed closed: {exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    finally:
        _core.api = original_core_api

    if result not in (None, 0):
        try:
            return int(result)
        except (TypeError, ValueError):
            print(f"gate returned invalid status: {result!r}", file=sys.stderr)
            return 1

    # A retry of a pre-existing needs-human verdict is authoritative even when
    # the retry remains unresolved and intentionally emits no duplicate notice.
    if verdict_seen or ("needs-human" in initial_labels and retry_needs_human):
        return 0

    print(
        "gate failed closed: open review claim returned without an authoritative "
        "bounty-eligible / needs-human / closed disposition",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
