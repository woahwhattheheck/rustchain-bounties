# Script — 55–60 seconds

**[0:00–0:05]**
What if an old POWER8 server stopped dragging every model weight through memory for every prompt?

**[0:05–0:14]**
RAM Coffers splits model knowledge across NUMA memory banks, routes a query to the relevant coffer, then warms that bank before inference.

**[0:14–0:25]**
On TinyLlama 1.1B Q4, the project reports **147.54 tokens per second** for `pp128` prompt evaluation — **8.81 times** its stock llama.cpp baseline.

**[0:25–0:35]**
Important caveat: the project’s own benchmark file calls that result **author-reported, not independently reproduced**. And 147.54 is prompt evaluation, not decode.

**[0:35–0:45]**
Decode is listed separately at **18.88 tokens per second**. The measured stack attributes the gain to VSX vectorization, 64-thread tuning, and DCBT resident prefetch.

**[0:45–0:57]**
The idea is simple: put weights where the hardware already has locality, activate only the useful memory path, and measure the result. That’s RAM Coffers.

**End card:** `RAM Coffers · NUMA-local weight banking · Source-pinned below`
