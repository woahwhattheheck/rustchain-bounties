# 9:16 visual / capture plan

**Canvas:** 1080×1920 vertical  
**Target runtime:** 57 seconds  
**Source state:** `Scottcjn/elya-snes@1464529b9bd92c75e2c21cebd65af104b8976e82`

Use only publisher-created captures of the public repository and repository-owned images/evidence. Do not use third-party game footage, music, logos, or stock media.

## 0:00–0:05 — Hook

Capture the top of the pinned `README.md`, including the sentence that the transformer runs on a stock Super Nintendo with no enhancement chip, SuperFX, or DSP.

Overlay, large:

> 6 TRANSFORMERS. ONE SNES CART.

Smaller subline:

> plus a 10-second AI-generated intro

Keep `Scottcjn/elya-snes@1464529` visible in a small evidence strap.

## 0:05–0:13 — Base model

Scroll to the README model paragraph. Punch in on:

- `102,400 ternary weights`
- `4-bit activations`
- `Ricoh 5A22`

Overlay:

> 102,400 ternary weights  
> 4-bit activations  
> stock SNES CPU

Do not describe the six shards as six models running simultaneously. The cartridge routes work to one shard for a given question.

## 0:13–0:23 — Six routed shards

Open commit `834766143791f9dec878256d3b010de0f08c37af` and frame the section describing the sixth shard, the eight-question menu, and the GRUN=8 receipt.

Animate three short callouts:

> 6 topic shards

> 8 routed questions

> all 8 answers token-identical to host reference

Label the evidence clearly:

> ares emulator receipt

Do **not** imply this commit establishes execution on physical SNES silicon; the source explicitly says it does not.

## 0:23–0:36 — The intro on the same cartridge

Open commit `1464529b9bd92c75e2c21cebd65af104b8976e82`. Frame the intro description and highlight:

- 10 seconds
- 12 fps
- 128×96
- 2 MiB cartridge
- six transformers

Overlay:

> 121 frames • 12 fps • 128×96

If a publisher uses any committed frame capture from the repository, label it `repository capture`; do not present it as real-hardware camera footage. The source proves end state and cadence, not the appearance of every intermediate frame on silicon.

## 0:36–0:49 — Byte-level receipt

Keep the latest commit or pinned `FINDINGS.md` on screen and animate the three receipt counts one at a time:

> BG1 map: 1,024 / 1,024

> CHR: 6,176 / 6,176 bytes

> CGRAM: 128 / 128 entries

Then add:

> 605 vblanks for 121 frames

Use a simple terminal/counter treatment; no illustrative footage is needed.

## 0:49–0:57 — Combined integration receipt

Frame the latest commit text stating that one run plays the whole intro and then executes the full eight-question game QA.

Final overlay:

> INTRO → GAME → 26 CHECKS PASS

Smaller line:

> every answer token-identical to its routed shard

End card:

> github.com/Scottcjn/elya-snes

## Accuracy guardrails

- Say `under ares` or `emulator receipt` when describing the routed-QA execution.
- Do not claim the final-state intro receipt proves intermediate motion or physical-hardware playback.
- Do not round or replace the committed counts.
- Do not call the six routed shards six simultaneous transformers.
- Do not add performance, profit, price, power, or benchmark claims not present in the pinned sources.
