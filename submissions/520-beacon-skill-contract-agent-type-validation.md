# RustChain bounty #520 — Beacon `/api/contracts` wrong-type agent IDs crash before validation

- **Bounty:** https://github.com/Scottcjn/rustchain-bounties/issues/520
- **Target repository:** https://github.com/Scottcjn/beacon-skill
- **Target main SHA:** `4f0431b03a67917bc0c0bda65d6150e42b10255d`
- **Affected file:** `atlas/beacon_chat.py`
- **Severity:** Low functional/API robustness bug
- **Environment:** Linux container; Python 3.13.5 for deterministic primitive reproduction
- **Status:** proper target issue creation was attempted first and returned GitHub App `403 Resource not accessible by integration`; this public report is the sponsor-documented fallback artifact.

## Summary

`POST /api/contracts` accepts arbitrary JSON types for `from` and `to`, then passes those values directly into `dns_resolve()` before any type validation. `dns_resolve()` calls `.startswith("bcn_")` on every truthy value.

A client can therefore send an integer or object for either agent identifier and trigger `AttributeError` before the route reaches its existing structured validation/authentication block. Falsy unhashable containers such as `[]` survive `dns_resolve()` unchanged and then trigger `TypeError` at `if from_agent not in all_agents`.

Malformed client input should produce a deterministic HTTP 400 validation error, not a server-side exception / HTTP 500 path.

## Source path

At target SHA `4f0431b03a67917bc0c0bda65d6150e42b10255d`, `dns_resolve()` is effectively:

```python
def dns_resolve(name_or_id):
    if not name_or_id:
        return name_or_id, False
    if name_or_id.startswith("bcn_"):
        return name_or_id, False
    ...
```

The contract route then does:

```python
data = request.get_json(silent=True)
...
from_agent = data.get("from", "")
to_agent = data.get("to", "")

from_agent, from_resolved = dns_resolve(from_agent)
to_agent, to_resolved = dns_resolve(to_agent)
...
if from_agent not in all_agents:
    errors.append("Invalid from agent")
if to_agent not in all_agents:
    errors.append("Invalid to agent")
...
if errors:
    return cors_json({"error": "; ".join(errors)}, 400)
```

The intended 400-level validation runs only **after** the unsafe DNS resolution.

The same module already contains a safe payload helper:

```python
def _payload_str(data, key, default=""):
    value = data.get(key, default)
    return value.strip() if isinstance(value, str) else ""
```

but `create_contract()` does not use it for `from` or `to`.

## Reproduction

From a checkout of the pinned target SHA, this Flask regression test exercises the public route:

```python
from atlas import beacon_chat

beacon_chat.app.config["TESTING"] = False
client = beacon_chat.app.test_client()

r = client.post("/api/contracts", json={
    "from": 123,
    "to": "bcn_contract_to",
    "type": "rent",
    "amount": 1,
    "term": "7d",
})
print(r.status_code)
```

The request reaches `dns_resolve(123)`, which attempts `123.startswith("bcn_")` and raises:

```text
AttributeError: 'int' object has no attribute 'startswith'
```

I separately executed the exact current helper primitive under Python 3.13.5 with representative JSON-compatible wrong types:

```text
int AttributeError 'int' object has no attribute 'startswith'
dict AttributeError 'dict' object has no attribute 'startswith'
```

An empty list takes a second exception path: it is falsy, so `dns_resolve([])` returns it unchanged; `from_agent not in all_agents` then attempts to hash the list and raises `TypeError: unhashable type: 'list'`.

## Expected behavior

Non-string `from` / `to` values should be rejected as client input, ideally with HTTP 400 and either the existing `Invalid from agent` / `Invalid to agent` response or an explicit `from/to must be strings` message.

No malformed JSON field type should escape as an unhandled Python exception.

## Actual behavior

Truthy non-string values can fail in `dns_resolve()` before validation and authentication. Falsy unhashable containers can fail in the following set-membership validation.

## Regression gap

`tests/test_contract_auth_security.py` covers:

- missing initiator relay token,
- wrong-party relay token,
- valid initiator relay token,
- PATCH authorization.

Its `_contract_payload()` uses valid string identifiers throughout. It has no wrong-type `from` / `to` coverage, so this input-validation failure is not currently fenced.

## Suggested fix

Normalize or reject the fields before DNS resolution. For example, reuse the module's existing `_payload_str()` helper:

```python
from_agent = _payload_str(data, "from")
to_agent = _payload_str(data, "to")
```

or perform explicit `isinstance(value, str)` checks and return HTTP 400.

Add regression cases for integer, object, and list values in both `from` and `to`, and assert HTTP 400 with zero contract insertion.

## Duplicate check

Before publication I searched current open and closed `Scottcjn/beacon-skill` issues, pull requests, Slack coordination/delegation history, and the existing `woahwhattheheck/rustchain-bounties` submission archive for `dns_resolve`, `/api/contracts` type validation, and this wrong-type crash. No matching report or active owner was found.

## Submission transport note

Bounty #520 requires a proper target issue. I attempted to create that issue through the available GitHub connector first; GitHub returned `403 Resource not accessible by integration`. The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publishing a deliverable in a repository you control and opening a file PR as fallback paths for this connector-specific 403. This file is that public, timestamped artifact; a user-token-authenticated target issue remains the final visibility step if the integration cannot write the sponsor repo.
