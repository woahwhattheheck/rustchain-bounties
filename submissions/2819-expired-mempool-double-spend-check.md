# RustChain bounty #2819 — expired mempool claims remain visible to `mempool_check_double_spend()`

## Scope and source pin

- Bounty: `Scottcjn/rustchain-bounties#2819` — UTXO red-team review
- Target repository: `Scottcjn/Rustchain`
- Reviewed commit: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`
- Exact source path: `node/utxo_db.py`
- Exact test path reviewed for overlap: `node/test_utxo_db.py`
- Classification: low-severity correctness / API-contract edge case; not a fund-moving exploit

I also checked the currently open #2819-related PRs `Scottcjn/Rustchain#8302` and `#8332`. Their reported findings cover conservation/value validation, stale-cleanup atomicity, JSON-parsing amplification, mutable coin-selection references, box-ID encoding width, and an error-information leak. This finding is distinct.

## Finding

`UtxoDB.mempool_check_double_spend(box_id)` says it returns `True` when a box is claimed by a **pending** mempool transaction, but it tests only whether a row exists in `utxo_mempool_inputs`:

```python
def mempool_check_double_spend(self, box_id: str) -> bool:
    """Return True if box_id is claimed by a pending mempool TX."""
    conn = self._conn()
    try:
        row = conn.execute(
            "SELECT tx_id FROM utxo_mempool_inputs WHERE box_id = ?",
            (box_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
```

The query neither joins `utxo_mempool` to check `expires_at` nor calls `mempool_clear_expired()` first. Therefore an expired transaction remains reported as a live double-spend claim until an unrelated path happens to perform expiry cleanup.

That differs from other public mempool helpers in the same file. For example, `mempool_add()` and `mempool_get_block_candidates()` call `mempool_clear_expired()` before relying on pending state.

## Reproduction

1. Create a UTXO for `alice`.
2. Add a valid transfer to the mempool that claims Alice's box.
3. Update that row's `expires_at` to `int(time.time()) - 1`, exactly as the existing expiry test does.
4. Call `mempool_check_double_spend(box_id)` **before** any method that clears expired rows.

Observed from the current implementation: the method returns `True`, because the `utxo_mempool_inputs` claim row still exists.

Expected: `False`, because the only parent transaction is expired and is no longer a pending mempool transaction.

Focused regression test:

```python
def test_mempool_double_spend_check_ignores_expired_claims(self):
    self._apply_coinbase('alice', 100 * UNIT, block_height=1)
    box = self.db.get_unspent_for_address('alice')[0]
    tx_id = 'expired-check' * 5

    self.assertTrue(self.db.mempool_add({
        'tx_id': tx_id,
        'inputs': [{'box_id': box['box_id']}],
        'outputs': [{'address': 'bob', 'value_nrtc': 100 * UNIT - 1000}],
        'fee_nrtc': 1000,
    }))

    conn = self.db._conn()
    try:
        conn.execute(
            'UPDATE utxo_mempool SET expires_at = ? WHERE tx_id = ?',
            (int(time.time()) - 1, tx_id),
        )
        conn.commit()
    finally:
        conn.close()

    self.assertFalse(self.db.mempool_check_double_spend(box['box_id']))
```

On the reviewed implementation, the final assertion fails: the method returns `True` until cleanup is triggered elsewhere.

## Impact

This is not a conservation bypass and does not create or move RTC. It is a stale-state correctness bug in the mempool API.

Any caller that uses `mempool_check_double_spend()` directly as the authority for whether a box is currently reserved can reject an otherwise valid spend after the claiming transaction has expired. The false positive lasts until another code path runs expiry cleanup. That makes behavior dependent on unrelated traffic/order of operations and contradicts the method's documented definition of a pending claim.

The current in-repo tests cover expiry cleanup through `mempool_add()` / block-candidate selection and verify `mempool_check_double_spend()` after stale candidate eviction, but they do not exercise the direct expired-claim boundary above.

## Suggested fix

Prefer making the predicate correct by construction rather than relying on a side-effecting cleanup call. Join the claim to its parent mempool row and require a live expiry:

```python
def mempool_check_double_spend(self, box_id: str) -> bool:
    """Return True if box_id is claimed by a live pending mempool TX."""
    conn = self._conn()
    try:
        row = conn.execute(
            """SELECT 1
               FROM utxo_mempool_inputs mi
               JOIN utxo_mempool m ON m.tx_id = mi.tx_id
               WHERE mi.box_id = ? AND m.expires_at > ?
               LIMIT 1""",
            (box_id, int(time.time())),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
```

This keeps the helper read-only, treats orphan claim rows as non-live, and does not make a simple predicate acquire the write lock used by `mempool_clear_expired()`.

The regression test above should accompany the fix.

## Duplicate checks performed before claiming

- Fresh GitHub issue search in `Scottcjn/Rustchain` for `mempool_check_double_spend`: no issue results.
- Fresh GitHub search for `expired mempool double spend`: no matching report of this edge case.
- Fresh Slack exact-symbol search for `mempool_check_double_spend`: no result.
- Reviewed open #2819 PRs #8302 and #8332; neither reports this stale-expiry predicate bug.

## Publication

Canonical fallback artifact:
https://github.com/woahwhattheheck/rustchain-bounties/blob/b1b57b9c788a3a5d5da0e69f419af3bf87bab924/submissions/2819-expired-mempool-double-spend-check.md
