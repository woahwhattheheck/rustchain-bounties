# Vertical visual plan — 9:16

All text/diagram cards below can be built from scratch by the publisher. No source-repo photography is required.

| Time | Visual | On-screen text / capture instruction |
|---|---|---|
| 0:00–0:05 | Original pixel-grid silhouette of a handheld, then a tiny transformer-node diagram appears inside the screen area. | `A TRANSFORMER. ON A STOCK GAME BOY COLOR.` |
| 0:05–0:13 | Split card: left = `TinyStories-260K`; right = a simple flow `D-pad/buttons → tokenizer → transformer → text`. | `LOCAL PROMPT → LOCAL INFERENCE` |
| 0:13–0:22 | Animate five stacked blocks. Then flash four source-pinned dimensions as large typography. | `5 layers` · `dim 64` · `8 heads` · `vocab 512` |
| 0:22–0:34 | Counter animation: `P 1/1` then `G 1/15 … G 15/15`; finish on `16 forward passes`. | `1 PREFILL + 15 GENERATED` |
| 0:34–0:45 | Stopwatch-style card counts up to `~45 min`, then switches to `~0.0059 tok/s` and `~1 token / 2m49s`. | Add small footer: `reported real-hardware result` |
| 0:45–0:54 | Original memory map diagram: `base WRAM < 8 KB` on one side, `cartridge SRAM → KV cache` and `MBC5 banks → model data` on the other. | `CARTRIDGE MEMORY DOES THE HEAVY LIFTING` |
| 0:54–0:59 | Return to handheld silhouette with three caveat stamps, then final line. | `16-token context` · `greedy only` · `proof of concept` → `REAL LOCAL INFERENCE` |

## Optional source-verification insert

For a documentary-style version, record an original screen capture of the pinned GitHub README at commit `28c443c1b0cb3d4536f4575bcdfd647a3ec8ad73`, zooming only on the text lines that report the hardware result and limitations. Do not reuse the committed hardware photograph unless publication rights are separately confirmed.

## Audio/edit notes

- Narration should remain intelligible at normal speed; do not time-compress to force the script below 60 seconds.
- No music is required. If music is added, use publisher-owned or properly licensed audio only.
- Keep the `reported real-hardware result` qualifier visible when the throughput number is on screen.
- Do not add claims about profitability, benchmark superiority, or comparative speed; the source describes the implementation as intentionally tiny and slow.