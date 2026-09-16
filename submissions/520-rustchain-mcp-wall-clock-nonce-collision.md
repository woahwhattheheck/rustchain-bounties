# Bug Hunter #520: `rustchain-mcp` wall-clock transfer nonces can collide or go backwards

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/520  
Target repository: https://github.com/Scottcjn/rustchain-mcp  
Target revision: `4b402e5a74575798610b4db8f7c4902682fc85f0`  
Affected path: `rustchain_mcp/server.py`  
Node behavior checked against: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

## Summary

`wallet_transfer_signed()` generates its replay-protection nonce directly from wall-clock milliseconds:

```python
nonce = int(time.time() * 1000)
```

The same value is included in the signed message and sent to `/wallet/transfer/signed`.

This nonce source is neither guaranteed unique nor strictly increasing for a wallet. Two calls that reach nonce generation during the same millisecond can generate the same nonce. A backward system-clock correction can also generate a nonce lower than one previously accepted by the node.

The RustChain node intentionally rejects both cases: duplicate nonces for one sender are rejected as `REPLAY_DETECTED`, and a nonce lower than the sender's latest accepted nonce is rejected as `OUT_OF_ORDER_NONCE`. The result is that legitimate MCP transfers can be rejected by replay protection even though they are distinct transactions.

This is an availability/correctness bug. It is **not** a replay-protection bypass and does not by itself permit unauthorized fund movement.

## Affected source

At the pinned `rustchain-mcp` revision, `wallet_transfer_signed()` contains:

```python
nonce = int(time.time() * 1000)
tx_data = {
    "from": wallet["address"],
    "to": to_address,
    "amount": float(amount_rtc),
    "memo": memo,
    "nonce": str(nonce),
}
transfer_message = json.dumps(
    tx_data, sort_keys=True, separators=(",", ":")
).encode()
signature = rustchain_crypto.sign_message(
    transfer_message, wallet["private_key"]
)

result = rustchain_transfer_signed(
    from_address=wallet["address"],
    to_address=to_address,
    amount_rtc=amount_rtc,
    signature=signature,
    public_key=wallet["public_key"],
    memo=memo,
    nonce=nonce,
)
```

Source permalink:
https://github.com/Scottcjn/rustchain-mcp/blob/4b402e5a74575798610b4db8f7c4902682fc85f0/rustchain_mcp/server.py

The existing signed-transfer regression tests verify message format, the fact that the nonce is signed as a string, payload field names, and signature compatibility. They do not verify that successive/concurrent client-generated nonces are unique and monotonic:

https://github.com/Scottcjn/rustchain-mcp/blob/4b402e5a74575798610b4db8f7c4902682fc85f0/tests/test_transfer_signed_message_format.py

## Environment

Reproduction environment used for the nonce-generation check:

- OS/kernel: Linux 6.18.44 x86_64, glibc 2.41
- Python: 3.13.5
- Target `rustchain-mcp`: `4b402e5a74575798610b4db8f7c4902682fc85f0`
- RustChain node source used to verify server behavior: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

No real on-chain transfer was required for this reproduction; the client-side collision and the node's duplicate/out-of-order rejection are independently deterministic.

## Steps to reproduce

### 1. Reproduce collisions in the exact nonce expression

Run:

```python
import time

vals = [int(time.time() * 1000) for _ in range(10_000)]
print(len(vals), len(set(vals)), min(vals), max(vals))
```

Observed in the environment above:

```text
10000 3 1789587009594 1789587009596
```

Ten thousand evaluations produced only three distinct nonce values because the expression has millisecond resolution. The exact count is machine-dependent; the invariant is that every evaluation within one wall-clock millisecond returns the same integer.

A deterministic same-tick demonstration is:

```python
frozen = 1789587000.123456
first = int(frozen * 1000)
second = int(frozen * 1000)
assert first == second == 1789587000123
```

Therefore two concurrent calls from the same local wallet that reach `nonce = int(time.time() * 1000)` during that tick sign different transfer bodies with the same replay nonce.

### 2. Verify the node rejects the duplicate nonce

The pinned RustChain repository already contains an exact regression test for the real `/wallet/transfer/signed` route:

`tests/test_signed_transfer_replay.py::test_signed_transfer_rejects_duplicate_nonce`

The test submits the same sender nonce twice. It asserts:

- first request: HTTP 200
- second request: HTTP 400
- response code: `REPLAY_DETECTED`
- error contains `Nonce already used`
- only one nonce and one pending transfer are recorded

Source:
https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/tests/test_signed_transfer_replay.py

### 3. Verify a backward nonce is rejected

The same test module contains `test_signed_transfer_rejects_out_of_order_nonce`. It submits nonce `1733420000002` successfully, then submits `1733420000001`. The second request is asserted to return HTTP 400 with:

```text
code = OUT_OF_ORDER_NONCE
latest_nonce = 1733420000002
```

A wall-clock step backward after a successful MCP transfer can therefore cause newly generated timestamps to be below the node's latest accepted nonce until clock time catches up.

## Expected behavior

For one sending wallet, every locally generated signed-transfer nonce should be unique and strictly increasing, including when:

- multiple tool calls execute concurrently;
- multiple calls start during the same millisecond;
- wall clock is corrected backward.

## Actual behavior

The nonce is a raw wall-clock millisecond value with no per-wallet synchronization, persisted last-nonce state, or monotonic correction. Same-millisecond calls can collide and clock rollback can regress the nonce.

## Impact

A legitimate transfer can be rejected as a replay solely because another legitimate transfer from the same wallet was generated in the same millisecond. Concurrent tool execution makes the collision case realistic. A backward clock correction can create a longer failure window in which otherwise valid later transfers are rejected as out of order.

Because the node correctly enforces replay protection, the failure is fail-closed: funds are not transferred by the rejected request. The user-facing effect is intermittent or sustained inability to submit valid transfers.

## Suggested fix

Maintain a synchronized last nonce per sending wallet and generate:

```python
candidate = int(time.time() * 1000)
next_nonce = max(candidate, last_nonce + 1)
```

The read/update must be atomic for concurrent calls. Persisting the latest generated/accepted nonce alongside local wallet state would also prevent regression across process restart when the wall clock has moved backward.

Regression coverage should freeze time and invoke two same-wallet transfers, asserting distinct strictly increasing submitted nonces. A second test should first generate a nonce, move the mocked wall clock backward, and assert the next generated nonce is still greater than the previous value.

## Duplicate check

Fresh searches on the pinned target found no issue for nonce collision, timestamp collision, or out-of-order client nonce generation. Existing `rustchain-mcp` PRs #248 and #249 repaired signed-message format and nonce threading, but do not make the nonce generator unique or monotonic. A fresh coordination search also found no owner or matching report for this exact defect.

## Submission-status note

The normal bounty flow requires a proper issue in the target repository and a link on bounty #520. Both target-repository issue creation and the bounty `/claim` comment were attempted through the connected GitHub App and returned `403 Resource not accessible by integration`. This file is the sponsor-documented public, timestamped fallback artifact for that connector-specific restriction.