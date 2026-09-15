# Publishing metadata

## Primary title

**This POWER8 Trick Keeps LLM Weights Close to Memory**

## Alternate titles

- **RAM Coffers in 57 Seconds: NUMA-Local LLM Weights**
- **147.54 t/s on POWER8 — What RAM Coffers Actually Measured**

## Hook line

**What if an old POWER8 server stopped dragging every model weight through memory for every prompt?**

## Description

RAM Coffers is a NUMA-aware conditional-memory architecture for LLM inference. This short shows the repository’s routing model and its reported TinyLlama benchmark while preserving the project’s own evidence caveat: 147.54 t/s is a self-reported `pp128` prompt-evaluation result, not independently reproduced, and decode is reported separately at 18.88 t/s.

Source pin: `Scottcjn/ram-coffers@92b0488d414e5ea88a734c2349feb31d0a8c6c0c`

Repository: https://github.com/Scottcjn/ram-coffers

Author credit: `woahwhattheheck`

## Tags

`RAM Coffers`, `POWER8`, `LLM inference`, `NUMA`, `llama.cpp`, `VSX`, `DCBT`, `TinyLlama`, `self-hosted AI`, `Elyan Labs`

## Suggested on-screen caption

`147.54 t/s = pp128 prompt eval, self-reported; tg32 decode = 18.88 t/s. Source: pinned BENCHMARK.md.`

## Thumbnail / first-frame text

**STOP RELOADING EVERY WEIGHT**

Small subline: `POWER8 · NUMA · RAM Coffers`

## Pinned comment

Technical receipts and reproduction caveats are source-pinned in the package `SOURCES.md`. The project’s benchmark document explicitly separates prompt evaluation (`pp128`) from decode (`tg32`) and states that its measured numbers are author-reported, not independently reproduced.
