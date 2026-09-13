# #16471 paid finding — non-finite money ceilings fail open

Reporter/payout identity: **@woahwhattheheck**  
Discovery/validation seat: **Z-TuringFurnace-20260913T1025-K2V7 / GPT-5.6 Sol**  
Upstream bounty: `Scottcjn/rustchain-bounties#16471`  
Requested route: the bounty's posted **+10 RTC per confirmed defect**. No acceptance, earning, or settlement is claimed until the maintainer confirms it.

## Filing status

The finding is ready for upstream filing, but this GitHub integration cannot write to the sponsor repository. On 2026-09-13 both an upstream issue-create attempt and a direct comment attempt on #16471 returned `403 Resource not accessible by integration`. The local fork has Issues disabled, so this branch is the durable handoff carrier. **Do not describe this memo as an upstream filing receipt.**

## Current-main defect

Upstream current main accepts monetary safety configuration through Python `float`:

- `scripts/bounty_payout.py`: `MAX_CLAIM_RTC=float(os.environ.get("MAX_CLAIM_RTC","25"))`
- `scripts/docstring_gate.py`: `MAX_RTC=float(os.environ.get("MAX_RTC","25"))`
- `scripts/docstring_gate.py`: `MAX_RTC_PER_WEEK=float(os.environ.get("MAX_RTC_PER_WEEK","40"))`

Their control flow then relies on ordered comparisons:

```python
if amount > MAX_CLAIM_RTC:
    ...
if already + amount > MAX_RTC_PER_WEEK:
    ...
if amount > MAX_RTC:
    ...
```

`float("NaN")` is accepted by Python and all of those `>` comparisons are false. As a result:

1. `MAX_CLAIM_RTC=NaN` silently removes the payout-time per-claim ceiling and an otherwise eligible oversized amount can reach `transfer()`.
2. `MAX_RTC=NaN` silently removes the docstring per-claim human-review ceiling.
3. `MAX_RTC_PER_WEEK=NaN` silently removes the rolling weekly docstring ceiling, allowing the gate to proceed toward payable labels despite exceeding the configured backstop.

That is a concrete #16471 silent-success/wrong-effect path: the workflow can complete successfully while a money-control effect configured as a safety ceiling does not happen.

The same parser class also applies to `RATE_RTC` and `RATE_PER_FUNC`; the sponsor-ready patch hardens those adjacent money inputs rather than leaving a one-line non-finite ingress next to the repaired ceilings. Reward classification remains the maintainer's decision; this carrier does not self-count multiple payouts.

## Duplicate fence

Before preserving the finding, upstream issue search for exact `MAX_CLAIM_RTC` + `NaN` and `MAX_RTC_PER_WEEK` + `NaN` returned zero matching reports. A plain `MAX_CLAIM_RTC` search returned only bounty #16471 itself.

## Evidence and repair

- `16471-ztf-nan-money-ceilings-repro.py` is zero-network and proves both the vulnerable NaN comparison behavior and strict rejection of `NaN`, `sNaN`, ±`Infinity`, zero, negative, malformed text, and finite-Decimal values that overflow when converted to float.
- `16471-ztf-nan-money-ceilings.patch` is a sponsor-ready source patch. It parses money configuration through `Decimal`, requires finite positive values, checks the final float is still finite, and exits before payout/gate work if configuration is invalid.

The patch intentionally does not mutate a payout endpoint, claimant issue, wallet, label, or sponsor branch.

## Upstream filing text

> Current main parses `MAX_CLAIM_RTC`, `MAX_RTC`, and `MAX_RTC_PER_WEEK` with Python `float`. `float("NaN")` is accepted, and ordered comparisons such as `amount > cap` and `already + amount > cap` are false when the cap is NaN. Therefore the payout per-claim ceiling and both docstring ceilings can silently disappear while the scripts continue successfully. This is the wrong-effect/green-run class #16471 asks for. Reject malformed/non-finite/non-positive money configuration before candidate enumeration, eligibility mutation, or transfer. I am submitting this as a paid #16471 defect report and intend to receive the posted defect reward if confirmed; I am not claiming payment until maintainer confirmation.
