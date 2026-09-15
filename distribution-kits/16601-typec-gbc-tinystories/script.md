# Script — target runtime 52–58 seconds

**0:00–0:05**  
This stock Game Boy Color is running a transformer locally — no cloud inference.

**0:05–0:13**  
The project packs a quantized TinyStories-260K model into a GBDK ROM, with prompt entry right on the handheld.

**0:13–0:22**  
Its tiny transformer is fixed at five layers, a 64-wide model dimension, eight attention heads, and a 512-token vocabulary.

**0:22–0:34**  
On real hardware, the published test used the prompt “a,” then generated fifteen tokens. Including prefill, that is sixteen transformer forward passes.

**0:34–0:45**  
The run took about forty-five minutes: roughly 0.0059 tokens per second, or one token every two minutes forty-nine seconds.

**0:45–0:54**  
The KV cache lives in cartridge SRAM so base WRAM stays under eight kilobytes, while model data uses MBC5 bank switching.

**0:54–0:59**  
It is slow, greedy-only, and capped at sixteen tokens — but it is real local transformer inference on a stock Game Boy Color.
