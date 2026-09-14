# Bounty #12444 submission — Proof of Antiquity vs Chia Proof of Space and Time

Claimant: `woahwhattheheck`

Immutable public evidence: https://github.com/woahwhattheheck/startup-credits/blob/94098f675d96be659b37d0c19296231e343e8b7b/bounty-evidence/rustchain-12444-poa-vs-chia.md

RustChain source basis: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`.

RustChain and Chia make different resources scarce. Chia asks a farmer to reserve disk space: plots are precomputed data structures, each plot acts like a lottery ticket, and challenges ask for compact proofs that the reserved space exists. RustChain instead tries to make *a particular physical machine* scarce. Its current PoA design combines client measurements with server-side validation: anti-emulation evidence, timing/clock-drift data, architecture/SIMD signals, optional ROM fingerprints, and cross-checks between claimed architecture and observed signals. Antiquity changes reward weight by tier rather than by raw storage capacity.

The verification trade-off is important. Chia's proof is cryptographic and cheap to verify: official documentation describes checking a compact set of x-values with hashes/comparisons. More valid plotted space means more chances to win. RustChain is closer to adversarial hardware attestation. There is no single mathematical proof that a 2003 PowerBook is physically present; confidence comes from several independent measurements that are harder to spoof consistently. RustChain's own whitepaper admits software-only attestation is imperfect and timing signals can be noisy. In return, PoA can distinguish VM-scale from physical-machine-scale in a way pure proof-of-space does not try to.

Lifecycle incentives also diverge. Chia rewards *capacity*, so economics favor efficient storage. Its 2026 Proof of Space 2 design has shifted plotting toward CPU/GPU + RAM, with temporary SSD use optional, so the old “Chia kills SSDs” story should not be treated as timeless. RustChain rewards *continued usefulness of older hardware*: current source defines 2.5x “classic,” 2.0x “vintage,” 1.5x “heritage,” and 1.0x “modern” tiers. That can make otherwise-idle old machines economically useful, but it creates a harder anti-spoofing problem.

Reward sustainability is clearer on Chia: block rewards halve every three years four times, then remain at 0.125 XCH per block in perpetuity. RustChain's distinctive lever is different: antiquity weighting changes who gets more of the reward budget. That is compelling for preservation, but sustainability still depends on network utility being valuable enough to justify paying a premium for scarce old hardware.

So each wins at a different job. Chia is stronger for a clean, scalable, cryptographically verifiable proof of reserved storage. RustChain is more interesting for proving *physical substrate and hardware history* and using incentives to keep real old machines in service. Chia's proof is simpler to verify; RustChain's target is harder to fake but also harder to prove perfectly.

RTC wallet: to be supplied in the authenticated sponsor-facing claim.
