# Bug report: rustchain-monitor silently reports canonical wallet balances as zero

**Bounty:** Scottcjn/rustchain-bounties#520 — Bug Hunter (3 RTC, multi-claim)  
**Target repository:** `Scottcjn/rustchain-monitor`  
**Pinned target commit:** `ee410625c1c5d738eaa9acd5469c48d77eb61e35`  
**Affected file:** `rustchain_monitor.py`  
**Canonical API reference:** `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`, `docs/api/REFERENCE.md`

## Summary

`RustChainMonitor.get_miner_balance()` reads only a `balance_rtc` JSON key from `/wallet/balance`. The current canonical RustChain API contract returns `amount_rtc` and `amount_i64` instead. A successful non-zero balance response therefore silently becomes `0.0` inside rustchain-monitor.

That incorrect zero is consumed by `get_miner_snapshot()` and can then be persisted by `record_history()`, so watch/history/reward-trend surfaces may show or store a false zero balance even though the node returned a valid non-zero balance.

## Affected source

At the pinned rustchain-monitor commit, the implementation is:

```python
def get_miner_balance(self, miner_id: str) -> float:
    """Get specific miner's RTC balance"""
    response = self.session.get(f"{self.node_url}/wallet/balance?miner_id={miner_id}")
    return response.json().get("balance_rtc", 0.0)
```

`get_miner_snapshot()` immediately uses this value:

```python
balance = self.get_miner_balance(miner_id)
...
return {
    "epoch": current_epoch,
    "balance_rtc": balance,
    ...
}
```

and `record_history()` stores `snapshot["balance_rtc"]` into the local history database.

## Current documented API contract

The pinned RustChain API reference documents:

```json
{
  "ok": true,
  "miner_id": "scott",
  "amount_rtc": 42.5,
  "amount_i64": 42500000
}
```

for `GET /wallet/balance?miner_id={NAME}`.

There is no `balance_rtc` key in that documented success shape.

## Deterministic reproduction

Environment used for the local deterministic probe:

- Linux 6.18.44 x86_64, glibc 2.41
- Python 3.13.5
- rustchain-monitor source pin: `ee410625c1c5d738eaa9acd5469c48d77eb61e35`

Minimal reproduction of the exact key lookup performed by the method:

```python
payload = {
    "ok": True,
    "miner_id": "scott",
    "amount_rtc": 42.5,
    "amount_i64": 42500000,
}

returned_balance = payload.get("balance_rtc", 0.0)
print("canonical_payload=", payload)
print("returned_balance=", returned_balance)
```

Observed output:

```text
canonical_payload= {'ok': True, 'miner_id': 'scott', 'amount_rtc': 42.5, 'amount_i64': 42500000}
returned_balance= 0.0
```

The node supplied a valid 42.5 RTC balance, but rustchain-monitor's lookup converts it to zero.

## Expected behavior

A successful canonical response should return `amount_rtc` (`42.5` in the example), or the monitor should explicitly reject an unexpected/malformed response shape. It should not synthesize a valid-looking zero balance when the requested key name is absent.

## Actual behavior

Any successful response that follows the documented `amount_rtc` / `amount_i64` schema but does not also expose the non-contract `balance_rtc` alias is returned as `0.0`.

## Impact

This is a silent data-integrity failure rather than a visible crash:

- a miner with funds can be displayed as having zero RTC;
- a false zero can be persisted into the history database;
- later snapshots can produce misleading balance deltas and trend output;
- operators can mistake a client/schema mismatch for a real wallet state because the fallback value is indistinguishable from a genuine zero balance.

## Suggested fix

Prefer the canonical key, optionally retaining the old key only as an explicit compatibility alias, and validate the response before returning a default. For example:

```python
payload = response.json()
if not isinstance(payload, dict):
    raise ValueError("wallet balance response must be a JSON object")
if "amount_rtc" in payload:
    return float(payload["amount_rtc"])
if "balance_rtc" in payload:  # compatibility only, if still desired
    return float(payload["balance_rtc"])
raise ValueError("wallet balance response missing amount_rtc")
```

A regression test should feed the documented success payload and assert that `get_miner_balance()` returns `42.5`, not `0.0`.

## Duplicate / collision check

Before taking this lane:

- GitHub issue searches in `Scottcjn/rustchain-monitor` for `amount_rtc` and `balance_rtc` returned no matching issue.
- Slack search for `rustchain-monitor` + `amount_rtc` returned no collision.
- Slack search for `rustchain-monitor` + `balance_rtc` returned one separate Z-CASSINI build order about rejecting `NaN` / `Infinity`; that is a distinct numeric-validation defect, not this response-schema mismatch.

## Submission-path note

The proper first-party bug issue was attempted in `Scottcjn/rustchain-monitor` first. The GitHub App write returned `403 Resource not accessible by integration`.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a repository the contributor controls, followed by a link, as an accepted route when a GitHub App is blocked by that 403. This report is the timestamped public deliverable under that documented fallback. No sponsor acceptance or payout is asserted here.
