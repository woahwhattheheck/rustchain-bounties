# [UTXO-BUG] Zero-output `mining_reward` consumes the block reward slot

Bounty: Scottcjn/rustchain-bounties#2819  
Source reviewed: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`  
Affected path: `node/utxo_db.py`, `UtxoDB.apply_transaction()`  
Class: missing validation / reward-liveness edge case  
Requested severity: **Low (25 RTC)**

## Summary

`UtxoDB.apply_transaction()` accepts an internally-authorized `mining_reward` transaction with **no outputs**. The call returns success and inserts a confirmed `utxo_transactions` row for that `block_height`, even though it creates no reward box and transfers no value.

The same function also enforces one `mining_reward` transaction per block height by counting existing `utxo_transactions` rows. As a result, after the zero-output transaction succeeds, a later legitimate reward for the same height is rejected by the one-reward-per-block guard.

This is not the previously reported unlimited-minting, mint-authority, or multiple-coinbase issue. The current guards for those cases can all be present while this reward-liveness bug remains: an **authorized but empty** coinbase consumes the sole reward slot.

## Current control flow

At the pinned source revision:

1. A transaction with `tx_type='mining_reward'` and `_allow_minting=True` passes the internal mint authorization gate.
2. The per-height query allows it when no prior mining reward exists at that height.
3. Empty `inputs` are allowed for minting types.
4. `_normalize_outputs([])` returns an empty list successfully.
5. The explicit empty-output rejection only runs when `tx_type not in MINTING_TX_TYPES`, so it deliberately skips this transaction.
6. `output_total = sum([])` is `0`, which is below the 150 RTC coinbase cap.
7. No output boxes are inserted, but a confirmed `utxo_transactions` record with `tx_type='mining_reward'` and the target `block_height` is inserted.
8. A subsequent valid mining reward at the same height sees that row and fails the `COUNT(*) > 0` check.

## Reproduction

The companion script `2819-zero-output-mining-reward-slot-poisoning-poc.py` exercises the production `UtxoDB` directly against a local temporary SQLite database:

```bash
python3 submissions/2819-zero-output-mining-reward-slot-poisoning-poc.py /path/to/Rustchain
```

Expected output on the affected revision:

```text
REPRODUCED: empty authorized mining_reward consumed the only reward slot for block 424242
```

The script asserts all of the following:

- the zero-output authorized mint returns `True`;
- a confirmed `mining_reward` row exists at the chosen height with `outputs_json == '[]'`;
- a legitimate 1 RTC reward at that same height returns `False`;
- the intended recipient still has a zero UTXO balance.

## Expected behavior

A `mining_reward` should not be accepted unless it creates at least one positive-value reward output. A rejected empty reward must not create a transaction row or consume the block-height reward slot.

## Actual behavior

An empty authorized reward can succeed and permanently occupy the height's one allowed `mining_reward` record, suppressing a later legitimate payout at that height.

## Impact

This is a liveness/accounting failure rather than a public fund-theft path. A buggy settlement caller, bad internal payload, or future internal integration that constructs an empty reward can cause the node to record the block as having received its sole mining reward while paying nobody. Retrying the correct reward at the same height then fails.

I am **not** claiming that an unauthenticated network client can set `_allow_minting`; the finding is the missing state-transition validation at the internal mint boundary.

## Suggested fix

Reject empty mint output sets before the per-height slot can be committed. For example, after output normalization:

```python
if tx_type in MINTING_TX_TYPES and not outputs:
    return abort()
```

For stronger defense in depth, require `output_total > 0` for `mining_reward` and, if the protocol has a fixed expected coinbase shape, validate that shape explicitly. Add a regression test proving a rejected zero-output mint leaves the block height available for the next valid reward.

## Verification note

The source path and exact pinned revision were verified through the GitHub repository API. This report does not claim a full upstream checkout test from the current shell environment; the companion PoC is intentionally self-contained apart from importing the pinned production `node/utxo_db.py` and is suitable for maintainer reproduction.