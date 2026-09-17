# Grazer #353 — `all` provider contract documentation patch

## Scope

- Paid lane: `Scottcjn/rustchain-bounties#100` improvement-PR track (10 RTC if accepted; scope-dependent).
- Target issue: `Scottcjn/grazer-skill#353`.
- Target upstream snapshot: `Scottcjn/grazer-skill@1167938eb96c57eb8718c09b13b720fdd645fb1f`.
- Target file: `README.md` (blob `5f90ac65b3951e752f79194a00dd4123011a13c3`).
- Source-report credit remains with the reporter named in #353 (`@Nish916`); this package is only the implementation attempt.

## Problem verified on the pinned upstream

The README still labels both of these interfaces as discovering across “all 5 platforms”:

- CLI: `grazer discover -p all`
- Python: `GrazerClient.discover_all()`

Current `GrazerClient.discover_all()` actually dispatches the same discovery sweep used by CLI `-p all` across **22 providers**:

`bottube`, `moltbook`, `clawcities`, `clawsta`, `fourclaw`, `pinchedin`, `clawtasks`, `clawnews`, `directory`, `agentchan`, `thecolony`, `moltx`, `moltexchange`, `arxiv`, `youtube`, `podcasts`, `bluesky`, `farcaster`, `semantic_scholar`, `openreview`, `mastodon`, `nostr`.

The CLI implementation calls `client.discover_all(...)` for the `all` selector, so there is no separate CLI provider set to document at this snapshot. `clawhub` and `swarmhub` appear in broader platform metadata/support surfaces but are **not** traversed by `discover_all()` at this commit; documenting the exact call set avoids implying otherwise.

## Proposed README behavior

The patch in [`README.patch`](README.patch):

1. Replaces both stale “all 5 platforms” comments with “all providers in the `discover_all()` contract”.
2. Adds an explicit **What `all` means** section listing all 22 keys in call order.
3. States that CLI `-p all` delegates to `GrazerClient.discover_all()`, so their sets are identical on the pinned commit.
4. Clarifies that this contract describes **read-only discovery** only; write/engagement commands are separate and are not implied by membership in `all`.
5. Explicitly notes that ClawHub and SwarmHub are not part of this aggregate sweep even though they exist elsewhere in the project’s support/registry surfaces.

## Validation

Static validation against upstream `1167938...`:

- README stale comment locations read directly from upstream `README.md`.
- `grazer/cli.py` was inspected: `-p all` calls `client.discover_all(**discover_options)`.
- `grazer/__init__.py` was inspected: the `calls` list inside `discover_all()` contains exactly the 22 providers listed above, in the same order.
- The patch is documentation-only and does not change runtime behavior.

## Publication / connector state

Direct branch creation in `Scottcjn/grazer-skill` was attempted from exact upstream main and returned `403 Resource not accessible by integration`. The sponsor’s current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly permits publishing a document/patch/report in a repository the contributor controls for this connector-specific limitation. This directory is that public, timestamped fallback deliverable.

Upstream acceptance, merge, and RTC payment are **not** asserted by this package.