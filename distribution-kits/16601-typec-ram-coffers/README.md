# Stop Reloading the Model: RAM Coffers in 60 Seconds

Type C YouTube Shorts / clip kit for Scottcjn/rustchain-bounties #16601.

**Pitch:** A 55–60 second vertical explainer of RAM Coffers: route model knowledge into NUMA-local memory banks, warm the selected bank, and measure the result on IBM POWER8. The short keeps the benchmark claim precise: the repository reports 147.54 t/s for TinyLlama `pp128` prompt evaluation (8.81× stock), while its own benchmark document says the result is author-reported and has not yet been independently reproduced.

**Author credit:** `woahwhattheheck`

**Source pin:** `Scottcjn/ram-coffers@92b0488d414e5ea88a734c2349feb31d0a8c6c0c`

## Package

- `script.md` — timed narration under 60 seconds
- `storyboard.md` — exact 9:16 capture instructions; no third-party footage required
- `metadata.md` — hook, titles, description, tags, captions, thumbnail text
- `SOURCES.md` — claim-by-claim source map pinned to the source commit

## Production notes

All writing and capture instructions in this package are original. The human publisher can produce every visual directly from the public RAM Coffers repository; no stock media, music, or third-party assets are required. By submitting this package under bounty #16601, the author licenses Elyan Labs to publish the package content with permanent attribution under the bounty terms.

## Accuracy guardrails

The short deliberately distinguishes prompt evaluation from token generation. `147.54 t/s` is the project’s reported `pp128` prompt-eval result, not decode throughput; the same benchmark document lists `tg32` decode at `18.88 t/s`. It also labels the 147.54 result as self-reported rather than independently reproduced.
