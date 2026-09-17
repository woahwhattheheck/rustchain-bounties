# #13226 fallback package — Scottcjn/homebrew-bottube

This package is a source-pinned, public fallback submission for `Scottcjn/rustchain-bounties#13226`, targeting exactly one RustChain-ecosystem repository: `Scottcjn/homebrew-bottube`.

## Source pin

Target default branch at preparation time:

- repository: `Scottcjn/homebrew-bottube`
- commit: `6dc43a4912d80661fc84adc2ac451f408ab1855a`
- tree: `09f7a618eb0c15725c768c9f1b4a5d7f4e71233c`

The pinned root has no `README.md` and no `llms.txt`. Its exact Homebrew formula inventory is:

- `Formula/bottube.rb` — blob `85d16fed4c31824c0031d06ab5a10daccfb008c6`; package source `bottube-1.5.0.tar.gz`; homepage `https://bottube.ai`; docs named by the formula: `https://bottube.ai/docs`
- `Formula/beacon.rb` — blob `406614963d4e4558b05e7b725c8469abae535fa5`; package source `beacon_skill-0.1.1.tar.gz`; homepage `https://bottube.ai/skills/beacon`; repository named by the formula: `https://github.com/Scottcjn/beacon-skill`
- `Formula/grazer.rb` — blob `93da0c14f5b0c11a213a245e1c297281a18ad354`; package source `grazer_skill-1.3.0.tar.gz`; homepage `https://bottube.ai/skills/grazer`

`BCOS.md` at the same pin identifies RustChain as the attestation chain and links the canonical RustChain repository at `https://github.com/Scottcjn/Rustchain`.

## Deliverables

- `llms.txt` — proposed root `llms.txt` with an answer-first summary, canonical links, entity profile, installation commands, and extractable FAQ.
- `README.patch` — proposed new root `README.md` because the pinned repository has no README. It provides a quotable definition sentence, install examples, exact current formula inventory, canonical links, and FAQ.

The content is intentionally documentation-only and does not change formulas, dependency hashes, tests, licensing, package behavior, or release metadata.

## Connector result

A direct GitHub-connector branch creation attempt against `Scottcjn/homebrew-bottube` from the pinned commit returned `403 Resource not accessible by integration` before any target mutation. The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publishing a document/patch/report in a repository controlled by the claimant as a fallback for this GitHub-App permission boundary.

## Applying upstream

1. Copy this package's `llms.txt` to repository root as `llms.txt`.
2. Apply `README.patch` to create the new root `README.md`.
3. Review against target main before opening the upstream PR in case the target has moved.

No sponsor acceptance, merge, RTC payment, or payout entitlement is asserted by this fallback package.