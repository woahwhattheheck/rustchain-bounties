# #520 Bug Hunter — rustchain-claim-portal MCP integer overflow returns HTTP 500

Target: `Scottcjn/rustchain-claim-portal`

Pinned target main: `46fd99ce53a4ab3ee62c07a96791e087bec490c4`

Relevant source blobs:
- `app/mcp_tools.py`: `15994304fd685d803d0b5e443c4029faf62b5e6e`
- `app/mcp.py`: `ac2df5ebd32c5bd03a250bff0842b62b7fb797e5`

Reproduction environment: Python 3.13.5

## Summary

The public read-only `/mcp` endpoint accepts syntactically valid JSON numeric values such as `1e309` for advertised integer arguments. Python's JSON decoder turns that value into `float('inf')`. The integer helpers in `app/mcp_tools.py` call `int(raw_value)` but catch only `TypeError` and `ValueError`; `int(float('inf'))` raises `OverflowError`, which therefore escapes the intended `MCPInvalidArguments` path.

`app/mcp.py` catches that unexpected exception only in its generic `except Exception:` handler, so the request becomes an HTTP 500 with JSON-RPC `-32603` (`internal error`) instead of an invalid-params response.

## Affected paths

`app/mcp_tools.py`:

- `_positive_int()` — used by `portal.claim_history.limit`.
- `_bridge_int_arg()` — used by bridge event, transfer and reconciliation `limit`, `offset`, `window_seconds`, and `epoch` arguments.

Both helpers contain the same conversion shape:

```python
try:
    value = int(raw_value)
except (TypeError, ValueError) as exc:
    raise MCPInvalidArguments(...) from exc
```

`OverflowError` is not handled.

`app/mcp.py` accepts `arguments` as a dictionary and dispatches it directly through `call_mcp_tool()`; it does not validate the request against the advertised tool JSON Schemas before dispatch. Its handlers distinguish `MCPInvalidArguments` from unexpected exceptions, with the latter becoming HTTP 500 / JSON-RPC `-32603`.

## Reproduction

Example request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "bridge.events.list",
    "arguments": {"limit": 1e309}
  }
}
```

Minimal proof of the exact decode/conversion path:

```python
import json

value = json.loads('{"limit":1e309}')["limit"]
print(value)  # inf
int(value)
# OverflowError: cannot convert float infinity to integer
```

The same malformed numeric value can reach other `_bridge_int_arg()` consumers (`epoch`, `offset`, `window_seconds`, reconciliation limits) and `_positive_int()` (`portal.claim_history.limit`).

## Actual behavior

The conversion raises uncaught `OverflowError`. The MCP endpoint reaches its generic exception handler and returns an HTTP 500 with JSON-RPC `-32603` / `internal error`.

## Expected behavior

Out-of-range or non-finite numeric values should be rejected as invalid tool arguments (`-32602`) without producing a server error.

## Suggested fix

Either require native JSON integers before conversion (`isinstance(raw_value, int) and not isinstance(raw_value, bool)`), explicitly reject non-finite numbers, or catch `OverflowError` together with `TypeError` and `ValueError`. Add endpoint regression coverage for `1e309` on the integer arguments.

## Validation and duplicate checks

- Target main was read fresh and pinned to the SHA above before reporting.
- Fresh target issue search found no existing issue matching MCP `OverflowError`, `1e309`, or this integer-conversion failure.
- Fresh workspace Slack search found no active `rustchain-claim-portal` lane before the claim was announced.
- The exact Python JSON-decoding and helper-conversion primitive was executed under Python 3.13.5 and reproduced `OverflowError` deterministically.
- A full repository checkout/test run was not possible in the execution container because DNS resolution for `github.com` failed; this report does not claim a full Flask-suite run.

## Submission status

A proper target issue was attempted through the GitHub connector and returned `403 Resource not accessible by integration`. A `/claim` comment on `Scottcjn/rustchain-bounties#520` returned the same 403.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publishing the deliverable in a controlled repository and attempting a file PR when this GitHub-App limitation occurs. This file is the public, timestamped fallback artifact for that route.
