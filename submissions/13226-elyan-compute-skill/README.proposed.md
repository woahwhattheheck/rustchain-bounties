# Elyan Labs Compute Skill

[![BCOS Certified](https://img.shields.io/badge/BCOS-Certified-brightgreen?style=flat&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxwYXRoIGQ9Ik0xMiAxTDMgNXY2YzAgNS41NSAzLjg0IDEwLjc0IDkgMTIgNS4xNi0xLjI2IDktNi40NSA5LTEyVjVsLTktNHptLTIgMTZsLTQtNCA1LjQxLTUuNDEgMS40MSAxLjQxTDEwIDE0bDYtNiAxLjQxIDEuNDFMMTAgMTd6Ii8+PC9zdmc+)](BCOS.md)

**Elyan Labs Compute Skill is a Beacon Protocol skill that lets agents buy pay-per-request inference, vision, text-to-speech, and video generation with x402 USDC on Base or RustChain RTC.**

It is packaged for Conway Automaton and uses [`beacon_skill.compute_marketplace`](https://github.com/Scottcjn/beacon-skill/blob/main/beacon_skill/compute_marketplace.py) plus [`openclaw-x402`](https://github.com/Scottcjn/openclaw-x402) for payment and compute access.

## Install

Conway agents can install this skill:

```
installSkill("https://github.com/Scottcjn/elyan-compute-skill", "elyan-compute")
```

Or fetch the SKILL.md directly:

```
installSkillFromUrl("https://raw.githubusercontent.com/Scottcjn/elyan-compute-skill/main/SKILL.md", "elyan-compute")
```

## Endpoints

| Endpoint | Price | Hardware |
|----------|-------|----------|
| `/api/compute/inference` | $0.01 | POWER8 512GB (Ollama) |
| `/api/compute/vision` | $0.05 | BAGEL-7B on V100 |
| `/api/compute/tts` | $0.02 | XTTS on RTX 4070 |
| `/api/compute/video` | $0.50 | ComfyUI on V100 32GB |

## Payment

All endpoints return HTTP 402 with x402 payment requirements. Compatible with any x402 client library. Payments in USDC on Base (chain ID 8453).

Dual economy: also accepts RustChain RTC tokens (1 RTC = $0.10 USD) via `X-RTC-Payment` header.

## Hardware

12 GPUs totaling 192GB VRAM across V100 32GB, V100 16GB, RTX 5070, RTX 4070, RTX 3060, and M40 cards. Plus IBM POWER8 S824 with 128 threads and 512GB RAM for large model inference. Hailo-8 TPU and 2x Alveo U30 FPGA for specialized workloads.

All infrastructure located in Baton Rouge, LA.

## Ecosystem

- [Beacon Protocol](https://github.com/Scottcjn/beacon-skill) — Agent orchestrator (13 transports, scorecard dashboard)
- [openclaw-x402](https://github.com/Scottcjn/openclaw-x402) — x402 payment middleware (used by this skill)
- [BoTTube](https://bottube.ai) — AI video platform
- [RustChain](https://github.com/Scottcjn/Rustchain) — Proof-of-Antiquity blockchain
- [Silicon Archaeology](https://github.com/Scottcjn/silicon-archaeology-skill) — Vintage hardware cataloging
- [Grazer](https://github.com/Scottcjn/grazer-skill) — Multi-platform discovery
- [Beacon Atlas](https://rustchain.org/beacon/) — Live agent directory (31+ agents)
- [Beacon Agents API](https://rustchain.org/beacon/api/agents) — Live Beacon agent metadata

## FAQ

### What is Elyan Labs Compute Skill?

Elyan Labs Compute Skill is a pay-per-request remote-compute interface for agents in the Beacon Protocol ecosystem, covering language-model inference, image understanding, speech synthesis, and video generation.

### How do I install it?

Install the repository as `elyan-compute` with Conway Automaton's `installSkill(...)`, or load the canonical [`SKILL.md`](https://github.com/Scottcjn/elyan-compute-skill/blob/main/SKILL.md) directly with `installSkillFromUrl(...)`.

### How do paid requests work?

A request without payment receives HTTP 402 with x402 payment requirements. An x402-capable client pays USDC on Base (chain ID 8453) and retries the request. The skill also documents RustChain RTC payment through the `X-RTC-Payment` header.

### What workloads are available?

The documented endpoints cover LLM inference, vision understanding, text-to-speech, and video generation. The endpoint table above is the canonical README summary of current per-request prices and hardware.

### Where are the canonical project links?

Use this repository and its [`SKILL.md`](https://github.com/Scottcjn/elyan-compute-skill/blob/main/SKILL.md) for the skill contract; use [Beacon Protocol](https://github.com/Scottcjn/beacon-skill) for orchestration, [openclaw-x402](https://github.com/Scottcjn/openclaw-x402) for x402 payment middleware, [RustChain](https://github.com/Scottcjn/Rustchain) for RTC, and [BoTTube](https://bottube.ai) for the ecosystem's AI video platform.

## License

MIT
