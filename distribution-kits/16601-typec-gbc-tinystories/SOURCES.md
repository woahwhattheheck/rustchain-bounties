# SOURCES — claim map

All technical claims in this package are pinned to:

`maddiedreese/gbc-transformer@28c443c1b0cb3d4536f4575bcdfd647a3ec8ad73`

Canonical source file:
https://github.com/maddiedreese/gbc-transformer/blob/28c443c1b0cb3d4536f4575bcdfd647a3ec8ad73/README.md

| Claim used in package | Source evidence |
|---|---|
| TinyStories-260K runs locally on a stock Game Boy Color. | README opening: “TinyStories-260K running locally on a stock Game Boy Color.” |
| It is a GBDK-2020 ROM with on-device prompt entry, tokenization, prefill, and autoregressive generation. | README introduction. |
| Real-hardware prompt was `a`; generation produced 15/15 tokens after prefill; total forward passes were 16. | README `Hardware Result`. |
| Estimated elapsed time was about 45 minutes. | README `Hardware Result`. |
| Throughput was about 0.0059 tokens/sec, or one token every 2 minutes 49 seconds. | README `Hardware Result`. |
| Model shape includes `dim=64`, `layers=5`, `heads=8`, `vocab=512` (also `hidden_dim=172`, `kv_heads=4`). | README `Current Limitations`. |
| Model data is embedded as MBC5 bank-switched cartridge data. | README `What Works`. |
| Cartridge SRAM is used for the KV cache so base WRAM stays below 8 KB. | README `What Works`. |
| Context is capped at 16 tokens and decoding is greedy-only. | README `Current Limitations`. |
| The implementation is intentionally tiny and slow, and is a proof of concept rather than a polished text generator. | README opening and `Current Limitations`. |

## Deliberately excluded claims

This package does **not** claim benchmark superiority, commercial readiness, profitability, independently reproduced timing, or rights to reuse the source repository's committed hardware photograph. Those are outside the pinned evidence or outside this package's rights grant.