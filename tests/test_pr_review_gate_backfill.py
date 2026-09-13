# SPDX-License-Identifier: MIT
"""The PR-review-gate backfill sweep must fail CLOSED and remain fair.

`list_unprocessed()` must distinguish a genuinely empty repository from an API
failure, malformed response, or truncated discovery set. Discovery paginates
all open issues first; `MAX_PER_RUN` only bounds adjudication after the complete
queue is known. Bounded scheduling must also advance across repeated runs so a
permanently unresolved prefix cannot starve later contributors forever.
"""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


def load_backfill():
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "pr_review_gate_backfill.py"
    )
    spec = importlib.util.spec_from_file_location("pr_review_gate_backfill_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeGate:
    """Minimal stand-in for the gate module's is_review_claim() classifier."""

    @staticmethod
    def is_review_claim(title):
        return title.startswith("Bounty #73 claim")


def _completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["gh", "api"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_gh_nonzero_exit_fails_closed(monkeypatch):
    """Issue enumeration failing with empty stdout must NOT read as zero claims."""
    mod = load_backfill()
    monkeypatch.setattr(
        mod.subprocess, "run", lambda *a, **k: _completed(1, stdout="", stderr="HTTP 503")
    )
    with pytest.raises(SystemExit) as exc:
        mod.list_unprocessed(FakeGate())
    assert exc.value.code == 1


def test_malformed_json_on_success_fails_closed(monkeypatch):
    """Exit 0 with truncated/garbage JSON must NOT read as zero claims."""
    mod = load_backfill()
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _completed(0, stdout="{"))
    with pytest.raises(SystemExit) as exc:
        mod.list_unprocessed(FakeGate())
    assert exc.value.code == 1


def test_unexpected_slurp_shape_fails_closed(monkeypatch):
    """A mixed pagination shape must not be treated as a complete queue."""
    mod = load_backfill()
    payload = [[{"number": 1, "title": "x", "labels": []}], {"oops": True}]
    monkeypatch.setattr(
        mod.subprocess, "run", lambda *a, **k: _completed(0, stdout=json.dumps(payload))
    )
    with pytest.raises(SystemExit) as exc:
        mod.list_unprocessed(FakeGate())
    assert exc.value.code == 1


def test_empty_issue_list_on_success_is_a_real_zero(monkeypatch):
    """A genuine empty list on a zero exit is a real zero, not a failure."""
    mod = load_backfill()
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _completed(0, stdout="[]"))
    never, stranded = mod.list_unprocessed(FakeGate())
    assert never == []
    assert stranded == []


def test_normal_path_partitions_claims(monkeypatch):
    """The fix must not break normal classification of open claims."""
    mod = load_backfill()
    issues = [
        {"number": 5, "title": "Bounty #73 claim: review of PR #100", "labels": []},
        {"number": 6, "title": "Bounty #73 claim: review of PR #101",
         "labels": [{"name": "needs-human"}]},
        {"number": 7, "title": "Bounty #73 claim: review of PR #102",
         "labels": [{"name": "bounty-eligible"}]},
        {"number": 8, "title": "unrelated issue", "labels": []},
    ]
    monkeypatch.setattr(
        mod.subprocess, "run", lambda *a, **k: _completed(0, stdout=json.dumps(issues))
    )
    never, stranded = mod.list_unprocessed(FakeGate())
    assert never == [5]
    assert stranded == [6]


def test_slurped_pages_are_all_classified_and_pull_requests_are_excluded(monkeypatch):
    """Discovery must flatten every REST page rather than silently cap at 1,000."""
    mod = load_backfill()
    pages = [
        [
            {"number": 5, "title": "Bounty #73 claim: review of PR #100", "labels": []},
            {"number": 55, "title": "Bounty #73 claim: review of PR #999", "labels": [],
             "pull_request": {"url": "https://example.test/pr/55"}},
        ],
        [
            {"number": 1005, "title": "Bounty #73 claim: review of PR #101",
             "labels": [{"name": "needs-human"}]},
        ],
    ]
    monkeypatch.setattr(
        mod.subprocess, "run", lambda *a, **k: _completed(0, stdout=json.dumps(pages))
    )
    never, stranded = mod.list_unprocessed(FakeGate())
    assert never == [5]
    assert stranded == [1005]


def test_two_runs_reach_persistent_stranded_claim_beyond_first_max():
    """A stable first batch cannot starve claim MAX+1 across repeated runs."""
    mod = load_backfill()
    stranded = list(range(1, 62))

    new0, retry0 = mod.select_batch([], stranded, max_per_run=60, run_number=0)
    new1, retry1 = mod.select_batch([], stranded, max_per_run=60, run_number=1)

    assert new0 == []
    assert new1 == []
    assert len(retry0) == 60
    assert len(retry1) == 60
    assert 61 not in retry0
    assert 61 in retry1
    assert set(retry0) | set(retry1) == set(stranded)


def test_rotation_crosses_never_and_stranded_boundary():
    """A full never-adjudicated prefix must not starve stranded retries forever."""
    mod = load_backfill()
    never = list(range(1, 61))
    stranded = [1001, 1002]

    new0, retry0 = mod.select_batch(never, stranded, max_per_run=60, run_number=0)
    new1, retry1 = mod.select_batch(never, stranded, max_per_run=60, run_number=1)

    assert new0 == never
    assert retry0 == []
    assert retry1 == stranded
    assert len(new1) == 58
    assert set(new0 + retry0 + new1 + retry1) >= set(stranded)


def test_nonpositive_max_per_run_is_rejected():
    """Zero/negative bounds must fail closed rather than trigger slice surprises."""
    mod = load_backfill()
    with pytest.raises(ValueError, match="MAX_PER_RUN must be > 0"):
        mod.select_batch([1], [2], max_per_run=0, run_number=1)
    with pytest.raises(ValueError, match="MAX_PER_RUN must be > 0"):
        mod.select_batch([1], [2], max_per_run=-1, run_number=1)


def test_main_rejects_nonpositive_max_before_discovery(monkeypatch):
    """Runtime config validation must stop before any issue enumeration/mutation."""
    mod = load_backfill()
    monkeypatch.setattr(mod, "MAX_PER_RUN", 0)
    monkeypatch.delenv("GITHUB_RUN_NUMBER", raising=False)

    def should_not_load_gate():
        raise AssertionError("invalid config must fail before loading/discovering claims")

    monkeypatch.setattr(mod, "_load_gate", should_not_load_gate)
    assert mod.main() == 2


def test_invalid_actions_run_number_is_rejected(monkeypatch):
    """A malformed durable rotation seed must fail closed, not silently reset."""
    mod = load_backfill()
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "not-an-int")
    with pytest.raises(ValueError, match="GITHUB_RUN_NUMBER must be an integer"):
        mod._rotation_run_number()
