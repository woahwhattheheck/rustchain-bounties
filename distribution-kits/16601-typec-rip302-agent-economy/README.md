# RIP-302 Agent Economy — Type C Shorts package

Bounty: `Scottcjn/rustchain-bounties#16601`  
Package type: **Type C — YouTube Shorts / clip kit**  
Angle: **An agent hires another agent: the RIP-302 escrow lifecycle in under 60 seconds**

This package is designed as a 9:16 short that can be assembled directly from the source-pinned RustChain repository without inventing production numbers, earnings claims, or security guarantees.

## Package contents

- `script.md` — timed narration, ~55 seconds at a normal delivery pace.
- `storyboard.md` — exact 9:16 capture instructions and on-screen text.
- `metadata.md` — title, description, tags, hook, caption, and upload notes.
- `SOURCES.md` — claim-by-claim source map pinned to RustChain commit `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`.

## Core story

RIP-302 turns RTC into a job-marketplace payment primitive. A poster creates a job and the implementation debits the poster by the worker reward plus a 5% platform fee, placing that amount in the internal `agent_escrow` wallet. A worker can claim and deliver the job. When the poster accepts the delivery, the implementation marks the job completed, pays the worker reward, routes the fee to `founder_community`, and records reputation/accounting updates.

The short deliberately says **“the code implements”** rather than implying that every deployment or transaction is independently verified live in this package.

## Validation notes

- No profitability or token-price claims.
- No claim that escrow is trustless, immutable, or free from bugs.
- No fabricated live job IDs, wallet balances, or payment screenshots.
- All factual implementation claims are pinned to the exact source SHA in `SOURCES.md`.
- Capture plan uses repository/code/UI-style visuals that a human editor can reproduce without privileged infrastructure.
