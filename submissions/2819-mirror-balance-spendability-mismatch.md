# #2819 low-severity finding: UTXO balance/box reads include account-mirror value that `/utxo/transfer` refuses to spend

## Source pin

- Upstream: `Scottcjn/Rustchain`
- `main`: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`
- `node/utxo_db.py` blob: `af2111d142d3254750e3cc0c65b4182354ae7329`
- `node/utxo_endpoints.py` blob: `f277fea736b040bee41283b344b0679a7621c54d`
- Bounty: `Scottcjn/rustchain-bounties#2819`

## Classification

**Low severity — API contract / code-quality edge case.** This is not a fund-creation, double-spend, or authorization bypass. It is a contradictory read-vs-spend contract for wallets containing account-mirror UTXOs.

## Summary

RustChain deliberately makes `account_mirror_boxes` ineligible for UTXO-native spending. `UtxoDB.get_coin_select_candidates()` excludes those rows before `/utxo/transfer` calls `coin_select()`. That is the correct safety policy for migrated/account-backed value.

The public read path does not apply the same eligibility policy:

- `UtxoDB.get_balance(address)` sums every unspent box owned by the address, including account-mirror boxes.
- `UtxoDB.count_unspent_for_address(address)` counts every unspent box, including mirrors.
- `UtxoDB.get_unspent_for_address(address)` returns every unspent box, including mirrors.
- `/utxo/balance/<address>` exposes the first two values as `balance_nrtc` / `balance_rtc` / `utxo_count`.
- `/utxo/boxes/<address>` exposes the unfiltered boxes without a spendability marker.
- `/utxo/transfer`, by contrast, selects from `get_coin_select_candidates()`, which excludes mirrors.

A mirror-only wallet therefore reports a positive UTXO balance and positive box count while its UTXO-spendable candidate total is zero.

There is a second user-visible contradiction in the transfer error path. When candidate selection returns no boxes, `/utxo/transfer` calls the unfiltered `get_balance(from_address)` and emits `Insufficient UTXO balance` with that raw positive number. For a mirror-only wallet holding 25 RTC, a request for 1 RTC can therefore be rejected as insufficient while the same error payload reports `balance_rtc: 25.0`.

## Relevant current code

### Read side

`node/utxo_db.py`:

```python
def get_balance(self, address: str) -> int:
    row = conn.execute(
        """SELECT COALESCE(SUM(value_nrtc), 0) AS total
           FROM utxo_boxes
           WHERE owner_address = ? AND spent_at IS NULL""",
        (address,),
    ).fetchone()
    return row['total']
```

`count_unspent_for_address()` and `get_unspent_for_address()` use the same `owner_address = ? AND spent_at IS NULL` eligibility boundary and do not exclude `account_mirror_boxes`.

`node/utxo_endpoints.py`:

```python
@utxo_bp.route('/balance/<address>')
def utxo_balance(address):
    balance_nrtc = _utxo_db.get_balance(address)
    utxo_count = _utxo_db.count_unspent_for_address(address)
    return jsonify({
        'address': address,
        'balance_nrtc': balance_nrtc,
        'balance_rtc': balance_nrtc / UNIT,
        'utxo_count': utxo_count,
    })
```

`/utxo/boxes/<address>` similarly calls `get_unspent_for_address()` and returns those rows directly.

### Spend side

`node/utxo_db.py:get_coin_select_candidates()` appends:

```sql
AND NOT EXISTS (
    SELECT 1 FROM account_mirror_boxes amb
    WHERE amb.box_id = utxo_boxes.box_id
)
```

when the provenance table exists.

`node/utxo_endpoints.py:/utxo/transfer` then uses that filtered method:

```python
utxos = _utxo_db.get_coin_select_candidates(from_address)
...
selected, change_nrtc = coin_select(utxos, target_nrtc)
```

but on failure reports the unfiltered balance:

```python
utxo_balance = _utxo_db.get_balance(from_address)
return jsonify({
    'error': 'Insufficient UTXO balance',
    'balance_nrtc': utxo_balance,
    'balance_rtc': utxo_balance / UNIT,
    ...
}), 400
```

## Reproduction

The companion script `2819-mirror-balance-spendability-mismatch-poc.py` uses the real current `UtxoDB` methods against a temporary SQLite DB.

It creates one 25 RTC unspent box owned by a wallet, registers that box in `account_mirror_boxes`, then compares the read-model values with the transfer candidate set.

Expected output on the pinned source:

```text
reported_balance_nrtc=2500000000
reported_utxo_count=1
listed_box_count=1
spendable_candidate_count=0
spendable_candidate_total_nrtc=0
mismatch=True
```

The PoC does not contact any production service or mutate any external state.

## Expected behavior

Public wallet responses should distinguish **total unspent UTXO state** from **UTXO-native spendable value** whenever account-mirror boxes exist. A caller should not be told it has an `N RTC` UTXO balance if the transfer endpoint considers zero of that value eligible.

Any of these contracts would remove the contradiction:

1. Add explicit `spendable_balance_nrtc`, `spendable_balance_rtc`, and `spendable_utxo_count` fields while retaining the current raw totals for observability.
2. Make `/utxo/balance` report spendable values by default and expose raw/mirror totals under separately named fields.
3. Mark `/utxo/boxes` entries with `spendable: false` / `reason: account_mirror` (or exclude them from the default listing).
4. At minimum, make the transfer failure payload report the filtered spendable balance rather than the raw `get_balance()` result, optionally including both values under unambiguous names.

The safest minimal patch is to centralize the account-mirror exclusion in a bounded/count/sum helper and reuse it for both transfer selection and the public spendable-balance fields, avoiding a second eligibility definition.

## Impact

- Wallets/UI can display funds as UTXO-available when the transfer API will never select those boxes.
- Automated clients can make futile transfer attempts based on `/utxo/balance` and receive a self-contradictory insufficient-funds response.
- `/utxo/boxes` does not tell a client that a listed mirror box is intentionally non-spendable on the UTXO route.

Because the underlying spend guard is fail-closed and value is not created or stolen, I classify this as **Low / API consistency + missing validation/metadata**, matching #2819's low-severity code-quality/test-gap tier.

## Duplicate boundary

This is distinct from the already-fixed mirror-box double-spend and coin-selection poisoning findings. Those fixes correctly prevent mirror boxes from being selected. This finding is about the remaining **read/error contract after that safety fix**: the same boxes still contribute to public `balance_nrtc`, `utxo_count`, and `/boxes` responses even though they are intentionally absent from the transfer candidate set.
