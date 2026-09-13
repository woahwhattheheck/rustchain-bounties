# SPDX-License-Identifier: MIT
"""The PR-review-gate backfill sweep must fail CLOSED on issue enumeration.

`list_unprocessed()` must distinguish a genuinely empty repository from an API
failure, malformed response, or truncated discovery set. Discovery paginates
all open issues first; `MAX_PER_RUN` only bounds adjudication after the complete
queue is known.
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
