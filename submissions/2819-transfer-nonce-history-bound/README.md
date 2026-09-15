# #2819 — UTXO signed-transfer nonce history grows without bound

Target bounty: https://github.com/Scottcjn/rustchain-bounties/issues/2819

Upstream source reviewed: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

Affected path: `node/utxo_endpoints.py`

Suggested tier: **Low (25 RTC)** as a code-quality/resource-bound defect, with maintainer discretion if the reachable storage-DoS impact merits a higher tier.

Payout identity: `woahwhattheheck` (GitHub handle).

## Finding

`/utxo/transfer` persists every successful signed-transfer nonce forever in the `transfer_nonces` table:

```sql
CREATE TABLE IF NOT EXISTS transfer_nonces (
    from_address TEXT NOT NULL,
    nonce TEXT NOT NULL,
    used_at INTEGER NOT NULL,
    PRIMARY KEY (from_address, nonce)
)
```

Each transfer calls `_reserve_transfer_nonce()`, which inserts a fresh `(from_address, nonce)` row. The same handler then enforces strict monotonicity with:

```sql
SELECT MAX(CAST(nonce AS INTEGER)) FROM transfer_nonces
WHERE from_address = ? AND nonce != ?
```

and rejects a transfer when the previous maximum is greater than or equal to the new nonce.

That invariant means old successful nonce rows are no longer needed for replay safety. Once nonce `N` has committed, every nonce `< N` is already rejected by the monotonicity check, and nonce `N` itself can remain as the one current replay sentinel.

Current code never removes superseded rows. Therefore one authenticated funded wallet can append one durable SQLite row per successful transfer forever.

## Reproduction / impact

A wallet can repeatedly transfer a dust-threshold amount to itself with sequential nonces. The endpoint accepts a zero requested fee, so this does not require burning value: the same value can be consumed and recreated as a new UTXO while `transfer_nonces` gains another permanent row.

The storage growth is linear in successful transfers for a single wallet. The table's composite primary key also grows its SQLite index with the history.

I reproduced the exact nonce-table SQL locally with 5,000 increasing accepted nonces:

```text
current rows/latest = (5000, 5000)
proposed rows/latest = (1, 5000)
stale nonce 7 accepted? False in both cases
```

The included `reproduce_nonce_history_growth.py` is a standalone deterministic SQLite reproduction of the current reservation/monotonicity logic and the proposed compaction.

This finding does **not** claim fund theft, double spend, or conservation bypass. It is a bounded-state/resource defect. The UTXO bounty itself notes this layer is pre-production / feature-flagged, which limits present production impact.

## Proposed fix

After the transfer and any dual-write shadow updates have succeeded, but before the surrounding SQLite transaction commits, delete superseded nonce rows for that wallet:

```python
conn.execute(
    "DELETE FROM transfer_nonces WHERE from_address = ? AND nonce != ?",
    (from_address, nonce),
)
```

Doing this inside the same `BEGIN IMMEDIATE` transaction preserves atomicity:

- if the transfer later rolls back, nonce history rolls back too;
- after a successful commit, exactly the latest nonce row remains;
- exact replay of the latest nonce is still rejected by `INSERT OR IGNORE` / `SELECT changes()`;
- any older nonce is still rejected because the retained latest nonce makes `previous_nonce >= nonce` true;
- other wallets are unaffected because the delete is scoped by `from_address`.

The included patch adds that one bounded-state cleanup plus a regression in `node/test_utxo_endpoints.py` that performs three successful increasing-nonce transfers, asserts only the latest row remains, and confirms an older nonce is still rejected as `OUT_OF_ORDER_NONCE` without changing balances.

## Duplicate boundary

Before taking this lane I checked:

- the full #2819 comment thread for `transfer_nonces`, `prune`, and unbounded nonce-history language;
- current Slack coordination/delegation searches for `transfer_nonces`;
- current Rustchain issue/PR search for nonce pruning.

The only `transfer_nonces` hit in #2819 was a different claim about a nonce allegedly leaking on `apply_transaction()` failure. This report is specifically about **successful transfers retaining every superseded nonce forever**.

I also avoided the separately active #2819 account-mirror / unreachable-409 lane.

## Submission-path note

A direct branch creation attempt against `Scottcjn/Rustchain` for this patch returned `403 Resource not accessible by integration`. The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a repository the contributor controls as a fallback for this connector-specific 403. This package is that public, timestamped fallback artifact.
