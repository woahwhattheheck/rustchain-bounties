# From Accounts to UTXOs: RustChain’s Migration Safety Story

Type B script + storyboard package for `Scottcjn/rustchain-bounties#16601`.

**Pitch:** a source-grounded 4–5 minute code-tour showing how RustChain’s current migration machinery translates account balances into deterministic UTXO boxes without pretending the two ledger models are interchangeable. The story follows six safeguards in the pinned source: deterministic conversion, read-only dry-run, write-lock + preflight guards, mirror provenance, conservation + state-root integrity, and authenticated rollback.

## Package

- `script.md` — narration with claim tags `[S1]`–`[S9]`
- `storyboard.md` — exact shot/capture plan for a human editor
- `assembly.md` — timing and edit map
- `metadata.md` — titles, description, tags, chapters, thumbnail copy
- `SOURCES.md` — every technical claim mapped to immutable source URLs
- `thumbnail.png` + two alternates — original 1280×720 title cards

## Source pin

All RustChain technical claims are pinned to `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35` (fresh `main` when this package was built).

This package describes source behavior at that commit. It **does not claim** that a particular migration phase or dual-write mode is active on production nodes.

## Rights / publication

Original package by `woahwhattheheck`, prepared for the compensated #16601 distribution-package bounty. Elyan Labs may publish the package with permanent author attribution under the bounty terms. No third-party media is bundled.