# Sources / claim map

Technical source pin: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`.

The package intentionally uses immutable commit URLs. The narration claim tags map as follows.

## [S1] Migration is deterministic account→UTXO conversion

Source: [`node/utxo_genesis_migration.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_genesis_migration.py)

Evidence in source:
- module contract says existing account balances are converted into genesis UTXO boxes;
- wallets are sorted by `miner_id ASC`;
- one genesis box is created for each non-zero balance;
- genesis height is `0`;
- the proposition is derived from the miner address.

## [S2] Exact units and deterministic genesis transaction IDs

Source: [`node/utxo_genesis_migration.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_genesis_migration.py)

Evidence in source:
- `ACCOUNT_UNIT = 1_000_000` describes account-model micro-RTC;
- `ACCOUNT_TO_UTXO_SCALE = UNIT // ACCOUNT_UNIT` converts to the UTXO unit;
- legacy decimal balances are converted with `Decimal` and rejected if they exceed supported precision;
- `compute_genesis_tx_id()` hashes `rustchain_genesis:` + `miner_id` with SHA-256.

## [S3] Dry-run is observational and hashes the would-be boxes

Source: [`node/utxo_genesis_migration.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_genesis_migration.py)

Evidence in source:
- `_open_readonly()` opens SQLite with `?mode=ro`;
- dry-run comments explicitly avoid `UtxoDB._conn()` because it enables WAL;
- `_has_complete_utxo_schema()` rejects a partial UTXO schema;
- dry-run collects `preview_boxes` instead of inserting rows;
- the reported dry-run state root is `_state_root_from_boxes(preview_boxes)`, not current disk state.

## [S4] Real migration locks the snapshot and rejects mixed UTXO state

Source: [`node/utxo_genesis_migration.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_genesis_migration.py)

Evidence in source:
- non-dry-run migration enters `BEGIN IMMEDIATE`;
- it aborts if genesis UTXO transactions already exist;
- it aborts if non-genesis UTXO state already exists;
- balances are loaded through the same transaction connection so the copied snapshot is consistent with the acquired lock.

## [S5] Migrated boxes carry account-mirror provenance

Source: [`node/utxo_genesis_migration.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_genesis_migration.py)

Evidence in source:
- real migration creates/updates `account_mirror_boxes`;
- each row binds `box_id`, `account_wallet`, `value_nrtc`, and `created_epoch`;
- the adjacent comment explains that the provenance lets confirmation reconcile the mirrored account value without relying on a fragile register marker or burning independently earned UTXOs.

## [S6] UTXO transaction application is atomic and conservation-checked

Source: [`node/utxo_db.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_db.py)

Evidence in source:
- `apply_transaction()` describes atomic input spending/output creation;
- when it owns the transaction it uses `BEGIN IMMEDIATE` and rolls back on validation failure;
- duplicate input box IDs are rejected;
- ordinary transactions require at least one input and at least one output;
- `output_total + fee` must exactly equal `input_total` for spending transactions;
- input rows are updated with `WHERE ... spent_at IS NULL`, and every update must affect exactly one row;
- deterministic box IDs are derived for the outputs before insertion.

## [S7] State root is deterministic and cardinality-bound

Source: [`node/utxo_db.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_db.py)

Evidence in source:
- `compute_state_root()` orders all unspent boxes by `box_id`;
- complete box contents are serialized with stable key ordering;
- the leaf count is mixed into each leaf hash;
- odd layers use `SHA256(0x01 || last_hash)` padding rather than duplicating the last leaf;
- the docstring states nodes with the same UTXO set produce the same root.

## [S8] Integrity checks compare models and also enforce a per-wallet mirror invariant

Source: [`node/utxo_db.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_db.py)

Evidence in source:
- `integrity_check()` reports unspent total, box count, and state root;
- when `expected_total` is supplied it records `models_agree` and fails on a total mismatch;
- `_check_mirror_provenance()` additionally verifies per wallet that unspent account-mirror UTXO value does not exceed that wallet’s account-model balance.

## [S9] Rollback is authenticated, atomic, and cleans dependent pending intent

Source: [`node/utxo_genesis_migration.py`](https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/utxo_genesis_migration.py)

Evidence in source:
- `rollback_genesis()` calls `_require_rollback_authorization()`;
- authorization fails closed when `RC_ADMIN_KEY` is unset and compares the supplied key with `hmac.compare_digest`;
- rollback enters `BEGIN IMMEDIATE`;
- it refuses rollback while non-genesis UTXO state exists;
- it identifies deterministic genesis box IDs and evicts dependent mempool transactions inside the rollback transaction.

## Bounty brief

[`Scottcjn/rustchain-bounties#16601`](https://github.com/Scottcjn/rustchain-bounties/issues/16601) defines Type B as a script + storyboard production kit, requires factual grounding in public repos, and requires a public GitHub delivery package.

## Scope statement

These sources establish **code behavior at the pinned commit**. They do not establish which migration or dual-write flags are enabled on live nodes, so the narration and metadata deliberately avoid deployment-state claims.