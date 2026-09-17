# Bounty #13224 — RIP-0301 critique: hardware resale creates a lineage-reset dilemma

Source pin for the protocol draft: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`, `rips/docs/RIP-0301-tip-credits-atlas-economy.md`.

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/13224  
RFC discussion: https://github.com/Scottcjn/bottube/issues/1309

## Finding

The existing identity-rotation critique correctly argues that anti-abuse history cannot simply be keyed to the public `beacon_id`: otherwise one operator can retire A1, re-attest as A2, and reset repeat-edge, reciprocity, concentration, and cycle history. But binding that history permanently to the **physical PoA hardware lineage** creates the opposite failure mode: **second-hand hardware can be poisoned by its previous owner**.

That matters unusually much for RustChain because antiquity and reuse are part of the system's economic premise. Old hardware is expected to remain useful and can change hands. If a PowerPC box or other attested device carries its economic abuse history forever, a seller can deliberately wash-tip or trip concentration/cycle penalties before sale. The innocent buyer then inherits reduced maturation, Atlas eligibility, or economic reputation because the protocol cannot distinguish “same operator rotating identity” from “new operator bought the machine.” This creates a lemons market: buyers cannot know whether a device lineage has hidden protocol debt, and otherwise-useful old hardware becomes less transferable.

The obvious fix — clear history on ownership transfer — is also exploitable. An attacker can repeatedly “sell” the device between controlled identities or wallets and obtain the same reset that persistent lineage was meant to prevent.

## Transfer-safe rule

Treat **hardware continuity** and **economic-controller continuity** as separate state:

```text
Beacon principal = (hardware_lineage, controller_lineage, generation)
```

A controller transfer should be a finalized chain event authorized by both the old and new controller. On transfer at height `h`:

1. the old Beacon identity is disabled for new allowance immediately;
2. the transfer does **not** refill the current epoch allowance;
3. tips received before `h` remain attributable to the old controller;
4. the new controller enters a maturation quarantine for `L = longest anti-abuse lookback` (for example, seven days): it may operate the service and receive raw/reputation tips, but those tips cannot mature into RTC or create yield-bearing economic reputation during quarantine;
5. after `L`, behavioral graph history may reset for a genuinely new controller, while hardware-specific integrity/tamper evidence remains with `hardware_lineage`;
6. another transfer before quarantine ends restarts the quarantine.

The key invariant is:

```text
transfer_reset_gain <= 0
```

If an attacker transfers every `d < L` to shed wash history, the device never exits quarantine and matures 0 RTC. If the attacker waits `L`, the transfer gives no faster reset than simply waiting out the same anti-abuse lookback. A legitimate buyer pays a bounded waiting period but does **not** inherit permanent behavioral guilt from a stranger.

## Suggested RIP wording

> PoA hardware lineage proves device uniqueness, not operator identity. Economic anti-abuse history MUST NOT become a permanent encumbrance on transferable hardware; controller transfer MUST preserve spent allowance and impose a maturation quarantine at least as long as the anti-abuse lookback, while hardware-integrity evidence remains device-bound.

This closes the reset loophole without turning vintage hardware into permanently tainted property.

## Novelty / review notes

Fresh review of the current BoTTube #1309 discussion found the accepted sequential-identity-rotation critique, which preserves anti-abuse state across A1→A2 identity churn on the same hardware. This submission addresses the distinct ownership-transfer boundary: a real new owner should not inherit permanent behavioral penalties, while a fake sale must not erase them. Searches of the current discussion found no prior critique framed around hardware resale or a new owner inheriting anti-abuse history.

## Submission status

The required direct critique comment on `Scottcjn/bottube#1309` was attempted through the connected GitHub integration and returned `403 Resource not accessible by integration`. The sponsor submission guide documents public publication / file-PR routes for that connector limitation, so this file is the public, timestamped fallback artifact. No sponsor acceptance or payout is asserted here.

## Payout identity

GitHub / hosted payout identity: `woahwhattheheck`.

Bounty #13224 states that a native `RTC…` wallet is required. No native wallet address is invented or asserted by this artifact; that requirement remains to be satisfied when the sponsor claim is filed through a user-authenticated or sponsor-supported path.
