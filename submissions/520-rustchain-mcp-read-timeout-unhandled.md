# Bug Hunter #520 — `rustchain-mcp` read tools crash on transport timeouts

## Target

- Bounty: `Scottcjn/rustchain-bounties#520` — Bug Hunter, 3 RTC, multi-claim
- Repository: `Scottcjn/rustchain-mcp`
- Pinned source: `4b402e5a74575798610b4db8f7c4902682fc85f0`
- File: `rustchain_mcp/server.py`

## Summary

Three basic read-only MCP tools — `rustchain_health()`, `rustchain_epoch()`, and `rustchain_miners()` — call `get_client().get(...)` before entering the `try/except` that handles HTTP status failures. Their handlers catch only `httpx.HTTPStatusError` from `raise_for_status()`.

A real transport failure such as `httpx.ReadTimeout` or `httpx.ConnectError` therefore escapes the tool function instead of being represented as an agent-readable error result. This is inconsistent with `_get_rustchain_balance()` in the same pinned file, which explicitly handles `httpx.TimeoutException`, `httpx.RequestError`, and HTTP status errors.

## Relevant source shape

The pinned source has this pattern for the affected tools:

```python
r = get_client().get(...)
try:
    r.raise_for_status()
except httpx.HTTPStatusError:
    return {"error": ..., "status": ...}
```

Because `get_client().get(...)` is outside the `try`, timeout/connection exceptions raised there cannot be caught by the existing handler. Even if the call were moved inside the existing `try`, `ReadTimeout`/`ConnectError` are `RequestError` subclasses rather than `HTTPStatusError`, so an explicit transport-error branch is still required.

The contrast is visible in `_get_rustchain_balance()`, whose request is inside a `try` with dedicated `httpx.TimeoutException`, `httpx.RequestError`, and `httpx.HTTPStatusError` branches.

## Environment

- Reproduction OS: Linux x86_64
- Python: 3.13.5
- `httpx`: 0.28.1
- Network: fully mocked; no production endpoint or credentials are required
- Source pinned above; reproduction models the three function bodies exactly at that commit

## Deterministic reproduction

A client whose `get()` raises the same `httpx.ReadTimeout` class that a timed-out real request raises is sufficient:

```python
import httpx
import rustchain_mcp.server as server

class TimeoutClient:
    def get(self, url, **kwargs):
        request = httpx.Request("GET", url)
        raise httpx.ReadTimeout("synthetic timeout", request=request)

server._client = TimeoutClient()

for fn in (
    server.rustchain_health,
    server.rustchain_epoch,
    server.rustchain_miners,
):
    try:
        print(fn())
    except Exception as exc:
        print(fn.__name__, "RAISED", type(exc).__name__, str(exc))
```

Observed from an exact source-level harness:

```text
python 3.13.5 httpx 0.28.1
rustchain_health RAISED ReadTimeout synthetic timeout
rustchain_epoch RAISED ReadTimeout synthetic timeout
rustchain_miners RAISED ReadTimeout synthetic timeout
```

## Expected behavior

A temporary node or network failure should produce a stable, inspectable error result so an MCP caller can distinguish retryable transport trouble from healthy data. The existing balance helper already demonstrates a suitable contract with `UPSTREAM_TIMEOUT`, `TRANSPORT_RETRYABLE`, and structured HTTP failure cases.

## Actual behavior

`ReadTimeout` and other `httpx.RequestError` subclasses escape these three tool functions and become MCP tool failures.

## Impact

A transient outage makes health, epoch, and miner-list queries fail as uncaught tool errors. Callers cannot branch on a normal error payload or determine retryability, despite the server already doing so for balance reads.

## Suggested repair

1. Put both `get_client().get(...)` and `raise_for_status()` under the exception-handling path.
2. Handle `httpx.TimeoutException`, `httpx.RequestError`, and `httpx.HTTPStatusError` consistently with `_get_rustchain_balance()`.
3. Add offline regression tests using clients that raise `ReadTimeout` and `ConnectError` for all three tools.

## Duplicate check

Immediately before publication, GitHub issue search in `Scottcjn/rustchain-mcp` returned no issue matching `ReadTimeout`, `rustchain_epoch`, or `rustchain_miners`; searches for `rustchain_health` also returned no issue. Existing issue #232 is a documentation request for a stable error shape, not a report of this concrete uncaught transport-exception path.

## Submission state

A direct attempt to file this proper bug issue in `Scottcjn/rustchain-mcp` returned GitHub `403 Resource not accessible by integration`. The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents controlled-repository publication as a fallback for that connector-specific 403. This file is that public, timestamped fallback artifact; no sponsor acceptance or payout is asserted here.
