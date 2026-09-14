# Bounty #12442 submission — RustChain vs Helium / DePIN

Claimant: `woahwhattheheck`
Payout identity: `woahwhattheheck` (hosted RTC handle)
Immutable evidence: https://github.com/woahwhattheheck/startup-credits/blob/fc25fa041d6a813f11b788dcd3a604416a527a00/bounty-evidence/rustchain-12442-depin-comparison.md

## Comparison

The cleanest 2026 comparison is not “Proof of Antiquity versus Helium Proof-of-Coverage,” because Helium removed Proof-of-Coverage on July 6, 2026. Helium now rewards useful wireless infrastructure and data transfer through oracle-accounted entities on Solana. RustChain instead tries to prove that a participant is a real physical machine, then weights it by antiquity.

**Scarce resource.** Helium’s resource is wireless capacity: LoRaWAN gateways and Mobile/Wi-Fi infrastructure moving real traffic. Users pay USD-pegged Data Credits, giving utility a direct price. RustChain’s resource is diverse physical computers with measurable substrate behavior and age. Current RustChain main documents six checks—oscillator drift, cache timing, SIMD identity, thermal entropy, instruction jitter, and anti-emulation—and higher multipliers for old hardware.

**Verification / Sybil resistance.** Helium binds rewardable entities on-chain and uses network/oracle data to account for traffic: “did this gateway deliver useful packets?” RustChain asks “is this machine physically what it claims to be?” That can resist cheap VM cloning and reward hardware diversity. But fingerprinting is a harder security problem: noisy signals, virtualization edge cases, and false positives need adversarial testing. The six checks are best treated as layered evidence, not an absolute guarantee.

**Hardware economics.** Helium can justify radio hardware where coverage demand exists; its IoT docs even support Raspberry Pi + LoRa concentrator builds. Render-style DePIN monetizes modern GPUs. RustChain inverts that incentive: a PowerBook G4 matters because it is old and still working, not because it wins on throughput. That aligns with reuse/e-waste reduction, but shifts utility toward attestation, preservation, and hardware-backed identity rather than raw compute.

**Token model.** Helium has a mature burn-and-mint loop: HNT follows a supply schedule, users burn HNT for USD-pegged Data Credits, and capped net emissions can replenish rewards. RustChain documents an 8.3M RTC supply with mining rewards weighted by antiquity. Helium therefore has the clearer external-demand sink today: paid wireless traffic. RustChain has the more unusual preservation incentive, but must keep issuance tied to verifiable participation so “old machine” does not become merely a narrative subsidy.

**What each does better.** Helium wins at measurable telecom utility and a defined payment loop. Render-class networks win at sellable compute. RustChain’s differentiated bet is hardware provenance: physical aging and architecture diversity as an anti-Sybil resource while keeping obsolete-but-functional machines alive. The strongest framing is not “better DePIN” but a different primitive: Helium monetizes **where packets move**, Render monetizes **what GPUs compute**, and RustChain monetizes **which real machine is present and how long it has survived**.
