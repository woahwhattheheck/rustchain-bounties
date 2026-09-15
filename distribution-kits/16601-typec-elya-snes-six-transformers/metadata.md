# Metadata

## Primary title

**Six Transformers on a Super Nintendo Cartridge**

## Alternate titles

1. **This SNES Cartridge Runs AI — and Plays Its Own Intro**
2. **A 2 MiB SNES Cart Holds Six Transformer Shards**

## First-frame text

**6 TRANSFORMERS. ONE SNES CART.**

Subline: **10-second AI-generated intro + exact receipts**

## Description

`Scottcjn/elya-snes` runs a ternary transformer on a stock Super Nintendo. At source commit `1464529b9bd92c75e2c21cebd65af104b8976e82`, one 2 MiB cartridge contains six routed transformer shards plus a 10-second, 121-frame AI-generated intro.

The committed verification reports a combined intro-to-game run with 26 checks and all eight routed answers token-identical to their host references. The intro's final PPU-state receipt matches 1,024/1,024 BG1 map entries, 6,176/6,176 CHR bytes, and 128/128 CGRAM entries, with 605 vblanks for 121 frames.

Source: https://github.com/Scottcjn/elya-snes/tree/1464529b9bd92c75e2c21cebd65af104b8976e82

Evidence note: routed game QA is verified under the ares emulator. The intro receipt proves final PPU state and cadence; the source explicitly does not claim that it proves how every intermediate frame looked on physical hardware.

## Tags

`SNES`, `Super Nintendo`, `retrocomputing`, `transformer`, `AI`, `machine learning`, `65816`, `ternary neural network`, `retro game dev`, `Elyan`, `on-device AI`

## Suggested pinned comment

Source-pinned receipts, not marketing estimates: https://github.com/Scottcjn/elya-snes/tree/1464529b9bd92c75e2c21cebd65af104b8976e82 — see README/FINDINGS and commits `8347661` + `1464529` for the routed-QA and intro receipts.

## Upload notes

- Format: 1080×1920, 9:16.
- Keep total duration at or below 60 seconds.
- Burn in captions for every spoken number.
- Preserve the `ares emulator receipt` label when showing routed-QA evidence.
- No music is required; if music is added, publisher must use material they have rights to.
