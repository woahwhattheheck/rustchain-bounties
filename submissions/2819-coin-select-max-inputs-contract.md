# #2819 UTXO red-team: configurable `max_inputs` diverges from `coin_select()`'s fixed 20-input cap

## Classification

Low severity / code-quality and regression-test gap. This is non-exploitable as written on the current public transfer endpoint because that endpoint calls `get_coin_select_candidates(from_address)` with the default value. It is nevertheless a real helper-contract defect: the database API advertises a configurable `max_inputs`, validates arbitrary positive values, and documents equivalence with unbounded `coin_select()`, while `coin_select()` ignores that configuration and hard-codes 20.

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/2819

## Source pin

Reviewed `Scottcjn/Rustchain` fresh `main`:

- commit: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`
- `node/utxo_db.py` blob: `af2111d142d3254750e3cc0c65b4182354ae7329`
- `node/test_utxo_2819_rollback_mempool_and_bounded_select.py` blob: `d8c43a60acad067810f34e27cd6e7788c6036353`

## Vulnerability / defect class

Configuration-consistency bug in bounded coin selection. A helper parameter that is presented as the selection bound is not propagated to the actual selector, so callers using a non-default positive value can receive a candidate set that cannot fund a transfer even though the full wallet can fund it within the selector's own allowed input count.

## Root cause

`UtxoDB.get_coin_select_candidates()` exposes:

```python
def get_coin_select_candidates(
    self, address: str, max_inputs: int = COIN_SELECT_MAX_INPUTS
) -> List[dict]:
```

The helper validates any positive integer `max_inputs`, then fetches only:

- the cheapest `max_inputs + 1` boxes; and
- the dearest `max_inputs` boxes.

Its docstring says that feeding this bounded union to `coin_select()` yields the same result as feeding the full unspent set because both selector passes see an identical prefix.

However, `coin_select()` does not accept that parameter. It hard-codes `20` three times:

```python
if len(selected) > 20:
    ...
    if len(selected) > 20:
        capped = sorted_desc[:20]
```

Therefore the equivalence proof only holds when `max_inputs == 20` (or in wallet shapes where the omitted boxes happen not to matter). The public method accepts values for which its own documented invariant is false.

## Deterministic reproduction

Use ten unspent boxes for one address, each worth exactly 1,000 nRTC. Ask for candidates with `max_inputs=2`, then try to fund a 6,000 nRTC target.

The bounded query can return at most five distinct boxes:

- cheapest slice: 3 boxes (`max_inputs + 1`)
- dearest slice: 2 boxes (`max_inputs`)
- union: 5 boxes

`coin_select(full_wallet, 6000)` succeeds with six inputs. Six is below the selector's hard-coded 20-input limit.

`coin_select(get_coin_select_candidates(address, max_inputs=2), 6000)` fails because only five boxes were fetched.

A faithful local probe of the current SQL slice + current selector produced:

```text
bounded ids: ['b00', 'b01', 'b02', 'b09', 'b08']
bounded count: 5
full-wallet selection count: 6
bounded selection count: 0
```

So the same wallet and target change from spendable to insufficient solely because a supported helper parameter differs from the hard-coded selector constant.

## Expected vs actual

Expected: if `max_inputs` is a supported parameter, `get_coin_select_candidates(address, max_inputs=m)` and the selector consuming its result should use the same input cap `m`, preserving the helper's documented bounded/unbounded equivalence under that configuration.

Actual: the database helper uses `m`, while `coin_select()` always uses 20. Small `m` values can truncate the only candidate set before the actual selector has reached its own permitted input count.

## Existing regression coverage misses the parameterized case

`TestBoundedCoinSelectCandidates.test_selection_matches_unbounded_input` is a good invariant test, but every call uses the default:

```python
bounded = self.db.get_coin_select_candidates(address)
sel_full, change_full = coin_select(full, target)
sel_bounded, change_bounded = coin_select(bounded, target)
```

That means the test exercises exactly the one configuration where both sides happen to agree on 20. There is no test using a non-default `max_inputs` even though the helper explicitly accepts it.

A regression should add at least one non-default case such as `max_inputs=2` with ten equal-value boxes and a target requiring six inputs, and define the intended contract explicitly.

## Suggested fixes

Two safe choices:

1. Make the limit genuinely configurable end-to-end. Add `max_inputs=COIN_SELECT_MAX_INPUTS` to `coin_select()`, replace all hard-coded `20` uses with the parameter, and have callers pass the same value used to obtain candidates.

2. If configurability is not intended, remove the public `max_inputs` knob from `get_coin_select_candidates()` or reject values other than `COIN_SELECT_MAX_INPUTS`. That makes the existing equivalence claim true instead of silently accepting unsupported configurations.

Whichever contract is chosen, keep a regression that compares bounded vs full selection under every supported input-cap configuration.

## Scope / impact note

I am classifying this as Low rather than claiming a production fund-movement issue. The current `/utxo/transfer` path calls `get_coin_select_candidates(from_address)` without overriding the default, so its present 20/20 pairing is unaffected. The defect matters to library callers, future configuration changes, and maintenance: the helper is explicitly parameterized and validated but only one parameter value preserves its documented behavior.
