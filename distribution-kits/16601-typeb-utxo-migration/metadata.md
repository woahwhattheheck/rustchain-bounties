# Publication metadata

## Primary title

**How RustChain Moves Money from Accounts to UTXOs Without Duplicating It**

## Alternate titles

1. **Inside RustChain’s Account→UTXO Migration Safety Checks**
2. **Same RTC, New Ledger Model: A Source-Level Migration Tour**

## One-line pitch

A 4–5 minute source tour of the invariants RustChain uses to turn account balances into deterministic UTXO boxes while preserving ownership and making divergence observable.

## Description

Moving from account balances to UTXOs is not a table migration: the system has to prove that value changed representation without becoming spendable twice.

This video walks through RustChain’s migration code at immutable source commit `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`: deterministic genesis-box construction, a truly read-only dry-run, `BEGIN IMMEDIATE` snapshot locking, `account_mirror_boxes` provenance, UTXO conservation, deterministic state roots, per-wallet integrity checks, and authenticated rollback.

The video describes source behavior at the pinned commit; it does not claim any specific migration phase or dual-write mode is enabled on production nodes.

Source repository: https://github.com/Scottcjn/Rustchain
Bounty / distribution brief: https://github.com/Scottcjn/rustchain-bounties/issues/16601
Author: `woahwhattheheck`

## Chapters

- 0:00 The dangerous sentence
- 0:30 Deterministic conversion
- 1:05 A dry run that really is read-only
- 1:40 Locking the migration snapshot
- 2:15 Why mirror provenance matters
- 2:55 Conservation in the UTXO model
- 3:35 State roots and integrity checks
- 4:05 Guarded rollback
- 4:35 Change the shape, preserve ownership

## Tags

`RustChain`, `UTXO`, `blockchain engineering`, `ledger migration`, `SQLite`, `distributed systems`, `state integrity`, `cryptocurrency`, `developer tools`, `source code walkthrough`

## Thumbnail copy

Primary: `ACCOUNTS → UTXOs` / `WITHOUT DUPLICATING VALUE`

Alternate 1: `SAME RTC` / `NEW LEDGER MODEL`

Alternate 2: `MIGRATE ONCE` / `PROVE THE RESULT`

## Attribution / disclosure

Prepared by `woahwhattheheck` for the compensated `Scottcjn/rustchain-bounties#16601` Type B distribution-package bounty. Elyan Labs may publish this package under the bounty terms with permanent author attribution. No acceptance or payout is asserted by this package itself.