# Bounty #13226 — homebrew-beacon GEO/AEO profile

Target bounty: https://github.com/Scottcjn/rustchain-bounties/issues/13226

Target repository: https://github.com/Scottcjn/homebrew-beacon

Claimant: `@woahwhattheheck`

## Source pin

Prepared against upstream `Scottcjn/homebrew-beacon` main commit:

`26e9ac68f7aded6e0fda647e3c9430992c3864a4`

Exact source reads before any publication:

- `README.md` blob `1a72e2f7ea42b7fb4617b4570ee10956b04413ca`
- `Formula/beacon.rb` blob `36847cbbb4361bb8248079afbf18af86ed1c16d2`
- root directory at the pinned commit had no `llms.txt`

Fresh collision checks before taking the lane found no `homebrew-beacon` GEO/AEO/`llms.txt` pull request and no Slack ownership for `homebrew-beacon` under bounty #13226.

## Deliverable

`target/llms.txt` is the proposed new root `llms.txt` for `Scottcjn/homebrew-beacon`.

`target/README.md` is the proposed complete README content preserving the existing install/upgrade workflow while adding:

- one answer-first, quotable definition sentence;
- a FAQ-style generative-engine profile;
- canonical links to the Homebrew tap, Beacon Skill, Beacon skill page, RustChain, and BoTTube;
- an explicit scope boundary between the Homebrew packaging repository and upstream Beacon application behavior.

The package is documentation-only. It does not modify `Formula/beacon.rb`, package versions, dependencies, runtime behavior, payment behavior, or RustChain state.

## Verification basis

Every behavioral statement in the proposed docs is grounded in the pinned repository:

- existing README install command: `brew tap Scottcjn/beacon` + `brew install beacon`;
- existing README upgrade command: `brew update` + `brew upgrade beacon`;
- `Formula/beacon.rb` description: AI-agent orchestrator with heartbeat, mayday, accords, Atlas cities, property contracts, and RustChain escrow;
- `Formula/beacon.rb` homepage: `https://bottube.ai/skills/beacon`;
- `Formula/beacon.rb` installs the `beacon-skill` Python package and exposes the `beacon` command;
- formula caveats point to `https://github.com/Scottcjn/beacon-skill` for docs.

## Connector-specific submission block

The normal sponsor claim route was attempted before publication and returned:

`403 Resource not accessible by integration`

Creating a branch directly in `Scottcjn/homebrew-beacon` from the exact pinned upstream commit returned the same 403.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a repository controlled by the claimant as an accepted route for documents, patches, or reports when the GitHub App cannot write to sponsor repositories. This directory is that public, timestamped fallback artifact.

No sponsor acceptance, merge, or RTC payout is asserted by this publication.
