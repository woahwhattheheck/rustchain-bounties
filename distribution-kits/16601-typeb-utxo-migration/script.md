# Script — From Accounts to UTXOs: RustChain’s Migration Safety Story

Target runtime: ~4:30 at 145–155 words/minute.

## 0:00–0:30 — The dangerous sentence

> “We’re moving the ledger from account balances to UTXOs.”

That sounds like a database migration. It isn’t. It changes what the system means by *the same money*. In an account model, a wallet owns one balance. In a UTXO model, value lives in individually spendable boxes. If you copy balances carelessly, the same RTC can appear spendable in both worlds.

RustChain’s current source treats that conversion as a protocol event, not a `CREATE TABLE` exercise. [S1]

## 0:30–1:05 — Make the bridge deterministic

The genesis migration starts with a deliberately boring rule set: sort positive-balance wallets by `miner_id`; convert account micro-RTC into UTXO nano-RTC exactly; create one genesis box per wallet; derive each genesis transaction ID as SHA-256 of `rustchain_genesis:` plus the miner ID; and put those boxes at creation height zero. [S1][S2]

That matters because four nodes should not “mostly agree” about the conversion. Given the same account snapshot, they must derive the same boxes and therefore the same state root.

## 1:05–1:40 — Preview without touching the target

Before a real migration, the code has a dry-run path. It opens the SQLite database with `mode=ro`, explicitly avoids the normal connection helper that would enable WAL, and refuses a half-created UTXO schema. The preview builds the would-be boxes in memory and hashes *those* boxes to produce a preview root. [S3]

So “dry run” means observational: no schema initialization, no journal-mode side effect, no accidental UTXO write.

## 1:40–2:15 — Lock the snapshot, reject mixed state

The real path is stricter. It enters `BEGIN IMMEDIATE`, initializes the UTXO tables inside that write transaction, and then checks two things before copying value: genesis must not already exist, and non-genesis UTXO state must not already exist. [S4]

Only after taking that lock does it read balances for the migration snapshot. That closes a nasty timing gap: you do not want balances changing halfway through a conversion while boxes are being minted from an earlier view.

## 2:15–2:55 — Remember which money is a mirror

Here is the subtle part. Every migrated genesis box is also recorded in `account_mirror_boxes` with the source account wallet and value. [S5]

That provenance is more than bookkeeping. During a transition, the account row and the UTXO box can represent the same economic value. The system needs a durable way to know, “this box is the UTXO image of that account balance,” so reconciliation does not burn independently earned UTXOs or leave one value spendable twice.

The current integrity checker goes beyond comparing totals: it can assert per wallet that unspent mirror-box value does not exceed the corresponding account balance. [S8]

## 2:55–3:35 — UTXOs enforce conservation differently

Once value is in boxes, a transfer is not “subtract A, add B.” `apply_transaction()` validates input and output shapes, rejects duplicate input box IDs, rejects ordinary transactions with no inputs or no outputs, and enforces exact conservation: outputs plus fee must equal the consumed input value. [S6]

It then derives deterministic output box IDs, marks each input spent only if it was still unspent, inserts the outputs, and records the transaction. The write path uses an immediate transaction when it owns the connection, so validation and state mutation are tied together. [S6]

That is the mental model shift: balances become a set of spend-once objects, and conservation is checked at the object boundary.

## 3:35–4:05 — Give every node one fingerprint of state

After migration, RustChain computes a Merkle-style root over the complete contents of every unspent box, sorted by box ID. The leaf count is mixed into the leaf hash, and odd tree layers use a domain-separated padding hash instead of simply duplicating the last leaf. [S7]

The integrity check reports the unspent total, box count, state root, an optional comparison against the expected account-model total, and the per-wallet mirror-provenance check. [S8]

One number cannot prove every invariant, but these checks make disagreement observable instead of silent.

## 4:05–4:35 — Rollback is a protocol operation too

Even rollback is guarded. `rollback_genesis()` requires an admin key matching `RC_ADMIN_KEY`, takes `BEGIN IMMEDIATE`, refuses to remove genesis if non-genesis UTXO state exists, and clears mempool intent that depends on those deterministic genesis boxes. [S9]

That last step matters: recreating the same deterministic box while an old pending spend still claims it would resurrect stale intent.

## 4:35–4:50 — Close

So the migration safety story is not one magic switch. It is a chain of invariants: deterministic conversion, read-only preview, a locked snapshot, provenance for mirrored value, conservation at the UTXO boundary, state-root and per-wallet integrity checks, and an authenticated rollback path.

Changing ledger models safely means proving that every unit of value has changed *shape* without changing *ownership* — and leaving enough evidence for every node to agree on the result.