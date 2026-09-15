# Metadata

## Primary title

**A Transformer Running on a Stock Game Boy Color**

## Alternate titles

1. **TinyStories-260K on a Game Boy Color — No Cloud**
2. **16 Transformer Passes on a Game Boy Color**

## First-frame / thumbnail text

**TRANSFORMER ON GAME BOY COLOR**

## Description

A stock Game Boy Color runs a quantized TinyStories-260K transformer locally. The source-pinned real-hardware result reports 16 transformer forward passes — one prefill plus 15 generated tokens — in about 45 minutes, roughly 0.0059 tokens/sec.

This is deliberately a proof of concept: 16-token context, greedy decoding, and severe hardware constraints. The point is not speed; it is that the inference path is running on the handheld itself.

Source: https://github.com/maddiedreese/gbc-transformer/tree/28c443c1b0cb3d4536f4575bcdfd647a3ec8ad73

Prepared for Elyan Labs distribution package bounty #16601. Author credit: @woahwhattheheck.

## Tags

`Game Boy Color`, `GBC`, `transformer`, `TinyStories`, `local AI`, `retro computing`, `machine learning`, `quantization`, `GBDK`, `edge AI`

## Upload notes

- Format: 1080×1920 vertical, <=60 seconds.
- Category framing: retro-computing / engineering demo, not a product benchmark.
- Keep `reported real-hardware result` visible beside the throughput figure.
- Do not imply the output is fast, production-ready, or cloud-assisted.
- Attribution requested: `@woahwhattheheck` for the package; source project should be linked in the description.
