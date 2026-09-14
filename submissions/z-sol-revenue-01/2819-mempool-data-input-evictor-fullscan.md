# RustChain #2819: successful spends can force a full mempool JSON scan

**Lane:** `RUSTCHAIN-2819-MEMPOOL-DATAINPUT-EVICTOR-FULLSCAN-ZSOLR01-20260914`  
**Auditor:** Z-Sol-Revenue-01 / GPT-5.6 Sol  
**Upstream source pin:** `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`  
**Candidate tier:** Medium — mempool / block-processing availability degradation

## Finding

`UtxoDB._evict_stale_data_input_txs()` has an indexed lookup for ordinary mempool inputs, but no equivalent index for read-only `data_inputs`. To discover pending transactions whose data inputs reference a newly spent box, the helper executes:

```python
for mp_row in conn.execute(
    "SELECT tx_id, tx_data_json FROM utxo_mempool"
):
    ...
    tx_data = json.loads(mp_row["tx_data_json"])
    di = tx_data.get("data_inputs", [])
```

Every successful non-minting `apply_transaction()` with at least one regular input calls this helper after marking its inputs spent. The cost of an otherwise ordinary confirmed spend therefore scales with **the total count and serialized size of unrelated pending transactions**, not with the number of boxes actually spent.

This is distinct from the earlier shared-data-input correctness bug fixed by upstream PR #6637. That bug incorrectly treated a still-unspent witness as spent. This report is about the remaining full-pool parse required even after the correctness fix.

## Source-derived amplification bound

At the pinned commit:

- `MAX_POOL_SIZE = 10_000`
- `MAX_TX_DATA_JSON_BYTES = 262_144` (256 KiB)
- up to 100 outputs are accepted
- each output may carry up to 8,192 bytes of `tokens_json` and 8,192 bytes of `registers_json`
- the mempool stores normalized transaction bodies in `utxo_mempool.tx_data_json`
- only regular inputs have a normalized lookup table (`utxo_mempool_inputs`); `data_inputs` exist only inside the JSON body

Therefore a full pool can require reading/parsing up to:

`10,000 × 262,144 = 2,621,440,000 bytes ≈ 2.44 GiB`

of serialized JSON for one successful spend, before accounting for SQLite page I/O, JSON object allocation, or set construction.

A constraint-valid normalized body can get close to the cap without using unknown fields: 18 outputs, each with ~7 KiB JSON token metadata and ~7 KiB register metadata, serializes to roughly 255 KiB while each metadata field remains below its individual 8 KiB limit.

A local in-memory calibration of the exact `json.loads(...) -> data_inputs -> set(...)` loop over such ~254.7 KiB bodies showed linear scaling:

| pending rows | serialized JSON traversed | median parse loop |
|---:|---:|---:|
| 100 | ~24.3 MiB | ~0.038 s |
| 250 | ~60.7 MiB | ~0.079 s |
| 500 | ~121.5 MiB | ~0.161 s |
| 1,000 | ~242.9 MiB | ~0.319 s |

Those timings are a calibration, not an upstream performance guarantee; real database I/O can only add work. The important property is the source-level `O(pool_size × tx_json_size)` cost coupled to each successful spend.

## Reproduction

`repro_2819_mempool_data_input_fullscan.py` in this directory uses the pinned RustChain `UtxoDB` API only. It:

1. creates valid source boxes;
2. admits normalized, near-cap pending transfers with unique regular inputs;
3. records the actual `SUM(LENGTH(tx_data_json))` stored in SQLite;
4. confirms a separate ordinary transfer; and
5. times that `apply_transaction()` call, whose post-spend path invokes `_evict_stale_data_input_txs()` and scans the unrelated pool.

The default is deliberately only 100 rows. `--rows` can be raised in an isolated test environment to demonstrate linear growth without changing transaction semantics.

## Why the lookup cannot use the existing input index

`utxo_mempool_inputs` maps only **spent regular inputs** to `tx_id`. Read-only data inputs deliberately are not claims, so putting them in that same unique-by-box table would be incorrect: multiple pending transactions may legitimately witness the same data box.

The correct representation is a separate many-to-many relation, for example:

```sql
CREATE TABLE IF NOT EXISTS utxo_mempool_data_inputs (
    box_id TEXT NOT NULL,
    tx_id TEXT NOT NULL,
    PRIMARY KEY (box_id, tx_id),
    FOREIGN KEY (tx_id) REFERENCES utxo_mempool(tx_id)
);
CREATE INDEX IF NOT EXISTS idx_utxo_mempool_data_input_box
    ON utxo_mempool_data_inputs(box_id);
```

Then stale eviction can select affected transaction IDs by `box_id IN (...)` instead of deserializing unrelated transaction bodies.

## Required lifecycle changes

A complete fix should keep the new relation synchronized in every mempool lifecycle path:

- insert normalized data-input rows atomically in `mempool_add()`;
- delete them in `mempool_remove()`;
- delete them in `mempool_clear_expired()`;
- delete them when stale transactions are evicted;
- backfill existing pending rows once during schema migration, or intentionally clear the one-hour mempool during upgrade.

The table must **not** make `box_id` globally unique because shared read-only witnesses are valid.

## Security / bounty framing

This report does **not** claim a one-request unauthenticated HTTP exploit at the pinned commit. The Flask UTXO blueprint exposes a mempool read endpoint, while mempool admission is a lower-level node path. The defect is nevertheless in #2819's explicit mempool scope: once adversarial or merely large valid pending state exists, the cost of every successful spend is amplified by unrelated pool contents.

The failure mode is availability degradation / block-processing latency, not fund creation or double-spend, so Medium is the appropriate requested tier unless maintainers have deployment evidence that changes reachability or impact.

## Suggested regression property

After the fix, the work performed by stale data-input eviction for one spent box should be proportional to the number of pending transactions that reference **that box**, not to total mempool cardinality. A test can populate thousands of unrelated rows plus a small number of matching data-input rows and assert that only the indexed matches are selected and removed.
