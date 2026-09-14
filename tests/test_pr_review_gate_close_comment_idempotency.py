# SPDX-License-Identifier: MIT
"""Regression coverage for rejection-comment replay idempotency."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "pr_review_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location(
        "pr_review_gate_close_comment_idempotency_test", GATE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO = "Scottcjn/rustchain-bounties"
    mod.NUM = "42"
    mod.TARGET = "Scottcjn/Rustchain"
    return mod


def claim(*, labels=None, state="open"):
    return {
        "state": state,
        "labels": [{"name": name} for name in (labels or [])],
        "title": "Code review bounty #73",
        "body": "RTC" + "a" * 40,
        "user": {"login": "alice"},
    }


@pytest.mark.parametrize("failed_step", ["comment", "close"])
def test_replayed_rejection_close_notifies_exactly_once(failed_step):
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    labels = set()
    comments = []
    state = "open"
    fail_once = True
    notice = "Gate rejection: first substantive reviewer was someone else."

    def provider(path, method="GET", data=None, strict=False):
        nonlocal state, fail_once
        if path == issue_path and method == "GET":
            return claim(labels=sorted(labels), state=state)
        if path.startswith(f"{issue_path}/comments?") and method == "GET":
            assert strict is True
            return [{"body": body} for body in comments]
        if path == f"{issue_path}/labels" and method == "POST":
            labels.update(data["labels"])
            return {}
        if path == f"{issue_path}/comments" and method == "POST":
            if failed_step == "comment" and fail_once:
                fail_once = False
                raise gate.ApiError("transient rejection comment failure")
            comments.append(data["body"])
            return {}
        if path == issue_path and method == "PATCH" and data.get("state") == "closed":
            if failed_step == "close" and fail_once:
                fail_once = False
                raise gate.ApiError("transient rejection close failure")
            state = "closed"
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path} {data!r}")

    def rejection_core():
        issue = gate._core.api(issue_path)
        seen = {row["name"] for row in issue["labels"]}
        if "gate-processed" in seen:
            return None
        gate._core.api(
            f"{issue_path}/labels", "POST", {"labels": ["gate-processed"]}
        )
        gate._core.api(f"{issue_path}/comments", "POST", {"body": notice})
        gate._core.api(
            issue_path, "PATCH", {"state": "closed", "state_reason": "not_planned"}
        )
        return None

    gate.api = provider
    gate._core.main = rejection_core

    assert gate.main() == 1
    assert labels == {"gate-processed"}
    assert state == "open"
    assert comments == ([] if failed_step == "comment" else [notice])

    assert gate.main() == 0
    assert state == "closed"
    assert comments == [notice]


def test_replay_comment_census_reads_past_first_100_comments():
    gate = load_gate()
    claim_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    target = "the rejection body"
    calls = []

    def provider(path, method="GET", data=None, strict=False):
        calls.append((path, method, strict))
        if path.endswith("page=1"):
            return [{"body": f"old-{index}"} for index in range(100)]
        if path.endswith("page=2"):
            return [{"body": target}]
        raise AssertionError(path)

    bodies = gate._existing_comment_bodies(provider, claim_path)
    assert target in bodies
    assert len(calls) == 2
    assert all(method == "GET" and strict is True for _, method, strict in calls)


def test_replay_comment_census_failure_fails_closed_without_posting():
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    posted = []

    def provider(path, method="GET", data=None, strict=False):
        if path == issue_path and method == "GET":
            return claim(labels=["gate-processed"])
        if path.startswith(f"{issue_path}/comments?") and method == "GET":
            assert strict is True
            raise gate.ApiError("GET comment census -> HTTP 429")
        if path == f"{issue_path}/comments" and method == "POST":
            posted.append(data["body"])
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path}")

    def rejection_core():
        gate._core.api(issue_path)
        gate._core.api(
            f"{issue_path}/comments", "POST", {"body": "already-published notice"}
        )
        return None

    gate.api = provider
    gate._core.main = rejection_core

    assert gate.main() == 1
    assert posted == []
