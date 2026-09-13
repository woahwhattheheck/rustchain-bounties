# Bounty #1102 submission — BoTTube `/api/studio/info` non-object JSON body

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/1102

Target: https://github.com/Scottcjn/bottube

Target revision reviewed: `00973f5b3d2098ad42404afb0cce3945d1eead85`

Target path: `studio_blueprint.py`

Claimant / RTC handle: `woahwhattheheck`

Requested tier: functional bug, 5 RTC if accepted. No payout is counted until maintainer acceptance/payment.

## Summary

`GET /api/studio/info` calls `_resolve_caller()`, which assumes every truthy parsed JSON request body is a mapping when `X-API-Key` is absent. Valid JSON arrays, strings, numbers, or `true` therefore reach `.get("agent_api_key")` and can raise `AttributeError` instead of returning the Studio info response or a bounded client error.

Current source:

```python
def _resolve_caller(conn):
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        api_key = ((request.get_json(silent=True) or {}).get("agent_api_key") or "").strip()
    ...

@studio_bp.route("/api/studio/info", methods=["GET"])
def studio_info():
    conn = _conn()
    try:
        caller = _resolve_caller(conn)
        ...
```

A non-empty list such as `[1]` is truthy, so `or {}` does not replace it and the subsequent `.get(...)` fails.

## Reproduction

```bash
curl -i -X GET 'https://bottube.ai/api/studio/info' \
  -H 'Content-Type: application/json' \
  --data-binary '[1]'
```

Equivalent Flask-client cases are JSON strings, numbers, booleans, and non-empty arrays. This report is based on the exact current-main request path and Flask JSON semantics; no production state-changing request was made.

## Expected

Either ignore the GET body and return the normal unauthenticated Studio pricing/info payload, or reject a supplied non-object JSON body with deterministic HTTP 400 JSON. A malformed body shape should not escape as an internal exception.

## Actual / root cause

`studio_info()` calls `_resolve_caller(conn)` without body-shape validation. `_resolve_caller()` assumes the parsed JSON value has `.get()`, so a truthy non-mapping value raises before the normal response is serialized.

## Impact

This is a public Studio pricing/balance-discovery endpoint. Clients that attach a malformed JSON body can turn an ordinary read request into a server error rather than receiving a diagnosable 4xx response or the normal public info document.

## Duplicate boundary

Searches of current open/closed BoTTube issues for `/api/studio/info`, `_resolve_caller`, Studio malformed JSON, and non-object Studio request bodies found no matching report.

BoTTube #1923 is distinct: it covered `POST /api/studio/generate`, which current main now validates as an object with typed fields. This GET path still reaches the unsafe shared caller resolver without that check.

## Suggested fix / regression

Parse/validate the request body safely inside `_resolve_caller()` or avoid body-based API-key lookup for this GET. If embedded `agent_api_key` remains supported, require an object and string key before `.strip()`.

Cover: no-body GET, non-object JSON, valid object/string key, and non-string key.

## Transport note

Direct issue creation in `Scottcjn/bottube` and direct comment submission on bounty #1102 both returned GitHub `403 Resource not accessible by integration` from the connected GitHub App. The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly lists a pull request as a fallback when comments are blocked, so this single-file branch is the same complete report prepared for that documented route.
