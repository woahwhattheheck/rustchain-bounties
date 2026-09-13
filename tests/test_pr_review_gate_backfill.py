# SPDX-License-Identifier: MIT
"""Hostiles for the PR-review-gate backfill safety net."""
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
    mod = load_backfill()
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *a, **k: _completed(1, stdout="", stderr="HTTP 503"),
    )
    with pytest.raises(SystemExit) as exc:
        mod.list_unprocessed(FakeGate())
    assert exc.value.code == 1


def test_malformed_json_on_success_fails_closed(monkeypatch):
    mod = load_backfill()
    monkeypatch.setattr(
        mod.subprocess, "run", lambda *a, **k: _completed(0, stdout="{")
    )
    with pytest.raises(SystemExit) as exc:
        mod.list_unprocessed(FakeGate())
    assert exc.value.code == 1


def test_unexpected_slurp_shape_fails_closed(monkeypatch):
    mod = load_backfill()
    payload = [[{"number": 1, "title": "x", "labels": []}], {"oops": True}]
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *a, **k: _completed(0, stdout=json.dumps(payload)),
    )
    with pytest.raises(SystemExit) as exc:
        mod.list_unprocessed(FakeGate())
    assert exc.value.code == 1


def test_empty_issue_list_on_success_is_real_zero(monkeypatch):
    mod = load_backfill()
    monkeypatch.setattr(
        mod.subprocess, "run", lambda *a, **k: _completed(0, stdout="[]")
    )
    assert mod.list_unprocessed(FakeGate()) == ([], [])


def test_normal_path_partitions_and_retry_marker_retires_stranded(monkeypatch):
    mod = load_backfill()
    issues = [
        {
            "number": 5,
            "title": "Bounty #73 claim: review of PR #100",
            "labels": [],
        },
        {
            "number": 6,
            "title": "Bounty #73 claim: review of PR #101",
            "labels": [{"name": "needs-human"}, {"name": "gate-processed"}],
        },
        {
            "number": 7,
            "title": "Bounty #73 claim: review of PR #102",
            "labels": [
                {"name": "needs-human"},
                {"name": "gate-processed"},
                {"name": mod.RETRY_MARKER_LABEL},
            ],
        },
        {
            "number": 8,
            "title": "Bounty #73 claim: review of PR #103",
            "labels": [{"name": "bounty-eligible"}],
        },
        {"number": 9, "title": "unrelated issue", "labels": []},
    ]
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *a, **k: _completed(0, stdout=json.dumps(issues)),
    )
    never, stranded = mod.list_unprocessed(FakeGate())
    assert never == [5]
    assert stranded == [6]


def test_slurped_pages_all_classified_and_pull_requests_excluded(monkeypatch):
    mod = load_backfill()
    pages = [
        [
            {
                "number": 5,
                "title": "Bounty #73 claim: review of PR #100",
                "labels": [],
            },
            {
                "number": 55,
                "title": "Bounty #73 claim: review of PR #999",
                "labels": [],
                "pull_request": {"url": "https://example.test/pr/55"},
            },
        ],
        [
            {
                "number": 1005,
                "title": "Bounty #73 claim: review of PR #101",
                "labels": [{"name": "needs-human"}],
            }
        ],
    ]
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *a, **k: _completed(0, stdout=json.dumps(pages)),
    )
    assert mod.list_unprocessed(FakeGate()) == ([5], [1005])


def test_dynamic_never_growth_cannot_suppress_stranded_retry():
    """Exact rereview hostile: 120 new + one S still reserves S immediately."""
    mod = load_backfill()
    never = list(range(1, 121))
    stranded = [9999]
    batch_new, batch_retry = mod.select_batch(
        never, stranded, max_per_run=60, run_number=1
    )
    assert len(batch_new) == 59
    assert batch_retry == [9999]
    assert len(batch_new) + len(batch_retry) == 60

    next_never = list(range(121, 301))
    next_stranded = [10000]
    batch_new, batch_retry = mod.select_batch(
        next_never, next_stranded, max_per_run=60, run_number=2
    )
    assert len(batch_new) == 59
    assert batch_retry == [10000]


def test_retry_marker_progress_reaches_claim_beyond_first_max():
    """Selected stranded claims retire by marker, so MAX+1 advances next run."""
    mod = load_backfill()
    stranded = list(range(1, 62))
    _, first = mod.select_batch([], stranded, max_per_run=60, run_number=0)
    assert first == list(range(1, 61))

    remaining = [number for number in stranded if number not in set(first)]
    _, second = mod.select_batch([], remaining, max_per_run=60, run_number=1)
    assert second == [61]


def test_both_classes_get_reserved_capacity_when_cap_at_least_two():
    mod = load_backfill()
    new, retry = mod.select_batch(
        list(range(1, 61)), [1001, 1002], max_per_run=60, run_number=0
    )
    assert len(new) == 58
    assert retry == [1001, 1002]
    assert len(new) + len(retry) == 60


def test_single_slot_alternates_classes():
    mod = load_backfill()
    never = [1, 2]
    stranded = [1001, 1002]
    assert mod.select_batch(never, stranded, 1, 0) == ([1], [])
    assert mod.select_batch(never, stranded, 1, 1) == ([], [1001])
    assert mod.select_batch(never, stranded, 1, 2) == ([1], [])


def test_unused_capacity_spills_to_other_class():
    mod = load_backfill()
    new, retry = mod.select_batch([1], list(range(100, 110)), 6, 0)
    assert new == [1]
    assert len(retry) == 5
    assert len(new) + len(retry) == 6


def test_nonpositive_max_per_run_is_rejected():
    mod = load_backfill()
    with pytest.raises(ValueError, match="MAX_PER_RUN must be > 0"):
        mod.select_batch([1], [2], max_per_run=0, run_number=1)
    with pytest.raises(ValueError, match="MAX_PER_RUN must be > 0"):
        mod.select_batch([1], [2], max_per_run=-1, run_number=1)


def test_invalid_actions_run_number_is_rejected(monkeypatch):
    mod = load_backfill()
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "not-an-int")
    with pytest.raises(ValueError, match="GITHUB_RUN_NUMBER must be an integer"):
        mod._rotation_run_number()


def test_main_rejects_nonpositive_max_before_discovery(monkeypatch):
    mod = load_backfill()
    monkeypatch.setattr(mod, "MAX_PER_RUN", 0)
    monkeypatch.delenv("GITHUB_RUN_NUMBER", raising=False)

    def should_not_load_gate():
        raise AssertionError("invalid config must fail before loading claims")

    monkeypatch.setattr(mod, "_load_gate", should_not_load_gate)
    assert mod.main() == 2


def test_retry_marker_is_persisted_before_retry_adjudication(monkeypatch):
    mod = load_backfill()
    events = []
    monkeypatch.setattr(mod, "_load_gate", lambda: FakeGate())
    monkeypatch.setattr(mod, "list_unprocessed", lambda gate: ([], [1001]))
    monkeypatch.setattr(mod, "ensure_retry_marker_label", lambda: True)

    def mark(number):
        events.append(("mark", number))
        return True

    def adjudicate(number, retry=False):
        events.append(("adjudicate", number, retry))
        return True

    monkeypatch.setattr(mod, "mark_retry_attempt", mark)
    monkeypatch.setattr(mod, "adjudicate", adjudicate)
    monkeypatch.setattr(mod, "MAX_PER_RUN", 60)
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "3")

    assert mod.main() == 0
    assert events == [
        ("mark", 1001),
        ("adjudicate", 1001, True),
    ]


def test_marker_write_failure_blocks_retry_and_fails_run(monkeypatch):
    mod = load_backfill()
    monkeypatch.setattr(mod, "_load_gate", lambda: FakeGate())
    monkeypatch.setattr(mod, "list_unprocessed", lambda gate: ([], [1001]))
    monkeypatch.setattr(mod, "ensure_retry_marker_label", lambda: True)
    monkeypatch.setattr(mod, "mark_retry_attempt", lambda number: False)
    monkeypatch.setattr(
        mod,
        "adjudicate",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("gate must not run without durable marker")
        ),
    )
    monkeypatch.setattr(mod, "MAX_PER_RUN", 60)
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "4")

    assert mod.main() == 1


def test_retry_label_creation_failure_fails_without_adjudication(monkeypatch):
    mod = load_backfill()
    monkeypatch.setattr(mod, "_load_gate", lambda: FakeGate())
    monkeypatch.setattr(mod, "list_unprocessed", lambda gate: ([], [1001, 1002]))
    monkeypatch.setattr(mod, "ensure_retry_marker_label", lambda: False)
    monkeypatch.setattr(
        mod,
        "mark_retry_attempt",
        lambda number: (_ for _ in ()).throw(
            AssertionError("no marker writes after label setup failure")
        ),
    )
    monkeypatch.setattr(
        mod,
        "adjudicate",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("no gate runs after label setup failure")
        ),
    )
    monkeypatch.setattr(mod, "MAX_PER_RUN", 60)
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "5")

    assert mod.main() == 1
