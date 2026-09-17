# Bounty #13226 — `Scottcjn/rustchain-rips` GEO/AEO package

This is a source-pinned, ready-to-apply fallback package for [Scottcjn/rustchain-bounties#13226](https://github.com/Scottcjn/rustchain-bounties/issues/13226), targeting exactly one ecosystem repository: [`Scottcjn/rustchain-rips`](https://github.com/Scottcjn/rustchain-rips).

## Source pin

- Target repository: `Scottcjn/rustchain-rips`
- Target branch: `main`
- Target commit: `a1ecdb2069388eb314840c5808521d0e59debbe7`
- Existing `README.md` blob: `efbe36802a21801f5814e0146178b63960b8860d`
- Existing root `llms.txt`: absent at the pinned commit
- Existing `CONTRIBUTING.md` blob: `156ddbeae41d71594e023a22a0f815777cd1128c`

## Deliverable

`target/` contains the exact proposed repository state for the two bounty-owned paths:

- `target/llms.txt` — root llms.txt with a project summary, canonical links, key entities, status/source guidance, and extractable questions and answers.
- `target/README.md` — the pinned README with a single answer-first definition plus a concise FAQ. The current RIP index and RIP-300 content are preserved verbatim.

No RIP specification, protocol status, reward rule, or implementation behavior is changed by this package.

## Source-truth notes

The wording is derived only from the pinned repository itself. In particular:

- `README.md` says this repository contains formal specifications for RustChain protocol changes and distinguishes RIPs stored here from canonical RIPs linked into the main RustChain repository.
- `CONTRIBUTING.md` says new proposals start from `RIP-TEMPLATE.md`, are submitted by pull request, and that README index changes must be mirrored into `rip-search.js` and checked with `node tools/check-rip-index.mjs`.
- This package does not alter the index, so it does not require a `rip-search.js` update.

## Application

Copy the two files under `target/` to the root of a checkout of `Scottcjn/rustchain-rips` at the pinned commit, review the resulting two-path diff, and open the required upstream pull request.

## Submission state

Direct `/claim` and direct branch creation on sponsor repositories were attempted through the connected GitHub App and returned `403 Resource not accessible by integration`. The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication of a document/patch/report in a repository controlled by the claimant as a fallback for that connector-specific limitation. This package is that public fallback artifact. No payout or maintainer acceptance is asserted here.
