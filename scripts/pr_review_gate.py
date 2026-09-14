#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed executable boundary for the PR-review bounty gate.

The historical implementation remains byte-for-byte in
``pr_review_gate_core.py``.  This entrypoint preserves its import surface while
closing money-path ambiguities that the legacy gate cannot distinguish itself.

For an open review claim that was not already terminal, exit 0 now means the
core produced an authoritative verdict (bounty-eligible, needs-human, or
closed).  A silent/no-op return exits nonzero instead.  ``gate-processed`` is
only a provisional marker because the core writes it before the final verdict;
a bare marker is replayed as retryable state rather than treated as terminal.

The legacy core also performs one non-strict, one-page read of PR review
comments.  That evidence participates in the paid first-substantive-reviewer
decision, so this wrapper upgrades that exact read to strict exhaustive
pagination.  Provider failure or incomplete pagination must never masquerade
as "zero inline comments".

When a bare-marker replay retries a rejection close, an exact strict census of
existing issue comments prevents the preserved core from notifying the claimant
twice if the first comment succeeded but the close PATCH failed.
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
_INLINE_COMMENTS_SUFFIX = "/comments?per_page=100"
_MAX_INLINE_COMMENT_PAGES = 100
_MAX_ISSUE_COMMENT_PAGES = 100


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


def _core_replay_issue(issue: dict[str, Any], labels: set[str]) -> dict[str, Any]:
    """Hide only a bare provisional marker from the preserved core.

    The legacy core treats ``gate-processed`` as terminal on entry even though
    it writes that label before its final payout disposition.  If that marker
    exists without ``bounty-eligible`` or ``needs-human`` on an open claim, a
    previous invocation may have died between the provisional write and the
    verdict mutation.  Replay the same authoritative claim with only that
    provisional label removed so the preserved core re-adjudicates it.  All
    other claim fields and labels remain untouched.
    """
    if "gate-processed" not in labels or _VERDICT_LABELS.intersection(labels):
        return issue
    replay = dict(issue)
    replay["labels"] = [
        item for item in issue["labels"] if item.get("name") != "gate-processed"
    ]
    return replay


def _is_inline_comment_read(path: str, method: str, data: Any) -> bool:
    """Return True only for the legacy paid-decision review-comment list read."""
    return (
        method == "GET"
        and data is None
        and path.startswith("/repos/")
        and "/pulls/" in path
        and path.endswith(_INLINE_COMMENTS_SUFFIX)
    )


def _read_inline_comments_strict(
    provider: Callable[..., Any], first_page_path: str
) -> list[dict[str, Any]]:
    """Read every review-comment page or fail closed.

    The legacy core asks only for ``per_page=100`` and treats a failed GET as
    ``[]``.  Both behaviours are unsafe because inline-comment presence helps
    decide who is the first substantive reviewer and whether a claim is
    payable.  Keep the first-page URL byte-compatible with existing callers,
    force strict transport semantics, then continue until a short page proves
    exhaustion.  A pathological source that never exhausts is not evidence of
    completeness and therefore fails closed.
    """
    comments: list[dict[str, Any]] = []
    for page in range(1, _MAX_INLINE_COMMENT_PAGES + 1):
        page_path = (
            first_page_path
            if page == 1
            else f"{first_page_path}&page={page}"
        )
        try:
            rows = provider(page_path, strict=True)
        except Exception as exc:
            if isinstance(exc, ApiError):
                raise
            raise ApiError(
                "authoritative inline review-comment read failed on "
                f"page {page}: {exc.__class__.__name__}: {exc}"
            ) from exc

        if not isinstance(rows, list):
            raise ApiError(
                f"inline review-comment page {page} returned a non-list payload"
            )
        if any(not isinstance(row, dict) for row in rows):
            raise ApiError(
                f"inline review-comment page {page} contains malformed rows"
            )

        comments.extend(rows)
        if len(rows) < 100:
            return comments

    raise ApiError(
        "inline review-comment pagination exceeded "
        f"{_MAX_INLINE_COMMENT_PAGES} full pages without proving exhaustion"
    )


def _existing_comment_bodies(
    provider: Callable[..., Any], claim_path: str
) -> set[str]:
    """Return a strict complete census of claimant-facing issue comments."""
    bodies: set[str] = set()
    for page in range(1, _MAX_ISSUE_COMMENT_PAGES + 1):
        try:
            rows = provider(
                f"{claim_path}/comments?per_page=100&page={page}", strict=True
            )
        except Exception as exc:
            if isinstance(exc, ApiError):
                raise
            raise ApiError(
                "authoritative issue-comment read failed on "
                f"page {page}: {exc.__class__.__name__}: {exc}"
            ) from exc
        if not isinstance(rows, list):
            raise ApiError(
                f"issue-comment page {page} returned a non-list payload"
            )
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("body"), str):
                raise ApiError(
                    f"issue-comment page {page} contains malformed rows"
                )
            bodies.add(row["body"])
        if len(rows) < 100:
            return bodies
    raise ApiError(
        "issue-comment pagination exceeded "
        f"{_MAX_ISSUE_COMMENT_PAGES} full pages without proving exhaustion"
    )


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
    if "bounty-eligible" in initial_labels:
        return 0
    if "needs-human" in initial_labels and not retry_needs_human:
        return 0

    provisional_replay = (
        "gate-processed" in initial_labels
        and not _VERDICT_LABELS.intersection(initial_labels)
    )
    replay_issue = _core_replay_issue(issue, initial_labels)
    replayed_claim = False
    verdict_seen = False
    replay_comment_bodies: set[str] | None = None
    original_core_api = _core.api

    def tracked_api(path, method="GET", data=None, strict=False):
        nonlocal replayed_claim, verdict_seen, replay_comment_bodies

        # The strict preflight is the authoritative first claim read.  Replay
        # it exactly once so the preserved core cannot perform the old
        # non-strict GET that collapsed 403/429 into None.  A bare provisional
        # gate-processed marker is removed only from this in-process replay so
        # the preserved core cannot mistake a half-commit for a terminal state.
        if (
            not replayed_claim
            and method == "GET"
            and data is None
            and path == claim_path
        ):
            replayed_claim = True
            return replay_issue

        # Inline review comments are payout evidence.  The preserved core asks
        # for a single non-strict page; convert that one legacy call into a
        # strict complete read so provider failure or page truncation cannot
        # become an authoritative zero.
        if _is_inline_comment_read(path, method, data):
            return _read_inline_comments_strict(provider, path)

        # On a bare-marker replay, the preserved rejection helper may retry a
        # claimant-facing comment which succeeded immediately before a close
        # PATCH failed.  Suppress only an exact body already present in a
        # strict exhaustive issue-comment census.
        rejection_comment = (
            provisional_replay
            and method == "POST"
            and path == f"{claim_path}/comments"
            and isinstance(data, dict)
            and isinstance(data.get("body"), str)
        )
        if rejection_comment:
            if replay_comment_bodies is None:
                replay_comment_bodies = _existing_comment_bodies(provider, claim_path)
            if data["body"] in replay_comment_bodies:
                return {"deduplicated": True}

        result = provider(path, method=method, data=data, strict=strict)

        if rejection_comment and replay_comment_bodies is not None:
            replay_comment_bodies.add(data["body"])

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
