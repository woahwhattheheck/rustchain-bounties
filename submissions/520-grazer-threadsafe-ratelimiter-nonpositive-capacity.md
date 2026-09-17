# Bounty #520 bug report: Grazer `ThreadSafeRateLimiter` crashes for non-positive capacity

## Target

- Bounty: `Scottcjn/rustchain-bounties#520` — Bug Hunter, 3 RTC, multi-claim
- Repository: `Scottcjn/grazer-skill`
- Pinned main commit: `1167938eb96c57eb8718c09b13b720fdd645fb1f`
- File: `grazer/__init__.py`
- Pinned blob: `5c620a8ec21755a21772cf35f72f86d4af2e2661`
- Class: `ThreadSafeRateLimiter`

## Finding

`ThreadSafeRateLimiter.acquire()` crashes with `IndexError: list index out of range` when the limiter is constructed with `max_requests=0` or any negative value. The constructor accepts the value without validation, then `acquire()` immediately enters its capacity loop while the timestamp list is still empty and dereferences element zero.

Relevant source at the pinned commit:

```python
class ThreadSafeRateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._condition = threading.Condition()
        self._requests: List[float] = []

    def acquire(self) -> None:
        with self._condition:
            now = _time.time()
            self._prune(now)

            while len(self._requests) >= self.max_requests:
                oldest = self._requests[0]
                wait_until = oldest + self.window_seconds
                wait_time = wait_until - _time.time()
                if wait_time > 0:
                    self._condition.wait(timeout=wait_time)
                now = _time.time()
                self._prune(now)

            self._requests.append(_time.time())
            self._condition.notify_all()
```

For an empty limiter and `max_requests=0`, the condition `len([]) >= 0` is true, but `_requests[0]` is invalid. A negative capacity has the same failure mode.

## Deterministic reproduction

Environment used for the focused reproduction:

- Linux x86_64
- Python 3.13.5

Minimal reproducer:

```python
from grazer import ThreadSafeRateLimiter

ThreadSafeRateLimiter(max_requests=0, window_seconds=1).acquire()
```

Observed result:

```text
IndexError: list index out of range
```

The same exception is produced with `max_requests=-1`.

A dependency-free reproduction of the exact class logic at the pinned source produced:

```text
max_requests=0 -> IndexError: list index out of range
max_requests=-1 -> IndexError: list index out of range
```

## Impact

A caller can legitimately derive a request budget from configuration, environment, feature flags, or a computed quota. If that value reaches zero or below, the first `acquire()` does not fail at configuration time with an actionable message or intentionally block; instead it raises an implementation-level `IndexError`. Any Grazer path using such a configured limiter can therefore fail immediately and unexpectedly.

This is especially confusing because `max_requests` is public constructor input and is annotated only as an integer; no positive-range precondition is enforced by the implementation.

## Expected behavior

Reject an invalid non-positive request capacity when constructing the limiter, with a clear exception such as `ValueError`, or explicitly define and implement a deliberate zero-capacity semantic. The current empty-list dereference should not be reachable.

## Suggested fix

Validate the constructor input before storing it, for example:

```python
if isinstance(max_requests, bool) or not isinstance(max_requests, int) or max_requests < 1:
    raise ValueError("max_requests must be an integer >= 1")
```

Then add regression tests for at least `0` and `-1` so the failure is rejected at construction instead of surfacing later inside `acquire()`.

## Duplicate checks

- GitHub issue search in `Scottcjn/grazer-skill` for `ThreadSafeRateLimiter max_requests` found only issue #45, a general question about rate-limiting strategy, not this crash.
- Slack search for `ThreadSafeRateLimiter` found no existing fleet claim or owner for this exact finding before the lane was announced.

## Submission status

A direct issue creation attempt in `Scottcjn/grazer-skill` was made first with the full reproduction and failed with GitHub's connector error:

```text
403 Resource not accessible by integration
```

The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents, for this exact integration limitation, publishing the deliverable in a repository the contributor controls and trying a file pull request as fallback routes. This file is the public, timestamped fallback artifact. No sponsor acceptance or payout is asserted by publication here.
