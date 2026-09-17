# Bounty #13226 — POSIX9 llms.txt + GEO/AEO README profile

Target bounty: https://github.com/Scottcjn/rustchain-bounties/issues/13226
Target repository: https://github.com/Scottcjn/posix9
Prepared against upstream `main` commit: `c67c4fe0da83d368c269d9431b62ef1fce6717e3`
Upstream README blob: `ca98da1367f6ad5eca5baf6b0ac1f815b3aabb75`

## Deliverables

- `llms.txt` — proposed root `llms.txt` following the llms.txt Markdown convention: answer-first project definition, supported targets, API/source map, limitations, build commands, entity relationships, and canonical links.
- `README.patch` — focused patch against the exact upstream README adding one quotable definition sentence, canonical entity links, and an FAQ section without replacing or deleting the existing documentation.

## Acceptance mapping

1. **Root `llms.txt`:** included as `llms.txt` in this public fallback package.
2. **Answer-first README intro:** the patch replaces the generic opening sentence with a direct definition of POSIX9 as a POSIX compatibility layer for Classic Mac OS, naming System 7–Mac OS 9, 68K/PowerPC, and Retro68.
3. **FAQ-style section:** the patch adds six focused questions covering project purpose, supported Macs/OS versions, build method, process-model limits, networking status, and path translation.
4. **Entity-rich coverage without stuffing:** POSIX9, Classic Mac OS, System 7, Mac OS 9, 68K, PowerPC, Retro68, Open Transport, and the canonical GitHub repository are introduced where technically relevant.
5. **Canonical outbound links:** the proposed files link to `Scottcjn/posix9` and `autc04/Retro68`; source/header links point to paths that exist on the pinned upstream commit.

## Source verification

Fresh upstream reads were performed before drafting:

- `Scottcjn/posix9` default branch is `main` and was pinned at `c67c4fe0da83d368c269d9431b62ef1fce6717e3`.
- No root `llms.txt` exists on that source revision.
- README platform claims used here come from the pinned README: 68K 68020+ / System 7.0–8.1 and PowerPC G3/G4/G5 / Mac OS 7.5.2–9.2.2 with Retro68.
- Fresh `src/` listing verifies `posix9_dir.c`, `posix9_file.c`, `posix9_misc.c`, `posix9_path.c`, `posix9_signal.c`, `posix9_socket.c`, and `posix9_thread.c` all exist at that commit.
- The README itself marks the socket module WIP and documents Open Transport as the networking layer, so the new copy deliberately describes networking as incomplete rather than overstating support.

## Scope and publication state

This package is intentionally documentation-only and contains no runtime/source-code changes. It is public and timestamped as the sponsor-documented fallback for a GitHub App integration that may be unable to write to the sponsor repositories. It is **not** a claim of upstream merge, bounty acceptance, or payment.

Bounty #13226 requires a native `RTC…` payout address for final claim. No wallet is invented here; the operator must attach the correct native address when posting `/claim` if it is not already registered with the sponsor.
