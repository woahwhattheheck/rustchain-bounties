# #13226 — `Scottcjn/rustchain-dos-miner` GEO/AEO package

This is a controlled-repository publication package for `Scottcjn/rustchain-bounties#13226`, targeting one RustChain ecosystem repository: `Scottcjn/rustchain-dos-miner`.

## Exact source state

- Target repository: https://github.com/Scottcjn/rustchain-dos-miner
- Upstream main inspected: `7fc1d136bfe6fadce6bdca7df112deb00435ee66`
- Upstream README blob inspected: `d0cb5d25de52314ba9a9c1fe8b141f2bafc2252c`
- Upstream `COMPLETE_SYSTEM.md` blob inspected: `24eed285fb0eaeef892eca5eaf6c5a780c337348`
- Upstream `NETWORK.TXT` blob inspected: `f960a3c8497dbe4877257fe632675e5e322c3a1a`
- Upstream `dos_bridge.py` blob inspected: `5f8f7e1dbd2be884074db79bafdc606a53eb0581`
- The inspected upstream root had no `llms.txt`.

Pinned source links:

- README: https://github.com/Scottcjn/rustchain-dos-miner/blob/7fc1d136bfe6fadce6bdca7df112deb00435ee66/README.md
- Complete system notes: https://github.com/Scottcjn/rustchain-dos-miner/blob/7fc1d136bfe6fadce6bdca7df112deb00435ee66/COMPLETE_SYSTEM.md
- Network guide: https://github.com/Scottcjn/rustchain-dos-miner/blob/7fc1d136bfe6fadce6bdca7df112deb00435ee66/NETWORK.TXT
- Offline bridge: https://github.com/Scottcjn/rustchain-dos-miner/blob/7fc1d136bfe6fadce6bdca7df112deb00435ee66/dos_bridge.py

## Deliverables

1. `llms.txt` — proposed root `llms.txt` with an answer-first definition, canonical URLs, key entities, source-backed project boundaries, and extractable FAQ.
2. `README-addition.md` — focused text to add to the existing upstream README: one quotable definition sentence, a link to `llms.txt`, and an answer-first FAQ. It intentionally does not replace the existing README.

## How to apply upstream

1. Copy this package's `llms.txt` to the repository root as `llms.txt`.
2. Add the definition block from `README-addition.md` below the existing project heading/subtitle.
3. Add its FAQ after the existing Offline Mode section and before License.
4. Preserve all existing README content around those insertions.
5. Re-check against current upstream main before opening the PR if upstream moved after the source pin above.

## Verification notes

The wording was checked against the exact upstream files listed above. In particular:

- the README documents 8086/8088 through Pentium-era targets, DOS 3.3+/FreeDOS, bootable images, wallet generation, hardware fingerprinting, and offline `ATTEST.TXT` handling;
- `NETWORK.TXT` documents the packet-driver/mTCP setup;
- `COMPLETE_SYSTEM.md` also documents a Watt-32-oriented build path, so the proposed copy explicitly distinguishes the repository's multiple networking/build workflows rather than collapsing them into one;
- `dos_bridge.py` watches `ATTEST.TXT` and submits parsed attestation payloads to `/attest/submit`.

No runtime behavior, dependencies, binaries, wallet code, or mining logic are changed by this documentation-only package.

## Submission state

The connected GitHub App cannot create a branch or comment in the sponsor repositories (`403 Resource not accessible by integration`). The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly lists publication in a repository controlled by the contributor as a fallback for a document/patch/report when that connector-specific 403 occurs. This public package preserves the deliverable and exact source pin for a user/PAT-authenticated sponsor-side submission.

No sponsor acceptance or payout is asserted by this package.
