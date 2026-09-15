# Sources

All technical claims in this package are pinned to:

`Scottcjn/ram-coffers@92b0488d414e5ea88a734c2349feb31d0a8c6c0c`

## Claim map

### 1. RAM Coffers is NUMA-aware conditional memory / weight banking

Source: `README.md`, title, Abstract, Architecture, Processing Flow, and Generative Engine Profile.

Pinned source:
https://github.com/Scottcjn/ram-coffers/blob/92b0488d414e5ea88a734c2349feb31d0a8c6c0c/README.md

The README describes model knowledge partitioned across NUMA nodes, query-to-coffer routing, coffer activation, DCBT prefetch, and NUMA-node execution.

### 2. Reported TinyLlama configuration and benchmark numbers

Source: `BENCHMARK.md` → `Model and quantization` and `Headline numbers`.

Pinned source:
https://github.com/Scottcjn/ram-coffers/blob/92b0488d414e5ea88a734c2349feb31d0a8c6c0c/BENCHMARK.md

The document identifies TinyLlama 1.1B Chat v1.0, Q4_K_M, and reports these `pp128` prompt-eval values:

- Stock llama.cpp: 16.74 t/s
- + POWER8 VSX: 66.49 t/s
- + PSE vec_perm Collapse: 84.62 t/s
- + RAM Coffers + DCBT: 147.54 t/s
- Reported stock-to-final speedup: 8.81×

### 3. 147.54 t/s is prompt evaluation, not decode

Source: `BENCHMARK.md` → `Headline numbers`.

Pinned source:
https://github.com/Scottcjn/ram-coffers/blob/92b0488d414e5ea88a734c2349feb31d0a8c6c0c/BENCHMARK.md

The benchmark explicitly says the 147.54 headline is a `pp128` prompt-eval number and lists `tg32` decode separately at 18.88 t/s.

### 4. The benchmark is self-reported and not independently reproduced

Source: `BENCHMARK.md` → `Measured vs. template`.

Pinned source:
https://github.com/Scottcjn/ram-coffers/blob/92b0488d414e5ea88a734c2349feb31d0a8c6c0c/BENCHMARK.md

The document says measured values are reported by the author from his POWER8 S824 and that nobody outside Elyan Labs has independently reproduced the numbers yet; it also notes raw `llama-bench` logs are not checked into the repository.

### 5. The measured stack attributes the gain to VSX, thread tuning, and DCBT resident prefetch

Source: `BENCHMARK.md` → paragraph immediately below the headline table.

Pinned source:
https://github.com/Scottcjn/ram-coffers/blob/92b0488d414e5ea88a734c2349feb31d0a8c6c0c/BENCHMARK.md

The document attributes the 8.81× chain to VSX vectorization, tuning from 128 to 64 threads, and DCBT resident prefetch keeping tensors hot in L2/L3.

### 6. 64 threads is the documented best point in the listed thread-scaling table

Source: `BENCHMARK.md` → `Thread scaling`.

Pinned source:
https://github.com/Scottcjn/ram-coffers/blob/92b0488d414e5ea88a734c2349feb31d0a8c6c0c/BENCHMARK.md

The table reports 84.62 t/s at 64 threads versus 76.54 at 96 and 65.83 at 128, and attributes the decline past 64 to POWER8 SMT8 cache contention.

## Claims intentionally excluded

This short does **not** claim independent reproduction, production deployment scale, cost savings, energy savings, profitability, or decode throughput of 147.54 t/s. Those claims are not supported by the pinned benchmark evidence.
