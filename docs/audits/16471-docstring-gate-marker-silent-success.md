# Docstring gate: payable labels can commit without the payout marker

**Bounty:** Scottcjn/rustchain-bounties#16471  
**Payout identity:** `woahwhattheheck`  
**Audited source:** `scripts/docstring_gate.py` blob `f4b37d6840aedcbd7266c25cd1e9b957534c614b`

## Finding

The docstring gate can complete successfully after applying payout-eligible labels even when publishing the verification comment fails. That comment contains the machine-readable `<!-- rtc-payout-amount:... -->` marker used by the weekly earnings/cap scan.

The success path currently does the following:

1. Calls `add_labels(num, "docstring-verified", "claimed")`.
2. Handles label failure by returning nonzero.
3. Calls `gh(["issue", "comment", ...], None)` to publish the verification result and `rtc-payout-amount` marker.
4. Ignores that call's return value.
5. Returns `0`.

`gh()` returns its default when the command exits nonzero unless `strict=True`. The verification-comment call is not strict and its result is unused. Therefore a transient GitHub API, authentication, rate-limit, or network failure at step 3 produces a green gate after the labels have already committed.

## Silent-success impact

The intended externally visible effect is incomplete even though the gate reports success:

- the claim remains labeled `docstring-verified` and `claimed`, so downstream payout handling can treat it as payable;
- the claimant receives no verification/payout-arithmetic comment;
- the `rtc-payout-amount` marker is absent;
- `weekly_docstring_git_earnings()` requires that marker when summing prior verified awards, so the award can be omitted from weekly-cap accounting;
- a later claim can consequently pass a cap calculation that should include the earlier award.

This is the opposite ordering from the previously addressed case where a success comment could precede failed labels. Labels are now guarded, but the marker publication that follows them is still allowed to fail silently.

## Concrete failure path

```text
qualifying contribution
  -> payout/cap checks pass
  -> add_labels("docstring-verified", "claimed") succeeds
  -> `gh issue comment` exits nonzero
  -> gh(..., default=None, strict=False) returns None
  -> caller ignores None
  -> main returns 0
```

At exit, the repository state advertises a verified/claimed contribution, while the accounting record expected by the same script is missing.

## Remediation

Make marker publication a required effect. If the verification comment cannot be written, the gate should exit nonzero and compensate by removing the newly applied payout labels or by replacing them with a clear `needs-human` hold. Longer term, weekly accounting should read a dedicated machine ledger rather than a best-effort human-facing comment.

The minimal invariant is:

> A run must not return success unless the payout labels and the machine-readable award record are both durable, or neither is considered payable.
