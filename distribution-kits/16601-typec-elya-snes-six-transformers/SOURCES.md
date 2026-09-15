# SOURCES — claim map

All technical claims in this package are pinned to public `Scottcjn/elya-snes` history. The publication target should preserve these qualifications rather than generalizing emulator evidence into silicon evidence.

## Source pin

- Repository tree: https://github.com/Scottcjn/elya-snes/tree/1464529b9bd92c75e2c21cebd65af104b8976e82
- README at pin: https://github.com/Scottcjn/elya-snes/blob/1464529b9bd92c75e2c21cebd65af104b8976e82/README.md
- FINDINGS at pin: https://github.com/Scottcjn/elya-snes/blob/1464529b9bd92c75e2c21cebd65af104b8976e82/FINDINGS.md

## Claim-by-claim provenance

| Claim used in package | Public source | Qualification |
| --- | --- | --- |
| A transformer language model runs on a stock Super Nintendo with no enhancement chip, SuperFX, or DSP. | README at source pin, opening paragraph. | This describes the base transformer engine. |
| Base model has 102,400 ternary weights and 4-bit activations and executes on the Ricoh 5A22. | README at source pin, opening model-spec paragraph. | Keep the exact number; do not substitute an estimated parameter count. |
| The sharded cartridge contains six routed topic shards. | Commit `834766143791f9dec878256d3b010de0f08c37af`: https://github.com/Scottcjn/elya-snes/commit/834766143791f9dec878256d3b010de0f08c37af | The shards are routed; this does not mean six models execute simultaneously. |
| Eight menu questions reach the six shards, and all eight answers were token-identical to their routed host references. | Commit `834766143791f9dec878256d3b010de0f08c37af`, “The sixth shard earns a button.” | Receipt is under ares; the source explicitly says “No silicon — ares only.” |
| GRUN=8 game autoplay passes 26 checks. | Commit `834766143791f9dec878256d3b010de0f08c37af`. | Same ares qualification. |
| The intro is 10 seconds of AI-generated video at 12 fps, 128×96, on the same 2 MiB cartridge as six transformers. | Commit `1464529b9bd92c75e2c21cebd65af104b8976e82`: https://github.com/Scottcjn/elya-snes/commit/1464529b9bd92c75e2c21cebd65af104b8976e82 | Source says the player streams the ESV1 intro from cartridge banks $21–$37. |
| Intro has 121 frames and a cadence receipt of 605 vblanks. | Commit `1464529b9bd92c75e2c21cebd65af104b8976e82`, byte-level receipt. | 605 vblanks = five vblanks per frame for 121 frames. |
| Final BG1 map receipt is 1,024/1,024 entries. | Commit `1464529b9bd92c75e2c21cebd65af104b8976e82`. | End-state verification. |
| Final CHR receipt is 6,176/6,176 bytes. | Commit `1464529b9bd92c75e2c21cebd65af104b8976e82`. | End-state verification. |
| Final CGRAM receipt is 128/128 entries. | Commit `1464529b9bd92c75e2c21cebd65af104b8976e82`. | End-state verification. |
| One integration run plays the whole intro, hands off, and runs the eight-question game QA with 26 checks and every answer token-identical to its routed shard. | Commit `1464529b9bd92c75e2c21cebd65af104b8976e82`. | This is the exact combined-run claim used in the ending. |
| The intro verification does not establish how every intermediate frame looked on real hardware. | Commit `1464529b9bd92c75e2c21cebd65af104b8976e82`, “What this does not establish.” | Mandatory caveat for publication; do not turn end-state/cadence evidence into a physical-hardware motion claim. |

## Deliberately excluded claims

This package does not claim power consumption, profitability, monetary value, physical-cartridge camera verification, intermediate-frame visual correctness on silicon, or performance for the six-shard build unless the pinned sources explicitly establish it. It also does not say six transformers execute at the same instant.
