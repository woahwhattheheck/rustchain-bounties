# [SECURITY] BoTTube GPU job submission accepts non-positive / non-finite pricing inputs

Bounty: `Scottcjn/rustchain-bounties#71` — ongoing bug bounty  
Target: `Scottcjn/bottube`  
Source pin: `6af6b63f7a5a87353a30cd4552dc5c0e183a96af`  
Affected file: `gpu_marketplace.py` (blob `0182bcda014bd1f9e65b0634e8169d7b3afd286c`)  
Affected route: `POST /api/gpu/jobs/submit`  
Payout handle: `woahwhattheheck`  
Status: submitted for maintainer review; no acceptance or payout is asserted.

## Summary

`_coerce_float()` rejects booleans and values that cannot be converted to `float`, but it does not require the resulting number to be positive or finite. `submit_job()` then multiplies the two client-controlled values directly:

```python
estimated_mins, error = _coerce_float(data.get("estimated_mins"), 5)
max_price, error = _coerce_float(data.get("max_price_per_min"), 0.10)
escrow_amount = max_price * estimated_mins * 1.5

balance = get_agent_balance(agent['id'])
if balance < escrow_amount:
    return ...
```

A negative value therefore produces a negative escrow. For any ordinary non-negative balance, `balance < negative_escrow` is false, so the insufficient-balance gate is bypassed and the negative amount is inserted into `gpu_jobs.rtc_escrowed`.

This is distinct from the already-fixed `bottube#1451` bug: that PR made non-numeric values return 400 instead of crashing. It intentionally left valid floats unbounded, so negative/zero/non-finite values still pass `_coerce_float()` on current main.

## Safe source-level reproduction

Do **not** exercise this against production. The repository's existing test fixture creates a local agent with 1 RTC and registers the real `gpu_bp` blueprint.

With that fixture, submit:

```http
POST /api/gpu/jobs/submit
X-API-Key: bottube_sk_gpu_agent
Content-Type: application/json

{
  "job_type": "video_render",
  "estimated_mins": 5,
  "max_price_per_min": -1
}
```

The current arithmetic is deterministic:

```text
max_price      = -1.0
estimated_mins = 5.0
escrow_amount  = -1.0 * 5.0 * 1.5 = -7.5
balance        = 1.0
1.0 < -7.5     = False
```

So the request passes the balance check and writes a pending job with `rtc_escrowed = -7.5`, then returns that negative escrow in the success response.

The symmetric case also works: `estimated_mins=-5` with `max_price_per_min=0.1` produces `rtc_escrowed=-0.75`.

A second malformed numeric class is also accepted by `_coerce_float()`: strings such as `"nan"`, `"inf"`, and `"-inf"`. Python's `float()` accepts them. In CPython `sqlite3`, binding `float('nan')` into a `REAL NOT NULL` column is treated as NULL and raises `sqlite3.IntegrityError`, turning a client-controlled field into a server error; infinities are stored as REAL values.

## Downstream impact

The invalid escrow survives into the completion path:

```python
payment = min(duration_mins * price_per_min, row[3])
```

For a normal positive provider price and a negative `row[3]` escrow, `payment` becomes negative. The completion transaction then:

- stores the negative value in `gpu_jobs.rtc_paid`;
- adds the negative value to `gpu_providers.total_rtc_earned`;
- records the negative amount in `gpu_job_history`.

The current module's settlement path does not directly debit or credit the RustChain ledger here, so I am **not** claiming fund theft. The demonstrated impact is integrity corruption of GPU-marketplace escrow/payment accounting plus a balance-gate bypass and an input-triggered 500 for NaN.

## Expected behavior

`estimated_mins` and `max_price_per_min` should be finite positive values before they participate in escrow arithmetic. Non-positive and non-finite inputs should return a deterministic HTTP 400 and should never reach SQLite.

## Suggested fix

Keep the existing non-numeric behavior from `#1451`, then validate the converted value:

```python
import math

number = float(value)
if not math.isfinite(number) or number <= 0:
    return None, (jsonify({"error": "Positive finite numeric value required"}), 400)
```

Apply that contract to both `estimated_mins` and `max_price_per_min`. A defense-in-depth `CHECK (rtc_escrowed >= 0)` on new schemas/migrations would also keep invalid escrow from being persisted if another caller is added later.

## Regression coverage to add

For each of `estimated_mins` and `max_price_per_min`, assert HTTP 400 for:

- `-1`
- `0`
- `"-0.5"`
- `"nan"`
- `"inf"`
- `"-inf"`

Keep controls proving existing valid numbers and numeric strings still submit jobs successfully.

## Duplicate / ownership check

Before publication I checked current `Scottcjn/bottube` issues and PRs for `max_price_per_min`, `estimated_mins`, `negative escrow`, and GPU-price variants; no matching report was found. The full current comments on bounty `#71` contain no `max_price_per_min`, `estimated_mins`, or `negative escrow` report. Slack coordination/delegation exact searches for both field names were empty before the lane was claimed.

## Severity

Suggested **Medium** under bounty `#71` because this is a reproducible payment/escrow integrity bug and client-triggered error path, but not demonstrated fund theft or authentication bypass. Maintainer severity classification controls the award.
