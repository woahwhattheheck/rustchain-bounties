# BoTTube bounty #1102 report — `/api/studio/info` non-object JSON body

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/1102

Target repository: https://github.com/Scottcjn/bottube

Target revision reviewed: `00973f5b3d2098ad42404afb0cce3945d1eead85`

Target path: `studio_blueprint.py`

GitHub / RTC handle: `woahwhattheheck`

Requested tier: functional bug, 5 RTC if the maintainer deems the report eligible. No payout is counted until acceptance/payment.

## Summary

`GET /api/studio/info` calls `_resolve_caller()`, which assumes every truthy parsed JSON request body is a mapping when `X-API-Key` is absent. Valid JSON arrays, strings, numbers, or `true` therefore reach `.get("agent_api_key")` and can raise `AttributeError` instead of returning the Studio info response or a bounded client error.

Current source:

```python
def _resolve_caller(conn):
    """Identify the calling agent from an X-API-Key header/body field or the session cookie."""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        api_key = ((request.get_json(silent=True) or {}).get("agent_api_key") or "").strip()
    ...

@studio_bp.route("/api/studio/info", methods=["GET"])
def studio_info():
    """Return tier pricing and the caller's RTC balance (if signed in)."""
    conn = _conn()
    try:
        caller = _resolve_caller(conn)
        ...
```

A non-empty list such as `[1]` is truthy, so `or {}` does not replace it and the subsequent `.get(...)` fails.

## Reproduction

A request with no `X-API-Key` and a truthy non-object JSON body exercises the failing path:

```bash
curl -i -X GET 'https://bottube.ai/api/studio/info' \
  -H 'Content-Type: application/json' \
  --data-binary '[1]'
```

Equivalent Flask-client cases are JSON strings, numbers, booleans, and non-empty arrays.

This report is based on the exact current-main request path and Flask JSON semantics. No production state-changing request was made.

## Expected

Either:

- ignore the GET body and return the ordinary unauthenticated Studio info payload; or
- reject a supplied non-object JSON body with deterministic HTTP 400 JSON.

In either case, malformed request shape should not escape as an internal exception.

## Actual / root cause

`studio_info()` calls `_resolve_caller(conn)` without body-shape validation. `_resolve_caller()` assumes the parsed JSON value has `.get()`, so a truthy non-mapping value raises before `studio_info()` can serialize its normal response.

## Impact

This is a public Studio pricing/balance-discovery endpoint. Clients that attach a malformed JSON body can turn an ordinary read request into a server error rather than receiving a diagnosable 4xx response or the normal public info document.

## Duplicate boundary

Searches of current open/closed BoTTube issues for `/api/studio/info`, `_resolve_caller`, Studio malformed JSON, and non-object Studio request bodies found no matching report.

BoTTube #1923 is distinct: it covered `POST /api/studio/generate`. Current main now explicitly validates that route's body is a dict and validates its string fields. The `GET /api/studio/info` path still reaches the unsafe shared caller resolver without that check.

## Suggested fix

Parse body shape safely inside `_resolve_caller()` or avoid body-based API-key lookup for this GET endpoint. If an embedded `agent_api_key` remains supported, require an object body and string key before calling `.strip()`.

Regression coverage should include:

- ordinary no-body `GET /api/studio/info`;
- a non-object JSON body;
- an object with a string `agent_api_key`;
- an object with a non-string `agent_api_key`.

## Submission transport status

Direct target-repo issue creation through the connected GitHub integration returned `403 Resource not accessible by integration`.

Direct comment submission to `Scottcjn/rustchain-bounties#1102` through the same integration returned the same `403 Resource not accessible by integration`.

The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a repository controlled by the claimant as an accepted fallback when an installation token cannot write to the sponsor repositories, except for bounties where activity on the sponsor repository is itself the deliverable. Bounty #1102 pays for the bug report, so this file is the public, timestamped fallback deliverable.

The remaining external step is to send this public URL to the maintainer using an owner/PAT-authenticated GitHub comment or another documented sponsor submission channel.
