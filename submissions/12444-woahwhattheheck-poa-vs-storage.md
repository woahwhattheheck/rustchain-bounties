# Bounty #12444 — Proof of Antiquity vs Proof of Storage

Claimant: `woahwhattheheck`

RustChain source pin: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`.

RustChain, Filecoin, and Chia all turn a physical resource into something a network can verify, but they make different things scarce. Filecoin makes storage capacity and continued custody scarce: Proof of Replication establishes a unique encoded copy, while Proof of Spacetime repeatedly proves that sealed sectors remain stored. Chia makes committed disk space scarce and combines proofs of space with a sequential VDF from Timelords. RustChain instead makes verified hardware identity and antiquity economically relevant. Its current fingerprinting document describes six checks—clock skew, cache timing, SIMD behavior, thermal drift, instruction jitter, and anti-emulation—and expects at least five of six to pass.

“Time” therefore means different things. Chia’s Proof of Time is protocol sequencing: a VDF demonstrates sequential work after a challenge. RustChain’s antiquity is a hardware classification and reward weight. Current RustChain API docs use a PowerPC G4 example with a 2.5 antiquity multiplier, while the reward spec divides a fixed per-epoch pot proportionally by miner weight. A larger multiplier changes relative share; it does not by itself enlarge that epoch’s total issuance.

The hardware incentives diverge too. Filecoin’s 32/64-GiB sectors, recurring WindowPoSt deadlines, collateral, and slashing favor reliable storage infrastructure. Chia farmers commit disk space without needing the host computer to be old. RustChain explicitly values the machine itself, so an otherwise-obsolete PowerPC or x86 box can remain economically useful. That is a real reuse/e-waste angle, but it should not be oversold: old computers still consume electricity, and RustChain does not provide the storage service Filecoin does.

Economically, Filecoin combines simple minting with baseline minting linked to network storage growth, plus vesting and penalties. Chia’s published schedule halves block rewards every three years for four halvings, then keeps a perpetual tail reward. RustChain’s current PoA model is relative weighting inside an epoch pot. Put simply: Filecoin pays for persistent storage service, Chia secures consensus with space plus sequential time, and RustChain rewards authenticated physical-hardware participation with an antiquity bias.

Each has a clearer strength. Filecoin is the strongest fit for verifiable client storage. Chia is a clean space-based consensus design that avoids repeated hash competition. RustChain is most distinctive when the goal is preserving and authenticating real hardware. Its harder problem is calibration: physical fingerprints are protocol-specific measurements, not the same cryptographic object as PoSt or proof-of-space, so adversarial testing of thresholds and spoof resistance is central to keeping the antiquity premium credible.

Comparison body: 2,803 characters.

## Sources

- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/docs/hardware-fingerprinting.md
- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/specs/RIP_POA_SPEC_v1.0.md
- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/docs/API.md
- https://docs.filecoin.io/basics/the-blockchain/proofs
- https://docs.filecoin.io/basics/what-is-filecoin/crypto-economics
- https://docs.chia.net/chia-blockchain/consensus/proof-of-space-1.0/
- https://docs.chia.net/chia-blockchain/architecture/timelords/
- https://docs.chia.net/chia-blockchain/consensus/block-validation/block-rewards/

RTC payout identity / miner ID: `woahwhattheheck`.
