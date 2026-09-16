# #520 Bug Hunter — `bounty-concierge` payout status crashes on scalar JSON

Bounty: `Scottcjn/rustchain-bounties#520` — Bug Hunter, 3 RTC  
Target: `Scottcjn/bounty-concierge`  
Source pin: `a73d838163d6da67d568ba356f2bdd3bc1a5b22b`  
Affected file: `concierge/payout_tracker.py`  
Related tests: `tests/test_payout_tracker.py`  
Finding class: reproducible robustness/reliability bug  
Payout identity: `woahwhattheheck`

## Summary

`concierge status` can crash with an uncaught `AttributeError` when the RustChain node returns HTTP 200 with syntactically valid JSON that is neither a list nor an object for `/wallet/pending` or `/wallet/history`.

Both payout helpers accept a list directly, but otherwise assume the decoded JSON object implements `.get(...)`:

```python
data = resp.json()
return data if isinstance(data, list) else data.get("pending", [])
```

The history helper has the same shape with `"history"`. Valid JSON scalar values such as `null`, a string, number, or boolean do not implement `.get`, so they escape the existing `except requests.RequestException` and abort the command.

The CLI's `_cmd_status()` calls `check_pending(wallet)` and `check_history(wallet)` directly before formatting JSON or text output, so the uncaught helper exception terminates the public `concierge status` path.

## Pinned source

Fresh main at review time:

```text
Scottcjn/bounty-concierge@a73d838163d6da67d568ba356f2bdd3bc1a5b22b
```

`concierge/payout_tracker.py` SHA:

```text
fa46cc0d6b0fa08d4842e72148d4c0264fc0e697
```

`tests/test_payout_tracker.py` SHA:

```text
c4d78a493674c9713d310192f9a241db4d9962d8
```

## Reproduction

Environment used for the deterministic control-flow reproduction:

```text
Linux 6.18.44 x86_64
Python 3.13.5
```

The HTTP request can be mocked because the bug occurs after a successful status check and JSON decode:

```python
from unittest.mock import patch
from concierge import payout_tracker


class Resp:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return None  # valid JSON body: null


with patch("concierge.payout_tracker.requests.get", return_value=Resp()):
    payout_tracker.check_pending("alice", node_url="https://node")
```

Observed:

```text
AttributeError: 'NoneType' object has no attribute 'get'
```

I repeated the exact current helper logic for both endpoints and four valid scalar JSON classes:

```text
check_pending  null   -> AttributeError: 'NoneType' object has no attribute 'get'
check_history  null   -> AttributeError: 'NoneType' object has no attribute 'get'
check_pending  "ok"   -> AttributeError: 'str' object has no attribute 'get'
check_history  "ok"   -> AttributeError: 'str' object has no attribute 'get'
check_pending  7      -> AttributeError: 'int' object has no attribute 'get'
check_history  7      -> AttributeError: 'int' object has no attribute 'get'
check_pending  true   -> AttributeError: 'bool' object has no attribute 'get'
check_history  true   -> AttributeError: 'bool' object has no attribute 'get'
```

## Expected behavior

An unexpected but valid JSON response shape should not crash the payout-status command. The helper should validate the decoded type and either return an empty result or surface a controlled response-shape error.

## Actual behavior

Every successful non-list JSON body is treated as mapping-like. Scalars raise `AttributeError`, which is not a `requests.RequestException` and therefore is not caught by either helper.

## Existing coverage gap

The current `tests/test_payout_tracker.py` covers:

- list payloads;
- wrapped dict payloads;
- a dict missing the expected history key;
- 404 responses;
- connection failures; and
- HTTP errors.

It does not cover a successful scalar JSON body for either helper. In fact, its `_response()` helper defaults `payload=None` to `[]`, so a `null` response cannot currently be represented by that test helper without changing it.

## Impact

This is a reliability/robustness issue, not a demonstrated fund-movement primitive. A node, reverse proxy, compatibility shim, or malformed upstream response can turn a status check into an uncaught exception even though the HTTP response is successful and the body is valid JSON. Shell jobs or monitoring that call `concierge status` therefore lose the intended graceful fallback behavior.

## Suggested fix

Validate the decoded payload before key access, e.g.:

```python
if isinstance(data, list):
    return data
if isinstance(data, dict):
    return data.get("pending", [])
return []
```

and mirror that for history. Add regression cases for `None`, string, number, and boolean payloads to both helpers.

## Duplicate / ownership checks

Before taking this lane:

- fresh Slack searches for `bounty-concierge`, `payout_tracker`, and `check_pending` on 2026-09-16 returned no owner/claim;
- fresh GitHub issue search in `Scottcjn/bounty-concierge` found no matching scalar-JSON payout-status report;
- fresh GitHub PR search found payout-tracker test PRs, but no fix/report for scalar successful JSON bodies;
- the exact lane was announced in both Commons coordination and delegations before this artifact was created.

## Submission status

A proper issue creation attempt in `Scottcjn/bounty-concierge` returned:

```text
403 Resource not accessible by integration
```

A `/claim` comment attempt on `Scottcjn/rustchain-bounties#520` returned the same connector-specific 403.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents this GitHub-App failure and lists publication of a deliverable in a repository the contributor controls, followed by linking it, as an accepted fallback. It also lists opening a pull request for file deliverables and email as later fallback routes.

This file is the public, timestamped fallback artifact. Sponsor acceptance and RTC payout are **not** asserted here.
