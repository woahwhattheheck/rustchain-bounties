# Beacon #929 — canonical Quick Start consolidation

## Lane

- Revenue track: `Scottcjn/rustchain-bounties#100` accepted improvement PR track.
- Target issue: `Scottcjn/beacon-skill#929`.
- Reporter credit remains with `@stratumpraxis`; this package is an implementation carrier only.
- Target source pin: `Scottcjn/beacon-skill@4f0431b03a67917bc0c0bda65d6150e42b10255d`.
- Exact source blob: `README.md` = `a475e2ee3f7a130c625e2015e5b7722fc4567b92`.

## Verified gap

At the pinned source, `README.md` contains two consecutive `## Quick Start (2 minutes)` sections. Both repeat the AI-agent bullets. The first Human Quick Start contains a literal `...` line inside a shell block; the second repeats installation and optional-extra commands. This makes the executable first-run path ambiguous and leaves a placeholder that a reader could copy literally.

## Proposed change

`README.patch` does only the #929 repair:

1. Keep one `## Quick Start (2 minutes)` heading.
2. Keep one copy of the AI-agent Quick Start bullets.
3. Merge the optional mnemonic, dashboard, and editable-source install commands into the surviving Human Quick Start.
4. Remove both literal `...` placeholder lines.
5. Preserve the identity creation and local webhook loopback commands as the first runnable message-delivery path.
6. Preserve the npm installation alternative.

No runtime, protocol, dependency, transport, security, or package metadata is changed.

## Validation

The patch was generated against the exact pinned README excerpt. A structural check of the proposed replacement reports:

- `## Quick Start (2 minutes)` occurrences in the replaced region: `1`.
- standalone literal `...` lines in the replaced region: `0`.
- retained install commands: base pip, mnemonic extra, dashboard extra, editable source, npm.
- retained first-run commands: `beacon identity new`, webhook receiver, and webhook sender.

Patch SHA-256: `245582b6109b2d2cd3f5134caa4302aa626125b4091d1ceffcfbc644ea6aaf09`.

This is a documentation-only patch, so no runtime-test success is asserted.

## Submission state

The GitHub App connection can read the target repository but direct target issue/branch writes return `403 Resource not accessible by integration`. The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly permits publishing a document/patch/report in a repository controlled by the claimant for this connector-specific condition. This directory is that public, source-pinned fallback package. Sponsor acceptance and RTC payout are not asserted until the maintainer receives/accepts it.
