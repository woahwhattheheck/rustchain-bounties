# Bug Hunter #520 — BoTTube Python SDK leaks raw `URLError`

Claimant: `@woahwhattheheck`  
Tracker: `Scottcjn/rustchain-bounties#520` (Bug Hunter, multi-claim)  
Target: `Scottcjn/bottube`  
Pinned target revision: `6af6b63f7a5a87353a30cd4552dc5c0e183a96af`

## Summary

The stdlib Python SDK normalizes HTTP response failures into `BoTTubeError`, but its ordinary `_request()` path does not catch `urllib.error.URLError`. DNS failures, refused connections, and similar transport failures therefore escape as raw stdlib exceptions instead of the SDK exception type callers are otherwise instructed to handle.

This is a functional error-contract bug rather than a feature request: the same public SDK method can throw `BoTTubeError` for an HTTP 4xx/5xx response and a completely unrelated `URLError` for a lower-level request failure.

Pinned source:

- `python-sdk/bottube/client.py` at `Scottcjn/bottube@6af6b63f7a5a87353a30cd4552dc5c0e183a96af`
- `_request()` catches `HTTPError` and raises `BoTTubeError`.
- The module already imports `URLError`, but `_request()` has no `except URLError` branch.
- The streaming upload helper separately catches `URLError`, which makes the ordinary request path inconsistent with another SDK transport path.

## Reproduction against the pinned SDK

From the BoTTube repository root:

```python
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path("python-sdk").resolve()))
from bottube.client import BoTTubeClient, BoTTubeError

client = BoTTubeClient(base_url="https://example.invalid")

try:
    with patch("bottube.client.urlopen", side_effect=URLError("dns failure")):
        client.health_check()
except Exception as exc:
    print(type(exc).__module__ + "." + type(exc).__name__)
    print(repr(exc))
    print("is_BoTTubeError=", isinstance(exc, BoTTubeError))
```

Observed from the pinned `_request()` control flow:

```text
urllib.error.URLError
URLError('dns failure')
is_BoTTubeError= False
```

The finding was independently reproduced in an isolated Python 3.13.5 process by executing the pinned helper's exception structure with a mocked `urlopen`; no live BoTTube request or production traffic was generated.

## Expected behavior

A public SDK request should expose a stable SDK error contract for transport failures. Two reasonable fixes are:

1. Catch `URLError` in `_request()` and convert it to `BoTTubeError` with an appropriate transport/network status convention; or
2. Add a dedicated `BoTTubeTransportError` subclass and document it alongside `BoTTubeError`.

Either approach should have regression coverage for DNS failure / refused connection while preserving current HTTP error parsing.

## Impact

A caller following the SDK README's `except BoTTubeError` pattern can crash or bypass its normal error handling when DNS resolution fails, a connection is refused, or another request-layer failure arrives as `URLError`. HTTP response errors take the SDK path; transport failures do not.

## Environment

- OS: Linux 6.18.44 x86_64, glibc 2.41
- Python: 3.13.5
- Target source: `Scottcjn/bottube@6af6b63f7a5a87353a30cd4552dc5c0e183a96af`
- Reproduction: mocked transport only; no production traffic

## Duplicate check

Before publication, GitHub issue search for BoTTube Python SDK `URLError` / network-error reports returned no matching issue, and Slack coordination/delegation search found no owner for this exact finding.

## Submission note

A direct `create issue` attempt against `Scottcjn/bottube` returned `403 Resource not accessible by integration`. The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a repository controlled by the claimant as a fallback for that connector-specific 403. This file is that public, timestamped fallback artifact.

AI/automation disclosure: this report was prepared and reproduced by the claimant's authorized ChatGPT automation using the pinned public source and mocked local transport behavior.
