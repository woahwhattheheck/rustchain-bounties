# Bug report — openclaw-x402 consumes a paid transaction before the paid tool succeeds

**Bounty:** Scottcjn/rustchain-bounties#520 — Bug Hunter (3 RTC, multi-claim)  
**Target:** `Scottcjn/openclaw-x402`  
**Pinned target main:** `483005c673f7704a84413720a450342f723a815e`  
**Affected file:** `openclaw_x402/mcp_server.py`

## Summary

The paid MCP path marks a verified RustChain transaction as spent **before** the paid tool's backend operation has succeeded. If the backend then returns a transient non-200 response or raises, `premium_search()` and `miner_profile()` return a successful paid wrapper containing fallback/stub data, while the transaction is already permanently present in the local `spent_tx` ledger. A retry with that same payment is rejected as a replay.

This means a caller can pay for a tool invocation, receive no actual backend result because the service is temporarily unavailable, and then be forced to pay a second time to retry.

## Source behavior on the pinned head

`_verify_payment()` verifies `/api/tx/<tx_id>` and, for a matching transaction, immediately calls `_consume_tx(tx_id, tool_name)`. `_consume_tx()` inserts the transaction into SQLite with `tx_id` as the primary key. Only after `_gate()` returns success do the paid tools perform their actual backend lookup.

`premium_search()` then requests `/api/ledger`; if that request fails or returns non-200, it still returns `_paid_result(...)` with:

```json
{
  "matches": [],
  "query": "...",
  "note": "Ledger search unavailable, returning stub."
}
```

`miner_profile()` has the same ordering and returns a paid stub on lookup failure.

The existing payment-helper tests cover malformed token JSON, insufficient amount, wrong treasury, missing chain sender, verification network failure, and missing transactions, but do not cover a backend/service failure **after** payment verification/consumption.

## Deterministic reproduction

Environment used for the reproduction:

- Linux x86_64, kernel 6.18.44
- Python 3.13.5
- `httpx` 0.28.1
- SQLite 3.46.1

I used a deterministic local harness mirroring the pinned `_consume_tx`, `_verify_payment`, `_gate`, `_paid_result`, and `premium_search` logic. No live funds or production writes were used.

Stubbed responses:

1. `GET /api/tx/tx-paid-once` → HTTP 200 with a valid 0.10 RTC transaction to the configured treasury from `payer-1`.
2. `GET /api/ledger?q=alice&limit=20` → HTTP 503 to model a transient backend outage.

Payment token:

```json
{"tx_id":"tx-paid-once","from":"payer-1","amount":0.1}
```

### First invocation

The transaction verifies, is inserted into `spent_tx`, the ledger lookup returns 503, and the paid tool still returns:

```json
{
  "status": "ok",
  "payment": {
    "amount": 0.1,
    "currency": "RTC",
    "tx_id": "tx-paid-once"
  },
  "result": {
    "matches": [],
    "note": "Ledger search unavailable, returning stub.",
    "query": "alice"
  }
}
```

### Retry with the same verified payment

```json
{
  "status": "payment_failed",
  "error": "Payment token already used. Each transaction pays for exactly one call -- send a new payment."
}
```

Observed call sequence:

```text
GET /api/tx/tx-paid-once -> 200 valid payment
GET /api/ledger?q=alice&limit=20 -> 503 transient failure
retry: GET /api/tx/tx-paid-once -> 200, then local spent_tx rejects tx-paid-once as replay
```

## Expected behavior

A verified transaction should not become irreversibly consumed until the paid operation has successfully produced its service result. If concurrency requires reservation before execution, the reservation should have explicit pending/committed states and be released on a retryable backend failure.

A backend outage should also not be wrapped as `status: "ok"` with a successful payment receipt when the requested service result was not delivered.

## Impact

This is a payment-integrity/reliability bug. A transient RustChain/backend outage can charge an MCP caller without delivering the requested result, while replay protection prevents the caller from retrying with the payment it already made. At least `premium_search()` and `miner_profile()` follow this ordering.

## Suggested fix

Separate payment verification/reservation from final consumption:

1. Verify the on-chain transaction and reserve its `tx_id` atomically.
2. Execute the paid operation.
3. Mark the transaction committed/spent only after successful service completion.
4. Release a pending reservation on a retryable tool/backend failure.
5. Return a non-`ok`, retryable service failure instead of a paid-success stub when the backend is unavailable.

Add regression coverage where transaction verification succeeds but the tool backend returns HTTP 503 or raises. Assert both that the first response is a service failure and that the same verified transaction can be retried after the transient failure without a replay rejection.

## Duplicate check

Fresh target issue searches found no existing report for payment consumption before backend/service success or for retry loss after a paid backend failure. `Scottcjn/openclaw-x402#18` is a different issue covering malformed payment-token shapes/non-finite amounts; issues #1/#11 concern earlier header-verification bypasses.

## Submission routing / connector receipt

A proper target issue was attempted first through the GitHub connector and returned:

```text
403 Resource not accessible by integration
```

The RustChain bounty submission guide explicitly documents controlled-repository publication, followed by a file-PR attempt where possible, as accepted fallback routing for that connector-specific 403. This report is published through that path so the evidence is public, timestamped, and independently reviewable.

No payout or maintainer acceptance is asserted by this report.