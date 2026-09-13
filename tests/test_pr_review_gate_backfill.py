import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pr_review_gate_backfill.py"
spec = importlib.util.spec_from_file_location("pr_review_gate_backfill", MODULE_PATH)
backfill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backfill)


class _Gate:
    @staticmethod
    def is_review_claim(title):
        return "review" in title.lower()


def test_list_unprocessed_fails_closed_when_issue_discovery_command_fails():
    failed = SimpleNamespace(returncode=1, stdout="", stderr="rate limited")

    with patch.object(backfill.subprocess, "run", return_value=failed):
        with pytest.raises(backfill.GhError, match="exited 1"):
            backfill.list_unprocessed(_Gate())


def test_list_unprocessed_fails_closed_on_malformed_discovery_json():
    malformed = SimpleNamespace(returncode=0, stdout="not-json", stderr="")

    with patch.object(backfill.subprocess, "run", return_value=malformed):
        with pytest.raises(backfill.GhError, match="unparseable JSON"):
            backfill.list_unprocessed(_Gate())


def test_main_returns_nonzero_when_claim_discovery_fails(monkeypatch):
    monkeypatch.setattr(backfill, "_load_gate", lambda: _Gate())
    monkeypatch.setattr(
        backfill,
        "list_unprocessed",
        lambda gate: (_ for _ in ()).throw(backfill.GhError("transport failed")),
    )

    assert backfill.main() == 1


def test_list_unprocessed_still_classifies_successful_discovery():
    payload = """[
      {"number": 10, "title": "Code review claim", "labels": []},
      {"number": 11, "title": "PR review claim", "labels": [{"name": "needs-human"}]},
      {"number": 12, "title": "PR review claim", "labels": [{"name": "bounty-eligible"}]},
      {"number": 13, "title": "Not a claim", "labels": []}
    ]"""
    succeeded = SimpleNamespace(returncode=0, stdout=payload, stderr="")

    with patch.object(backfill.subprocess, "run", return_value=succeeded):
        never, stranded = backfill.list_unprocessed(_Gate())

    assert never == [10]
    assert stranded == [11]
