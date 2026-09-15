# Bounty #16471 — `pr_review_gate.py` top-level issue fetch fails open

## Scope and source pin

This report covers one silent-success defect in the current public payout/review pipeline, specifically `scripts/pr_review_gate.py` in `Scottcjn/rustchain-bounties`.

Source reviewed: `main`, file blob `d94de135a8765656e04fc94d42122f82ec231336`.

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/16471

## Finding

The gate's authoritative first read of the claim issue is a **non-strict** GitHub GET. A transient HTTP failure can therefore be converted into `None`, after which `main()` returns normally. The process exits successfully even though the claim was never adjudicated and no durable retry/hold state was written.

The helper has this behavior for non-strict GETs:

```python
except urllib.error.HTTPError as e:
    if strict:
        raise ApiError(...)
    if method == "GET":
        return None
```

The first operation in `main()` is then effectively:

```python
iss = api(f"/repos/{REPO}/issues/{NUM}")
if not iss or iss.get("state") != "open":
    return
```

The module wrapper only exits non-zero when an exception escapes `main()`. Here no exception escapes: the failed GET is converted to `None`, `main()` returns, and the process exits 0.

## Concrete wrong-effect path

1. A legitimate code-review claim is newly opened or edited and triggers the gate.
2. The first `GET /repos/<repo>/issues/<number>` receives a transient 403, 429, 5xx, or another HTTP failure handled by the non-strict branch.
3. `api()` returns `None`.
4. `main()` treats that exactly like a missing/non-open issue and returns immediately.
5. No `needs-human`, `gate-processed`, or `bounty-eligible` label is written, and no explanatory comment is posted.
6. The script nevertheless exits 0, so the workflow can appear green while the claim received zero adjudication.

This is a silent-success failure in the bounty's stated class: the runner reports success while the intended effect — deciding or durably holding the claim — does not happen.

## Bounded reproduction

The current control flow can be reproduced without touching GitHub or the payout node:

```python
calls = []

def api_stub(*args, **kwargs):
    return None  # current non-strict GET failure result


def main_stub():
    iss = api_stub("/repos/example/repo/issues/999")
    if not iss or iss.get("state") != "open":
        return
    calls.append("mutated")

assert main_stub() is None
assert calls == []
```

The real module's `__main__` wrapper only calls `sys.exit(1)` for an escaped exception, so this branch exits successfully.

## Distinctness from prior #16471 findings

This is not the previously reported `gh issue list`/candidate-enumeration failure, malformed `_list()` JSON fallback, review/comment pagination, cap-lookup failure, bot-claimant handling, or review-list failure. It happens **before the gate has loaded the issue body, author, labels, PR reference, or reviews at all**. The only failed dependency needed is the top-level claim issue GET itself.

## Suggested fix

Make the authoritative claim read fail closed. For example, call the API with `strict=True`, or otherwise raise if the issue read cannot be completed. A real closed/not-found issue can still be treated as non-actionable, but “could not read the issue” must be distinguishable from “issue is not open” so the workflow becomes visibly red and retry machinery can act.

A focused regression should stub the initial issue GET to fail and assert a non-zero process result rather than a green no-op.

## Submission receipt

A direct comment submission to `Scottcjn/rustchain-bounties#16471` through the connected GitHub App returned `403 Resource not accessible by integration`. The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a contributor-controlled repository as a fallback for this connector-specific failure. This file is that public, timestamped handoff artifact.

Payout destination: `woahwhattheheck` (hosted RTC wallet handle).
