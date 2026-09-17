# #13226 — Scottcjn/homebrew-tap GEO/AEO package

This directory is a source-pinned fallback submission for `Scottcjn/rustchain-bounties#13226`, targeting exactly one RustChain-ecosystem repository: `Scottcjn/homebrew-tap`.

No maintainer acceptance or RTC payout is asserted here. The bounty title currently says 7 RTC while the issue body says 10 RTC; compensation is whatever the sponsor ultimately accepts and records.

## Source pin

Target repository: `Scottcjn/homebrew-tap`

Target `main` at preparation time:

`6573bc6438590db2bca0517e7ea26d1110957224`

Read before preparing the patch:

- `README.md` blob `d94c2e168b9a0bb6c1345a94ff21eaa71e7f8b79`
- `Formula/bcos.rb` blob `84175be5d952502d0e137c4ac33189fa3a4aabe6`
- `Formula/grazer.rb` blob `efdae3ab699ed45c31af1847f23b7a5df6ccd066`
- root `llms.txt`: absent at the pinned commit

The pinned `Formula/` tree contains `bcos.rb` and `grazer.rb`. The proposed text therefore tells readers to treat `Formula/` as the revision-specific package inventory instead of repeating a broader README list as if every named package were present in this checkout.

## Deliverables

- `llms.txt` — proposed root llms.txt with an answer-first project definition, source-backed entity profile, canonical links, install guidance, and concise FAQ.
- `README.patch` — focused additive patch near the existing README introduction. It adds one quotable definition sentence and an FAQ without replacing or restructuring the existing README.

The proposed documentation links only to project-specific/public destinations (`Scottcjn/homebrew-tap`, `Scottcjn/Rustchain`, `Scottcjn/grazer-skill`, `rustchain.org/bcos`, Homebrew docs). It does not link to internal build/coordination infrastructure.

## Duplicate and ownership checks

Before any write:

- the full `#13226` issue-comment response contained no `homebrew-tap` claim or submission;
- joined Slack exact search for `homebrew-tap` returned no result;
- GitHub target PR search for `llms`, `GEO`, `AEO`, or `answer-first` returned no matching PR;
- the target root `llms.txt` returned 404;
- target `main` and the exact README/Formula paths above were read first.

## Connector boundary and sponsor fallback

A direct branch-create attempt against `Scottcjn/homebrew-tap` returned:

`403 Resource not accessible by integration`

A direct `/claim` comment attempt on `Scottcjn/rustchain-bounties#13226` returned the same connector-specific 403.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` at `Scottcjn/rustchain-bounties@39ee6eedd31d141d1130f310c5cf09e9447017f3` explicitly documents this GitHub-App limitation and lists publishing a document, patch, or report in a repository the contributor controls as an accepted fallback route. This directory is that public, timestamped fallback artifact.

## Applying upstream

From a checkout of `Scottcjn/homebrew-tap` at the pinned commit:

1. copy this directory's `llms.txt` to repository root;
2. apply `README.patch` to `README.md`;
3. run `git diff --check`;
4. review the resulting two-file documentation delta against current `Formula/` before opening the target PR.

If target `main` has moved, re-read `README.md` and `Formula/` and regenerate the patch rather than applying it blindly.

## Remaining sponsor-side step

The bounty requires a target PR plus `/claim` with a native `RTC…` wallet. This connector cannot write to the sponsor/target repositories and no native RTC wallet is available in this execution context. A user/PAT-authenticated or email-enabled operator must therefore apply/open the target PR and post the final claim with the correct wallet, linking this public artifact. Until then, payout remains unclaimed and uncounted.
