# RustChain vs Helium: two different DePIN proofs (September 2026)

**Bounty:** Scottcjn/rustchain-bounties#12442  
**Claimant / miner_id:** `woahwhattheheck`  
**RustChain source pin:** `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

A fair comparison has to separate Helium's history from its current network. Helium's own documentation says Proof-of-Coverage was removed on July 6, 2026. Current IoT Hotspots earn HNT for carrying LoRaWAN device traffic, and onboarding is permissionless for any compatible LoRaWAN gateway; Helium even documents Raspberry Pi + RAK concentrator builds. So the live Helium model is increasingly "did this gateway deliver useful wireless data?", not the older model of earning from RF coverage challenges.

RustChain verifies a different resource: the physical computer itself. On current RustChain main, the protocol documentation describes six hardware-fingerprint signals/checks: clock drift, cache timing, SIMD identity, thermal behavior, instruction-path jitter, and anti-emulation heuristics. Those signals are used to distinguish physical hardware from common VM/emulator patterns before antiquity-weighted rewards are applied. The documented multiplier tables give a PowerPC G4 a 2.5x base multiplier and modern x86_64 1.0x, while the mining documentation assigns virtual machines 0.0x. RustChain's scarce input is therefore hardware identity and age rather than radio coverage.

The hardware economics diverge for the same reason. A Helium operator needs a LoRaWAN gateway, radio/concentrator hardware, antenna placement, and useful local device traffic, but no longer necessarily a proprietary hotspot: current Helium docs say any LoRaWAN gateway may onboard, and provide a Raspberry Pi + RAK2287 reference build. RustChain can use existing general-purpose computers and deliberately weights older architectures more heavily. Helium optimizes deployment of useful connectivity; RustChain optimizes preservation and diversity of compute hardware.

The token models also solve different problems. Helium's HNT uses a two-year halving schedule plus burn-and-mint economics: HNT is burned to create USD-pegged Data Credits, while capped net emissions can replenish reward availability. Helium's documentation describes an approximately 223 million HNT HIP-20 max-supply target. RustChain's current docs describe roughly 24-hour reward epochs, a 1.5 RTC epoch reward, antiquity multipliers, and an 8.3 million RTC supply cap.

Anti-spoofing is the most interesting contrast. Helium historically used Proof-of-Coverage to test geographic radio coverage; because that mechanism is now retired, it would be misleading to judge today's network only by its old PoC attack surface. Current IoT onboarding binds a hotspot key to a wallet, asserts physical location, and rewards the device data a gateway actually carries. RustChain instead examines timing, thermal, microarchitectural, and virtualization signals. Those checks can raise the cost of large VM farms and reject common emulation environments, but they should be treated as an adversarial measurement system rather than an unbreakable hardware identity oracle.

Where Helium wins is clear external utility: enterprises and developers can buy wireless data transport, and operators can place gateways where that demand exists. Where RustChain is distinctive is turning otherwise-obsolete physical machines into consensus participants and making hardware age economically relevant. The trade-off is equally clear: RustChain must keep its fingerprints robust as virtualization and emulation improve, while Helium must keep gateway rewards aligned with real traffic and useful coverage. They are both DePIN, but they prove different things: **Helium proves service; RustChain tries to prove substrate.**

## Sources checked

### RustChain (pinned source)
- `docs/PROTOCOL.md` / `docs/MINING_GUIDE.md` / `docs/protocol-overview.md` — six hardware-fingerprint checks and anti-emulation model.
- `docs/PROTOCOL_v1.1.md` and `docs/mining.html` — antiquity multipliers including PowerPC G4 2.5x, modern x86_64 1.0x, VM 0.0x.
- `docs/token-economics.md` and `docs/ARCHITECTURE_OVERVIEW.md` — epoch reward / antiquity weighting and 8.3M RTC cap.

### Helium (official documentation, checked 2026-09-16)
- https://docs.helium.com/network-data/oracle-data/ — Proof-of-Coverage removed July 6, 2026.
- https://docs.helium.com/iot/onboard-a-hotspot/ — any LoRaWAN gateway may onboard; Hotspots earn HNT for device data carried.
- https://docs.helium.com/iot/packet-forwarders/balena/ — Raspberry Pi + RAK2287 reference Hotspot build.
- https://docs.helium.com/tokens/hnt-token/ — HNT halving, max-supply, burn-and-mint, and net-emissions mechanics.

No sponsor acceptance or payout is asserted by this file; it is a public, timestamped submission artifact for review.
