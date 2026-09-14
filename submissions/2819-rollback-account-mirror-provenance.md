# #2819 low-severity finding: `rollback_genesis()` leaves stale `account_mirror_boxes` provenance

## Scope and source identity

This report is for **Scottcjn/rustchain-bounties #2819** (UTXO red-team bounty), low-severity code-quality / test-gap category.

Reviewed source:

- `Scottcjn/Rustchain` main commit: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`
- `node/utxo_genesis_migration.py` blob: `a7609c2806728fe061a45b59b1c0aa704d2e943c`
- `node/utxo_db.py` blob: `af2111d142d3254750e3cc0c65b4182354ae7329`

I am **not** claiming fund creation, theft, or a production-network exploit. The UTXO layer is still feature-gated per the bounty. This is a rollback-consistency defect and missing regression case.

## Vulnerability / defect class

**Incomplete rollback / orphaned provenance state.**

`migrate()` creates an `account_mirror_boxes` table and inserts one provenance row for every genesis mirror box:

```sql
CREATE TABLE IF NOT EXISTS account_mirror_boxes (
    box_id TEXT PRIMARY KEY,
    account_wallet TEXT NOT NULL,
    value_nrtc INTEGER NOT NULL,
    created_epoch INTEGER NOT NULL
)
```

followed by:

```sql
INSERT OR REPLACE INTO account_mirror_boxes
(box_id, account_wallet, value_nrtc, created_epoch) VALUES (?,?,?,?)
```

`rollback_genesis()` correctly runs under one `BEGIN IMMEDIATE`, discovers the genesis box IDs, evicts mempool dependencies, deletes the matching rows from `utxo_boxes`, then deletes `utxo_transactions WHERE tx_type = 'genesis'`.

However, it never deletes the corresponding rows from `account_mirror_boxes`. That table has no foreign key to `utxo_boxes`, so deleting the box cannot cascade. After a successful rollback, provenance for boxes that no longer exist remains in the database.

## Why this matters

The function's contract is to remove the genesis migration state so the migration can be cleanly rolled back/re-run. A successful rollback currently leaves a third piece of migration state behind.

For an unchanged wallet balance, a later migration happens to reuse the same deterministic `box_id` and `INSERT OR REPLACE` masks the stale row. But that does not make the rollback complete. If balances change between rollback and re-run (for example, a previously-positive account becomes zero and therefore receives no new genesis box), the old provenance row survives indefinitely and points at a deleted box.

Current consumers often join provenance back to `utxo_boxes`, which limits immediate impact, but the database invariant is still false and future code can reasonably treat `account_mirror_boxes` as authoritative provenance. This is exactly the sort of state-cleanliness regression a rollback test should catch.

## Reproduction

A focused reproducer is included next to this report:

`submissions/2819-rollback-account-mirror-provenance-poc.py`

Run it from a checkout of the pinned RustChain commit:

```bash
RUSTCHAIN_ROOT=/path/to/Rustchain \
  python3 submissions/2819-rollback-account-mirror-provenance-poc.py
```

The script creates a fresh SQLite database with one positive account balance, calls the real `migrate()`, verifies one genesis box / one genesis transaction / one mirror-provenance row, then calls the real `rollback_genesis()` with a local test admin key. The final assertion expects all three migration-state classes to be gone.

Expected final state:

```text
boxes=0
genesis_txs=0
mirror_rows=0
```

Current-source state:

```text
boxes=0
genesis_txs=0
mirror_rows=1
```

I also replayed the exact deletion sequence against an isolated SQLite schema matching these three tables. Observed counts were:

```text
before rollback: {'utxo_boxes': 1, 'utxo_transactions': 1, 'account_mirror_boxes': 1}
after rollback:  {'utxo_boxes': 0, 'utxo_transactions': 0, 'account_mirror_boxes': 1}
```

The remaining row retained the deleted genesis `box_id`, wallet, value and epoch.

## Expected vs actual

**Expected:** `rollback_genesis()` removes all state created solely to represent the genesis migration, including provenance rows for the boxes it deletes.

**Actual:** genesis boxes and genesis transaction rows are deleted, but `account_mirror_boxes` retains orphan rows because rollback never touches that table and no FK/cascade exists.

## Suggested fix

Inside the existing `BEGIN IMMEDIATE`, delete provenance for the captured `genesis_box_ids` before deleting `utxo_boxes` (guarding for databases created before the provenance table existed), for example:

```python
if genesis_box_ids:
    have_mirror_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='account_mirror_boxes'"
    ).fetchone()
    if have_mirror_table:
        placeholders = ",".join("?" for _ in genesis_box_ids)
        conn.execute(
            f"DELETE FROM account_mirror_boxes WHERE box_id IN ({placeholders})",
            genesis_box_ids,
        )
```

A schema-level foreign key with `ON DELETE CASCADE` could also enforce the invariant, but that requires a migration for existing databases. The targeted delete is the least invasive repair.

Add a regression test that:

1. migrates one positive account,
2. confirms the mirror provenance row exists,
3. rolls genesis back,
4. asserts `utxo_boxes`, genesis `utxo_transactions`, and matching `account_mirror_boxes` are all empty,
5. changes/removes the account balance before a re-run to prove stale provenance cannot survive by relying on deterministic-ID replacement.

## Bounty classification

Requested classification: **Low severity / code quality + test coverage gap (25 RTC tier)**. This report intentionally does not claim a higher-severity exploit.
