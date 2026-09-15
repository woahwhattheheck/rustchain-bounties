# Storyboard — vertical 9:16

Target canvas: 1080×1920. Keep all source text inside the center 780 px safe column so platform controls do not cover evidence. Use only captures from the pinned public repository and simple text overlays.

## Shot 1 — Hook (0:00–0:05)

**Visual:** Screen-record the top of `README.md` at source pin `92b0488…`, with the title “RAM Coffers: NUMA-Distributed Conditional Memory for LLM Inference” visible. Slow push-in.

**Overlay:** `STOP RELOADING EVERY WEIGHT`

**Capture:** Open the pinned README URL from `SOURCES.md`; crop browser chrome out; do not show star counts or other changing UI.

## Shot 2 — The memory-bank idea (0:05–0:14)

**Visual:** Scroll to README `Architecture`, showing the four-row Coffer / NUMA Node / Capacity / Role table, then to `Processing Flow`.

**Overlay:** `QUERY → COFFER → LOCAL MEMORY`

**Motion:** Highlight one table row, then animate a simple arrow to the `route_to_coffer` text. No invented topology diagram is needed.

## Shot 3 — Headline benchmark (0:14–0:25)

**Visual:** Open pinned `BENCHMARK.md`, `Headline numbers`, and frame the rows:
- Stock llama.cpp — 16.74 t/s
- RAM Coffers + DCBT — 147.54 t/s

**Overlay:** `pp128 PROMPT EVAL · 147.54 t/s · 8.81×`

**Guardrail:** Keep `pp128` visible on screen. Never label this number as decode/generation throughput.

## Shot 4 — Evidence caveat (0:25–0:35)

**Visual:** Jump to `BENCHMARK.md` → `Measured vs. template`. Box the sentence saying measured values are author-reported and not independently reproduced.

**Overlay:** `SELF-REPORTED · NOT YET INDEPENDENTLY REPRODUCED`

**Motion:** Hold for at least 3 seconds so the caveat can be read.

## Shot 5 — Decode + stack (0:35–0:45)

**Visual A:** Return to the headline-number section and frame the sentence `Decode throughput (tg32) ... 18.88 t/s`.

**Visual B:** Pan one paragraph upward to the attribution: VSX vectorization, 64-thread tuning, DCBT resident prefetch.

**Overlay sequence:**
1. `tg32 DECODE: 18.88 t/s`
2. `VSX → 64 THREADS → DCBT PREFETCH`

## Shot 6 — Locality payoff (0:45–0:57)

**Visual:** Split-screen two pinned README excerpts: `Processing Flow` on top and the one-line `What is RAM Coffers?` definition under `Generative Engine Profile` on bottom.

**Overlay:** `ROUTE WEIGHTS WHERE MEMORY IS LOCAL`

At 0:54, replace overlay with end card:

`RAM COFFERS`
`NUMA-local weight banking`
`github.com/Scottcjn/ram-coffers`

## Audio / rights

Narration only; no music required. All visuals are direct captures of the public source repository plus original text overlays. Avoid third-party logos beyond GitHub/RAM Coffers text already present in the captured pages.
