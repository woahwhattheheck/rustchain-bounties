# SPDX-License-Identifier: MIT
"""Zero-network regressions for the PR-review gate's fail-closed entrypoint."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "pr_review_gate.py"
BACKFILL_PATH = ROOT / "scripts" / "pr_review_gate_backfill.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("pr_review_gate_entrypoint_test", GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO = "Scottcjn/rustchain-bounties"
    mod.NUM = "42"
    mod.TARGET = "Scottcjn/Rustchain"
    return mod


def claim(*, labels=None, state="open", title="Code review bounty #73"):
    return {
        "state": state,
        "labels": [{"name": name} for name in (labels or [])],
        "title": title,
        "body": "RTC" + "a" * 40,
        "user": {"login": "alice"},
    }


@pytest.mark.parametrize("status", [403, 429])
def test_authoritative_claim_transport_failure_exits_nonzero(status):
    gate = load_gate()
    core_called = False

    def provider(path, method="GET", data=None, strict=False):
        assert strict is True
        raise gate.ApiError(f"GET {path} -> HTTP {status}")

    def should_not_run():
        nonlocal core_called
        core_called = True

    gate.api = provider
    gate._core.main = should_not_run

    assert gate.main() == 1
    assert core_called is False


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"state": "open", "title": "Code review bounty #73", "labels": "not-a-list"},
        {"state": "open", "title": None, "labels": []},
    ],
)
def test_empty_or_malformed_claim_detail_exits_nonzero(payload):
    gate = load_gate()
    gate.api = lambda path, method="GET", data=None, strict=False: payload
    gate._core.main = lambda: pytest.fail("core must not run after bad claim detail")

    assert gate.main() == 1


def test_open_review_claim_noop_core_exits_nonzero():
    gate = load_gate()
    calls = []

    def provider(path, method="GET", data=None, strict=False):
        calls.append((path, method, strict))
        return claim()

    gate.api = provider
    gate._core.main = lambda: None

    assert gate.main() == 1
    assert calls == [("/repos/Scottcjn/rustchain-bounties/issues/42", "GET", True)]


def test_preserved_core_ordinary_unresolved_claim_is_authoritative():
    gate = load_gate()
    labels = []
    comments = []
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"

    def provider(path, method="GET", data=None, strict=False):
        if path == issue_path and method == "GET":
            return claim()
        if path == f"{issue_path}/labels" and method == "POST":
            labels.extend(data["labels"])
            return {}
        if path == f"{issue_path}/comments" and method == "POST":
            comments.append(data["body"])
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path}")

    gate.api = provider

    assert gate.main() == 0
    assert "gate-processed" in labels
    assert "needs-human" in labels
    assert comments


def test_successful_close_counts_as_authoritative_disposition():
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"

    def provider(path, method="GET", data=None, strict=False):
        if path == issue_path and method == "GET":
            return claim()
        if path == issue_path and method == "PATCH" and data["state"] == "closed":
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path}")

    gate.api = provider

    def close_core():
        gate._core.api(
            issue_path, "PATCH", {"state": "closed", "state_reason": "not_planned"}
        )
        return None

    gate._core.main = close_core

    assert gate.main() == 0


def test_backfill_does_not_count_failclosed_child_as_adjudicated():
    spec = importlib.util.spec_from_file_location("pr_review_gate_backfill_test", BACKFILL_PATH)
    backfill = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backfill)
    failed = SimpleNamespace(returncode=1, stdout="", stderr="claim read failed closed")

    with patch.object(backfill.subprocess, "run", return_value=failed):
        assert backfill.adjudicate(42) is False


def test_preexisting_needs_human_nonretry_stays_idempotent(monkeypatch):
    gate = load_gate()
    monkeypatch.delenv("RETRY_NEEDS_HUMAN", raising=False)
    gate.api = lambda path, method="GET", data=None, strict=False: claim(
        labels=["needs-human"]
    )
    gate._core.main = lambda: pytest.fail("non-retry needs-human must stay idempotent")

    assert gate.main() == 0


def test_preexisting_bounty_eligible_stays_terminal():
    gate = load_gate()
    gate.api = lambda path, method="GET", data=None, strict=False: claim(
        labels=["gate-processed", "bounty-eligible"]
    )
    gate._core.main = lambda: pytest.fail("eligible claim must stay terminal")

    assert gate.main() == 0


def test_bare_gate_processed_is_not_authoritative_terminal_state():
    gate = load_gate()
    gate.api = lambda path, method="GET", data=None, strict=False: claim(
        labels=["gate-processed"]
    )
    gate._core.main = lambda: None

    assert gate.main() == 1


@pytest.mark.parametrize("final_kind", ["needs-human", "bounty-eligible", "closed"])
def test_half_committed_marker_retries_until_authoritative_disposition(final_kind):
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    labels = set()
    state = "open"
    fail_final_once = True
    core_entry_labels = []

    def provider(path, method="GET", data=None, strict=False):
        nonlocal state, fail_final_once
        if path == issue_path and method == "GET":
            return claim(labels=sorted(labels), state=state)
        if path == f"{issue_path}/labels" and method == "POST":
            lab = data["labels"][0]
            if lab == "gate-processed":
                labels.add(lab)
                return {}
            if lab in {"needs-human", "bounty-eligible"}:
                if fail_final_once:
                    fail_final_once = False
                    raise gate.ApiError(f"transient {lab} mutation failure")
                labels.add(lab)
                return {}
        if path == issue_path and method == "PATCH" and data.get("state") == "closed":
            if fail_final_once:
                fail_final_once = False
                raise gate.ApiError("transient close mutation failure")
            state = "closed"
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path} {data!r}")

    def half_commit_core():
        issue = gate._core.api(issue_path)
        seen = {row["name"] for row in issue["labels"]}
        core_entry_labels.append(seen)
        # This is the preserved core's legacy idempotency rule.  Without the
        # wrapper replay repair, the second invocation would stop here and the
        # outer gate would incorrectly return rc=0 forever.
        if "gate-processed" in seen:
            return None
        gate._core.api(
            f"{issue_path}/labels", "POST", {"labels": ["gate-processed"]}
        )
        if final_kind in {"needs-human", "bounty-eligible"}:
            gate._core.api(
                f"{issue_path}/labels", "POST", {"labels": [final_kind]}
            )
        else:
            gate._core.api(
                issue_path, "PATCH", {"state": "closed", "state_reason": "not_planned"}
            )
        return None

    gate.api = provider
    gate._core.main = half_commit_core

    assert gate.main() == 1
    assert labels == {"gate-processed"}
    assert state == "open"

    assert gate.main() == 0
    assert core_entry_labels == [set(), set()]
    if final_kind == "closed":
        assert state == "closed"
    else:
        assert final_kind in labels


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
