# SPDX-License-Identifier: MIT
"""Zero-network custody tests for PR-review inline-comment evidence."""
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "pr_review_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location(
        "pr_review_gate_inline_comment_test", GATE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO = "Scottcjn/rustchain-bounties"
    mod.NUM = "42"
    mod.TARGET = "Scottcjn/Rustchain"
    mod.CAP = 15
    mod.RATE = "3"
    return mod


def claim():
    return {
        "state": "open",
        "labels": [],
        "title": "Code review bounty #73 PR #10",
        "body": "RTC" + "a" * 40,
        "user": {"login": "alice"},
    }


def review(body="LGTM"):
    return {
        "submitted_at": "2026-09-13T00:00:00Z",
        "body": body,
        "state": "COMMENTED",
        "user": {"login": "alice"},
    }


def test_inline_comment_transport_failure_fails_closed_without_rejecting_claim():
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    inline_path = "/repos/Scottcjn/Rustchain/pulls/10/comments?per_page=100"
    writes = []

    def provider(path, method="GET", data=None, strict=False):
        if path == issue_path and method == "GET":
            return claim()
        if path == "/repos/Scottcjn/Rustchain/pulls/10/reviews":
            return [review()]
        if path == inline_path:
            assert strict is True
            raise gate.ApiError("GET inline comments -> HTTP 429")
        if method in {"POST", "PATCH"}:
            writes.append((path, method, data))
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path}")

    gate.api = provider

    assert gate.main() == 1
    assert any(
        path == f"{issue_path}/labels"
        and method == "POST"
        and data == {"labels": ["gate-processed"]}
        for path, method, data in writes
    )
    assert not any(method == "PATCH" for _, method, _ in writes)
    assert not any(
        path == f"{issue_path}/labels"
        and method == "POST"
        and data in (
            {"labels": ["bounty-eligible"]},
            {"labels": ["needs-human"]},
        )
        for path, method, data in writes
    )


def test_inline_comment_pagination_finds_claimant_evidence_on_page_two():
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    page1 = "/repos/Scottcjn/Rustchain/pulls/10/comments?per_page=100"
    page2 = f"{page1}&page=2"
    writes = []
    comment_reads = []

    first_page = [{"user": {"login": f"noise-{i}"}} for i in range(100)]
    second_page = [{"user": {"login": "alice"}}]

    def provider(path, method="GET", data=None, strict=False):
        if path == issue_path and method == "GET":
            return claim()
        if path == "/repos/Scottcjn/Rustchain/pulls/10/reviews":
            return [review()]
        if path == page1:
            comment_reads.append((path, strict))
            assert strict is True
            return first_page
        if path == page2:
            comment_reads.append((path, strict))
            assert strict is True
            return second_page
        if path.startswith("/search/issues?"):
            assert strict is True
            return {"total_count": 0}
        if method in {"POST", "PATCH"}:
            writes.append((path, method, data))
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path}")

    gate.api = provider

    assert gate.main() == 0
    assert comment_reads == [(page1, True), (page2, True)]
    assert any(
        path == f"{issue_path}/labels"
        and method == "POST"
        and data == {"labels": ["bounty-eligible"]}
        for path, method, data in writes
    )
    assert not any(method == "PATCH" for _, method, _ in writes)


def test_later_inline_comment_page_failure_is_not_laundered_as_complete():
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    page1 = "/repos/Scottcjn/Rustchain/pulls/10/comments?per_page=100"
    page2 = f"{page1}&page=2"
    writes = []

    def provider(path, method="GET", data=None, strict=False):
        if path == issue_path and method == "GET":
            return claim()
        if path == "/repos/Scottcjn/Rustchain/pulls/10/reviews":
            return [review()]
        if path == page1:
            assert strict is True
            return [{"user": {"login": "noise"}} for _ in range(100)]
        if path == page2:
            assert strict is True
            raise gate.ApiError("GET inline comments page 2 -> HTTP 403")
        if method in {"POST", "PATCH"}:
            writes.append((path, method, data))
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path}")

    gate.api = provider

    assert gate.main() == 1
    assert not any(method == "PATCH" for _, method, _ in writes)
    assert not any(
        data == {"labels": ["bounty-eligible"]}
        for _, method, data in writes
        if method == "POST"
    )


def test_malformed_inline_comment_page_fails_closed():
    gate = load_gate()
    issue_path = "/repos/Scottcjn/rustchain-bounties/issues/42"
    inline_path = "/repos/Scottcjn/Rustchain/pulls/10/comments?per_page=100"
    writes = []

    def provider(path, method="GET", data=None, strict=False):
        if path == issue_path and method == "GET":
            return claim()
        if path == "/repos/Scottcjn/Rustchain/pulls/10/reviews":
            return [review()]
        if path == inline_path:
            assert strict is True
            return {"message": "not a list"}
        if method in {"POST", "PATCH"}:
            writes.append((path, method, data))
            return {}
        raise AssertionError(f"unexpected provider call: {method} {path}")

    gate.api = provider

    assert gate.main() == 1
    assert not any(method == "PATCH" for _, method, _ in writes)
    assert not any(
        data == {"labels": ["bounty-eligible"]}
        for _, method, data in writes
        if method == "POST"
    )
