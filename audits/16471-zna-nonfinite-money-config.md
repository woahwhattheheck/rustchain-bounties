# RustChain #16471 — non-finite money configuration fails open

**Operation:** `RUSTCHAIN-16471-NONFINITE-MONEY-CONFIG-ZNAL7V2-20260913`  
**Audit source:** `Scottcjn/rustchain-bounties@ea011e8d8c7d770115cd7ea2bb88482eff94ac7f`  
**Reporter / donor carrier:** `@woahwhattheheck` / `Z-NoetherAegis-913937-L7V2`  
**Scope:** `scripts/docstring_gate.py`, `scripts/bounty_payout.py`  
**Safety:** source audit + zero-network regression only. No live wallet, transfer, issue-label, or payout action was performed.

## Executive finding

Several money-bearing environment settings are parsed with raw `float(...)` and never required to be finite and strictly positive. Python deliberately accepts `NaN`, `Infinity`, and `-Infinity`, and ordered comparisons with `NaN` are false. That turns the intended payout ceilings into fail-open controls.

The strongest #16471 path is a terminal silent-success state in the docstring gate:

1. `RATE_PER_FUNC=NaN`.
2. A normal merged docstring claim produces `amount = round(doc_count * RATE, 2) == NaN`.
3. `already + amount > MAX_RTC_PER_WEEK` is false.
4. `amount > MAX_RTC` is also false.
5. The gate applies `bounty-eligible` + `docstring-verified`, posts `<!-- rtc-payout-amount: nan -->`, prints `verified ... -> nan RTC`, and returns 0.
6. `bounty_payout.py` only accepts trusted markers matching `([\d.]+)`, so `nan` has **no trusted amount marker** and is skipped.
7. Future gate runs see the payable labels and return `already adjudicated; skipping`.

Result: the workflow reports successful verification and creates terminal payable state, while the payout worker cannot ever parse the amount that the gate itself committed.

## Independently reachable fail-open ceilings

These are separate source-visible money decisions. Maintainers can decide whether to count them as separate confirmed defects under #16471.

### A. `MAX_RTC` can disable the per-claim auto-pay ceiling

Current source:

```python
MAX_RTC = float(os.environ.get("MAX_RTC", "25"))
...
if amount > MAX_RTC:
    ... needs-human ...
```

With `MAX_RTC=NaN`, `30.0 > NaN` is false. A 30 RTC verified claim therefore bypasses the stated 25 RTC auto-pay ceiling and continues into payable labels/marker generation. `MAX_RTC=Infinity` has the same practical fail-open effect for every finite amount.

### B. `MAX_RTC_PER_WEEK` can disable the rolling weekly ceiling

Current source:

```python
MAX_RTC_PER_WEEK = float(os.environ.get("MAX_RTC_PER_WEEK", "40"))
...
if already + amount > MAX_RTC_PER_WEEK:
    ... weekly-cap-reached ...
```

With `MAX_RTC_PER_WEEK=NaN`, `44.0 > NaN` is false. A contributor already near the 40 RTC/week limit can receive another payable claim even though the intended cap is exceeded. `Infinity` likewise disables the upper bound.

### C. `MAX_CLAIM_RTC` can disable the payout-time hard ceiling

Current source:

```python
MAX_CLAIM_RTC=float(os.environ.get("MAX_CLAIM_RTC","25"))
...
amount=float(m.group(1))
if amount > MAX_CLAIM_RTC:
    ... skipping ...
...
transfer(..., amount)
```

With `MAX_CLAIM_RTC=NaN`, a trusted numeric marker such as 30 RTC passes the hard-ceiling check because `30.0 > NaN` is false and reaches `transfer(...)`. `Infinity` again disables the ceiling for every finite amount.

This is independent of the separate `MAX_PER_RUN` aggregate-cap repair: `MAX_CLAIM_RTC` is the per-claim payout ceiling.

## Adjacent configuration surface

`RATE_RTC` in `bounty_payout.py` is also a raw float and should be validated by the same helper. Its exact node-side effect depends on how the wallet endpoint parses non-standard JSON numeric constants, so this report does **not** mint a separate defect claim from it. The donor patch closes it preventively because it is directly money-bearing.

Malformed text currently raises at import, but `NaN`/infinities do not. Zero/negative values are also nonsensical for rates/ceilings and should fail before any provider/GitHub interaction.

## Zero-network proof

`audits/16471-zna-nonfinite-money-config-repro.py` pins:

- `RATE_PER_FUNC=NaN` => gate reaches `verified-green`, labels payable, marker is unparseable by the current payout regex, later gate is terminal.
- `30.0 > NaN` and `41.0 > NaN` are both false.
- `Infinity` disables the same upper-bound comparisons.
- the proposed parser accepts ordinary positive finite values and rejects NaN, infinities, zero, negative, and malformed text.

Run:

```bash
python audits/16471-zna-nonfinite-money-config-repro.py
```

Expected: 4 tests, all PASS, no network.

## Proposed repair

`audits/16471-zna-nonfinite-money-config.patch` is an upstream-base donor patch. It deliberately does **not** touch `MAX_PER_RUN`, scheduler fairness, provider pagination, wallets, or transfers.

For every money-bearing environment rate/ceiling in this lane:

1. parse once at startup;
2. require `math.isfinite(value)`;
3. require `value > 0`;
4. exit non-zero before candidate enumeration, GitHub writes, or transfer attempts if invalid.

Covered settings:

- `bounty_payout.py`: `RATE_RTC`, `MAX_CLAIM_RTC`
- `docstring_gate.py`: `RATE_PER_FUNC`, `MAX_RTC`, `MAX_RTC_PER_WEEK`

The patch preserves the existing float arithmetic/transfer contract; it only closes invalid configuration states. A later Decimal migration can be layered independently.

## Duplicate / custody note

The immediate pointer for this audit was the independent review release `ZARG-Q5N2`, which explicitly called out `MAX_CLAIM_RTC` and docstring `MAX_RTC` / `MAX_RTC_PER_WEEK` as adjacent non-finite follow-ups after the separate `MAX_PER_RUN` repair. That discovery pointer is preserved here. Fresh workspace searches before TAKE found no earlier durable owner or sponsor submission for this exact non-finite-ceiling seam. Earlier materially-same sponsor filing, if surfaced, wins.

## Reward / payment boundary

This carrier is evidence and a proposed repair only. It does **not** assert sponsor confirmation, acceptance, an RTC award, transfer, withdrawability, or USD value.
