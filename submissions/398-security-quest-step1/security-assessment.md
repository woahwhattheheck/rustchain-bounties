# Bounty #398 — Step 1 Security Assessment

**Target:** `Scottcjn/Rustchain`
**Source snapshot:** `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`
**Bounty:** `Scottcjn/rustchain-bounties#398`, Step 1 only (10 RTC)
**Assessment date:** 2026-09-17

## Scope and method

This is a source review of the current public RustChain main branch. I did not probe production, move funds, or claim that a code-level observation is exploitable on a deployed node without the additional conditions described below. The review follows the Step 1 requirements: explain `/attest/submit`, hardware fingerprinting/VM resistance, epoch reward calculation/distribution, and one potential attack vector with concrete code references.

## 1. How `/attest/submit` works

The documented lifecycle is challenge/evidence driven: a miner collects system information and hardware measurements, builds a fingerprint, signs its attestation, and submits it to `POST /attest/submit`. The node verifies the submission, checks hardware uniqueness, persists accepted attestation state, and enrolls the miner into the epoch used for reward calculation. See `docs/attestation-flow.md`, especially the lifecycle and validation overview near lines 1–45.

The current integrated node has more hardening than the high-level diagram suggests. Its database schema keeps replay/identity and reward state separate: `epoch_enroll` is keyed by `(epoch, miner_pk)`, while `miner_attest_recent` stores the most recent attestation result, device family/architecture, entropy score, fingerprint status, source IP, signing key, and fingerprint-check JSON. Hardware bindings are also stored separately. These structures are initialized in `node/rustchain_v2_integrated_v2.2.1_rip200.py` around lines 1850–2100.

The important trust boundary is that reward-relevant hardware identity should not come directly from an unsigned client label. Current code explicitly recognizes that. In the integrated node, `resolve_enroll_weight_device()` prefers `miner_attest_recent.device_family/device_arch`, which were derived from attestation evidence, and only falls back to request-body device data for legacy/pre-migration rows. The adjacent `_fingerprint_check_passed()` also fails closed unless a structured check contains literal boolean `passed is True`; an empty object or truthy string such as `"false"` does not count as a pass. Rotating fingerprint checks are seeded by the prior epoch block hash and scored against measured evidence. See `node/rustchain_v2_integrated_v2.2.1_rip200.py` around lines 2500–2850.

The overall shape is therefore: signed/challenge-bound request -> server-side evidence validation -> durable recent-attestation state -> per-epoch enrollment snapshot -> rewards/producer logic. That separation matters because a miner-controlled `device_arch` string is economically sensitive: vintage tiers can carry higher reward weights.

## 2. How fingerprinting resists VM farms

RustChain does not rely on one Boolean like `is_vm`. The attestation documentation describes multiple physical signals—clock drift/jitter, cache timing, SIMD identity, thermal entropy, instruction jitter, and behavioral/hypervisor indicators. The current integrated implementation further cross-checks claimed architecture against observed capabilities. For example, modern SIMD evidence can contradict a vintage-x86 claim, and a capability-limited architecture is excused from an active rotating check only when the server-derived architecture supports that exception and the payload supplies native evidence.

That multi-signal design raises the cost of a VM farm in three ways.

First, evidence is expected to be internally coherent. A miner cannot safely gain a vintage bonus by changing only a family/architecture label because reward-device derivation and vouching compare the claim with measured characteristics. Current comments in the integrated source document why the server must not trust raw `device_family/device_arch` for high-paying tiers; the implementation caps unvouched high-paying claims to a neutral modern identity. See `node/rustchain_v2_integrated_v2.2.1_rip200.py` around lines 3240–3650 for the x86/SIMD cross-validation and reward-tier vouching logic.

Second, checks rotate by epoch. `evaluate_rotating_fingerprint_checks()` obtains a measurement nonce and active-check set derived from the previous epoch block hash. A farm that wants to fake every epoch has to keep producing mutually consistent evidence for the changing active subset rather than hard-code one static perfect result. The parser also treats absent or malformed evidence as failure unless a narrowly defined capability-limited path applies.

Third, the schema separates recent attestation from hardware binding and per-epoch enrollment. That creates places to detect cross-wallet reuse and prevents a later request from casually overwriting an already established epoch identity. The security objective is not “prove a VM is impossible”; it is “make scaled synthetic identities materially harder and prevent client-provided metadata alone from buying a higher economic weight.”

## 3. How epoch rewards are calculated and distributed

The RIP-200 reward path is implemented in `node/rip_200_round_robin_1cpu1vote.py`. `calculate_epoch_rewards_time_aged()` first derives the active RIP-309 fingerprint checks from the previous block hash and calculates chain age. For the target epoch it **prefers `epoch_enroll` as the canonical per-epoch miner/weight snapshot**. For each enrolled miner it reads the current stored architecture/fingerprint information, then computes fixed-point weights and distributes the epoch reward proportionally. The antiquity multiplier decays vintage bonus over chain age while sub-1.0 anti-farm penalties remain penalties. See approximately lines 480–760.

This snapshot-first behavior is important for settlement determinism. The function includes a compatibility fallback when an epoch has no `epoch_enroll` rows: it queries `miner_attest_recent` inside the epoch time window. The source itself warns that delayed settlement can make this fallback drop miners who re-attested outside that historical window. In normal populated epochs, however, `epoch_enroll` is the preferred source and avoids that time-window ambiguity.

The integrated node also guards epoch settlement with explicit finalized/settled state and transactional claiming. In its simpler local settlement helper, it starts `BEGIN IMMEDIATE`, rejects already-settled epochs, claims settlement before applying balances, filters non-positive/non-finite weights, computes each miner's fraction of total weight, and rolls back the settlement claim together with partial credits on exception. See `node/sophia_elya_service.py` roughly lines 120–230 for a compact version of the same invariants.

## 4. Potential attack vector — unenrolled miner remains producer-eligible (fail-open producer gate)

**Potential impact:** producer-selection policy bypass / Sybil surface; consensus impact depends on which block-validation path is authoritative.

The freshest concrete risk I found is not a fingerprint parser bug; it is the boundary between attestation enrollment and producer scheduling.

`node/rustchain_block_producer.py` loads `epoch_enroll` weights for the current epoch and puts `enroll_weight=None` on an attested miner if no row exists. `_miner_selection_weight()` excludes a miner only when `enroll_weight is not None and enroll_weight <= 0`. If the row is absent, the function falls through to heuristic device weighting and ultimately returns at least `1.0`. `_build_balanced_producer_rotation()` then includes every miner whose calculated weight is greater than zero. See `node/rustchain_block_producer.py` around lines 260–385.

That means “explicitly enrolled with zero/negative weight” is fail-closed, but “not enrolled at all” is fail-open. A miner that can remain in `miner_attest_recent` while avoiding an `epoch_enroll` row can still receive local producer turns from the heuristic path. The repository's current draft `rips/docs/RIP-0202-fail-closed-producer-enrollment.md` independently documents the same invariant: absent miners currently fall through to heuristic producer weight, while a correct fix needs a deterministic, finalized enrollment snapshot before absence can safely mean exclusion.

The draft also explains why this is not a one-line patch. Producer selection is deterministic; if nodes disagree about enrollment completeness, immediately treating absence as zero can make them choose different producers. The safe direction is the RIP-202 design: derive a chain-replicated enrollment snapshot, seal it deterministically, activate the fail-closed rule at a common chain-defined boundary, and then interpret absence from a finalized snapshot as zero producer weight.

There is an additional architectural caveat: the same RIP notes that current producer selection is advisory in parts of peer block application, so the real security boundary is not just the local rotation builder. A complete remediation should ensure the authoritative block-acceptance path validates the expected producer from the same deterministic enrollment state; otherwise hardening only the local scheduler can leave inbound-block acceptance looser than outbound production.

### Recommended mitigation

1. Finish the deterministic enrollment snapshot/finalization prerequisites described by RIP-202 instead of changing `None` to zero unconditionally.
2. After coordinated activation, treat an attested miner absent from a **finalized** epoch snapshot as weight `0.0`.
3. Fail closed on malformed finalized enrollment weights.
4. Make inbound block validation enforce the same expected-producer rule derived from the same chain-replicated snapshot.
5. Add cross-node determinism tests proving identical snapshots yield byte-identical producer rotations and that an attested-but-unenrolled miner never appears after activation.

## Conclusion

The current code has substantial defense in depth around hardware attestation: multi-signal fingerprints, explicit Boolean validation, rotating checks, server-derived/vouched hardware identity, durable hardware binding, and an epoch snapshot preferred by reward settlement. The most important residual boundary I found is producer eligibility: the scheduler distinguishes explicit zero-weight enrollment from missing enrollment and currently gives the latter a nonzero heuristic weight. RustChain already has a technically sound draft direction in RIP-202; the critical requirement is to make the enrollment snapshot and its activation deterministic across nodes before converting the producer gate from fail-open to fail-closed.

No payout is asserted by this artifact. It is a public, source-pinned Step 1 deliverable published through the sponsor-documented controlled-repository fallback after the GitHub App could not comment on bounty #398.