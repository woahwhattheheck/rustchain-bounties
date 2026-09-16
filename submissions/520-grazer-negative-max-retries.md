# Bug Hunter #520 — `grazer-skill` negative retry count crashes before any request

## Summary

`Scottcjn/grazer-skill` `GrazerClient._request_with_backoff()` raises `UnboundLocalError` when `GRAZER_MAX_RETRIES` or the public `max_retries` constructor argument is negative. The retry loop becomes empty, no HTTP request is made, and the function falls through to `return resp` even though `resp` was never assigned.

This report is pinned to `Scottcjn/grazer-skill` `main` commit `1167938eb96c57eb8718c09b13b720fdd645fb1f` (2026-09-16).

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/520
Target repository: https://github.com/Scottcjn/grazer-skill
Target source: `grazer/__init__.py`
Target regression tests: `tests/test_rate_limit_backoff.py`

## Environment

Reproduction/control-flow validation environment:

- Linux 6.18.44 x86_64, glibc 2.41
- Python 3.13.5
- Source inspected through the GitHub connector at exact commit `1167938eb96c57eb8718c09b13b720fdd645fb1f`

The execution sandbox had no DNS route to GitHub, so I did not claim a package-install or full-checkout run. The reproducer below executes the exact affected control flow with the session and rate limiter replaced by counters; this bug occurs before either dependency can be called.

## Reproduction

The public constructor accepts a retry count with no lower-bound validation:

```python
client = GrazerClient(max_retries=-1)
```

`_request_with_backoff()` then reads the environment override and executes:

```python
max_retries = int(os.environ.get("GRAZER_MAX_RETRIES", str(self.max_retries)))
base_ms = int(os.environ.get("GRAZER_BACKOFF_BASE_MS", str(self.backoff_base_ms)))

for attempt in range(max_retries + 1):
    self._rate_limiter.acquire()
    resp = self.session.request(method, url, **kwargs)
    # ... 429 handling ...
    return resp

return resp
```

For `max_retries=-1`, `range(max_retries + 1)` is `range(0)`. The loop body never executes, so the final `return resp` references an unbound local.

Minimal user-facing trigger:

```python
from grazer import GrazerClient

client = GrazerClient(max_retries=-1)
client._rate_limited_get("https://example.com")
```

Equivalent environment path:

```bash
GRAZER_MAX_RETRIES=-1 python -c 'from grazer import GrazerClient; GrazerClient()._rate_limited_get("https://example.com")'
```

## Observed result

Exact control-flow probe of the pinned implementation:

```text
max_retries=0  -> request issued normally (1 request, 1 rate-limiter acquire)
max_retries=1  -> request issued normally (1 request, 1 rate-limiter acquire)
max_retries=-1 -> UnboundLocalError: cannot access local variable 'resp' where it is not associated with a value (0 requests, 0 acquires)
max_retries=-2 -> UnboundLocalError: cannot access local variable 'resp' where it is not associated with a value (0 requests, 0 acquires)
```

The negative cases therefore fail before any network behavior can affect the result.

## Expected behavior

A negative retry count should have an explicit contract. Two reasonable fixes are:

1. reject negative values at constructor/environment parsing time with a clear `ValueError`, or
2. clamp negative values to zero retries while still allowing the initial request.

The same rule should apply to both `max_retries=` and `GRAZER_MAX_RETRIES`.

## Existing test gap

At the pinned commit, `tests/test_rate_limit_backoff.py` covers:

- exponential backoff calculation,
- integer `Retry-After`,
- successful retry after 429,
- retry-budget exhaustion,
- positive environment configuration (`GRAZER_MAX_RETRIES=1`).

It does not cover zero/negative retry-count bounds. A regression test should include at least `-1` through both the constructor and environment-variable paths.

## Duplicate check

Fresh GitHub issue and PR searches in `Scottcjn/grazer-skill` for `GRAZER_MAX_RETRIES`, `max_retries`, and `UnboundLocalError` found only the original 429-backoff feature work (`#344`, merged implementation `#347`, and competing PR `#351`). No existing issue or PR reports the negative-configuration crash. Fresh Slack search also found no owner for this exact finding before the lane was claimed.

## Submission-path receipt

The proper target issue creation attempt returned:

```text
403 Resource not accessible by integration
```

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents this GitHub-App failure and permits publishing a report in a repository the contributor controls, followed by a file PR attempt or other accepted route. This file is that public, timestamped fallback artifact.
