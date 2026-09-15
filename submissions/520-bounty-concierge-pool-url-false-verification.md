# #520 Bug Hunter report — arbitrary `--pool-url` is reported as verified

Bounty: `Scottcjn/rustchain-bounties#520` (Bug Hunter, 3 RTC per accepted real bug)

Target: `Scottcjn/bounty-concierge`

Pinned target main: `8af8fdf80b3dc3816d3e13f4e99e2a1cab331cbc` (fresh read on 2026-09-15)

## Summary

`concierge mine` treats any non-empty explicit `--pool-url` string as a verified pool/account proof. That `verified=True` flag is then fed directly into `calculate_bonus_multiplier`, which adds the advertised `pool_account_verified` 1.3x factor even though no URL validation, connection, pool response, or wallet/account ownership check occurred.

This is a correctness/trust bug in the dual-mining proof UI/summary. This report does **not** claim that the displayed bonus is currently used to pay RTC; the demonstrated defect is the false verification state and multiplier calculation itself.

## Exact source path

At the pinned commit, `concierge/pow_miners.py` contains:

```python
def resolve_pool_endpoint(pool_name, pool_url=None):
    if pool_url:
        return {
            "verified": True,
            "pool": pool_name or "custom",
            "endpoint": pool_url,
            "source": "explicit-url",
        }
```

`verify_pool_account()` only checks that `address` is non-empty, calls `resolve_pool_endpoint()`, and then returns:

```python
{
    "verified": True,
    "address": address,
    "pool": resolved["pool"],
    "endpoint": resolved["endpoint"],
    "proof": "pool-config-validated",
}
```

The same module defines:

```python
MULTIPLIER_POOL_VERIFIED = 1.3
```

and `calculate_bonus_multiplier()` multiplies the total by 1.3 whenever `pool_account_verified` is true.

`concierge/cli.py` passes `pool_proof.get("verified", False)` directly into that multiplier in both the `--dry-run` and managed-miner paths.

## Deterministic reproduction

From an exact checkout of the pinned commit:

```bash
python - <<'PY'
from concierge import pow_miners

endpoint = pow_miners.resolve_pool_endpoint("fake", "not-a-url")
proof = pow_miners.verify_pool_account("RTCabc", "fake", "not-a-url")
bonus = pow_miners.calculate_bonus_multiplier(False, False, proof["verified"], False)

print(endpoint)
print(proof)
print(bonus)
PY
```

Current source deterministically evaluates to the equivalent of:

```text
{'verified': True, 'pool': 'fake', 'endpoint': 'not-a-url', 'source': 'explicit-url'}
{'verified': True, 'address': 'RTCabc', 'pool': 'fake', 'endpoint': 'not-a-url', 'proof': 'pool-config-validated'}
{'base': 1.0, 'total_multiplier': 1.3, 'factors': [{'name': 'pool_account_verified', 'multiplier': 1.3}]}
```

No pool is contacted and `not-a-url` is not even a Stratum URL.

## Expected behavior

An arbitrary caller-supplied string should not be described as a verified pool/account proof or earn the `pool_account_verified` factor.

At minimum, explicit endpoints should be syntactically validated and the state should be named as configuration-only. If the 1.3x factor is intended to mean actual pool/account verification, the implementation should perform a real endpoint/account check before setting it.

## Actual behavior / impact

A caller can obtain a false-positive `verified=True`, a `pool-config-validated` proof label, and the 1.3x pool factor using only arbitrary strings. That makes the proof/bonus summary claim stronger evidence than the implementation actually possesses.

## Existing test gap

`tests/test_pow_miners.py` tests one valid explicit URL (`stratum+tcp://example.org:1234`) but has no malformed-URL case. Its multiplier test also assumes a trusted boolean rather than checking how `verify_pool_account()` earns that boolean.

Suggested regression coverage:

1. `resolve_pool_endpoint("fake", "not-a-url")` must not return verified.
2. `verify_pool_account("RTCabc", "fake", "not-a-url")` must not return verified.
3. A malformed/unverified explicit endpoint must not add `pool_account_verified` to the bonus factors.

## Validation notes

The target source, fresh main SHA, exact helper implementation, CLI call path, and tests were read through the GitHub repository API before publication. A local clone attempt in the execution sandbox could not resolve `github.com`, so this report intentionally distinguishes the deterministic pure-function/source reproduction above from an executed checkout test.

## Submission-path receipt

A direct attempt to open this report as an issue in `Scottcjn/bounty-concierge` returned GitHub connector error `403 Resource not accessible by integration`. A direct comment attempt on bounty `#520` returned the same 403.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents a file pull request as an accepted fallback when issue/comment writes are blocked. This PR is intentionally based directly on fresh sponsor `rustchain-bounties` main so the diff is only this report file.