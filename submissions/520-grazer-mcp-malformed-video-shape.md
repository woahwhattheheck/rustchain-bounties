# Bug Hunter report — grazer-mcp crashes on malformed successful `videos` payloads

**Bounty:** Scottcjn/rustchain-bounties#520 — Bug Hunter, 3 RTC  
**Target:** `Scottcjn/grazer-mcp`  
**Pinned target commit:** `663b4ae6ee7205313bb3307de122688a7da7f2e7`  
**Affected paths:** `grazer_mcp/client.py`, surfaced through `grazer_mcp/server.py`  
**Status:** report published after direct target-issue creation returned `403 Resource not accessible by integration`; no maintainer acceptance or payout is asserted.

## Summary

`GrazerClient.trending()`, `discover()`, and `feed()` can raise an uncaught `AttributeError` when an upstream HTTP 200 response is syntactically valid JSON but its `videos` member is not a `list[dict]`.

That contradicts the contract stated in both the client and MCP server: backend-facing methods/tools are documented to return either a successful dictionary or a predictable structured error dictionary. The existing error-contract tests cover HTTP failures, timeouts, and non-JSON bodies, but not valid JSON with the wrong successful-response shape.

## Source path

At the pinned commit, `grazer_mcp/client.py` contains:

```python
@staticmethod
def _videos(data: Any) -> list:
    if isinstance(data, dict):
        return data.get("videos", []) or []
    return data if isinstance(data, list) else []
```

Each backend method later does the equivalent of:

```python
items = [self._normalize(v) for v in self._videos(res["data"])]
```

and `_normalize()` immediately calls methods such as `v.get("video_id")`.

So `_videos()` checks the outer payload but neither validates the type of the `videos` member nor validates the type of each element. A string, mapping, `None`, integer, or other non-video object therefore reaches `_normalize()` and raises rather than becoming the documented error envelope.

`grazer_mcp/server.py` simply returns `_client.trending(...)`, `_client.discover(...)`, and `_client.feed(...)`; there is no wrapper exception conversion there, so this escapes the MCP tool surface too.

## Environment

- Linux `6.18.44` x86_64, glibc 2.41
- Python 3.13.5
- httpx 0.28.1
- Source inspected through the GitHub connector at commit `663b4ae6ee7205313bb3307de122688a7da7f2e7`

The execution container has no DNS access to GitHub, so the reproduction below was executed against the exact normalization logic read from that pinned source rather than by cloning over the network.

## Deterministic reproduction

The failure is independent of the live network and is the same shape exercised by the repository's existing `httpx.MockTransport` tests. A direct probe of the pinned `_videos()` + `_normalize()` logic produced:

```text
payload= {'videos': 'oops'} -> AttributeError: 'str' object has no attribute 'get'
payload= {'videos': {'video_id': 'v1'}} -> AttributeError: 'str' object has no attribute 'get'
payload= {'videos': [None]} -> AttributeError: 'NoneType' object has no attribute 'get'
payload= {'videos': [123]} -> AttributeError: 'int' object has no attribute 'get'
```

Equivalent repository-level regression case:

```python
import httpx
from grazer_mcp.client import GrazerClient


def handler(req):
    return httpx.Response(200, json={"videos": [None]})

client = GrazerClient(
    base_url="https://test.local",
    transport=httpx.MockTransport(handler),
)

# Actual: raises AttributeError instead of returning {"ok": False, "error": ...}
print(client.trending())
```

The same normalization path is used by `discover()` and `feed()`.

## Expected behavior

A syntactically valid but structurally invalid successful upstream response should be converted into a documented structured failure, for example:

```json
{
  "ok": false,
  "error": {
    "code": "UPSTREAM_BAD_SHAPE",
    "message": "...",
    "retryable": false,
    "source": "grazer",
    "details": {}
  }
}
```

The exact code name is not important; preserving the advertised non-throwing tool contract is.

## Actual behavior

The HTTP 200 JSON body is accepted by `_get()`, then the normalization list-comprehension raises `AttributeError`. This bypasses the error-envelope contract and can abort an MCP tool invocation.

## Impact

Any upstream schema regression, proxy-generated valid JSON object, partial backend rollout, or malformed `videos` member can turn a recoverable upstream-shape problem into an uncaught client exception. Downstream agents that rely on the advertised error dictionary cannot inspect `retryable`, `code`, or details because no dictionary is returned.

## Existing-test gap

`tests/test_error_contract.py` explicitly validates the error contract for:

- HTTP 500
- HTTP 404
- timeout
- HTTP 200 with a non-JSON body

Its success handler always returns `{"videos": [VIDEO]}` and therefore does not exercise valid-JSON/wrong-shape payloads.

## Suggested fix

Validate both levels before normalization:

1. if a mapping response has `videos`, require it to be a list;
2. require every list element to be a mapping/dict;
3. on violation, return a structured non-retryable upstream-shape error;
4. add `MockTransport` regression cases for `{"videos": "oops"}` and `{"videos": [None]}` across the backend-backed tools.

## Duplicate check

Before publication, GitHub issue/PR searches for `Scottcjn/grazer-mcp` using terms including `malformed`, `videos`, `AttributeError`, `UPSTREAM_BAD_JSON`, and normalization surfaced only the unrelated open issue #18 about `ranked=False` returning ranked content. A Slack search for `grazer-mcp` + `videos` + `malformed` returned no existing lane.

## Submission-routing receipt

A direct `create_issue` call to `Scottcjn/grazer-mcp` with the complete report returned:

```text
403 Resource not accessible by integration
```

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents this GitHub-App limitation and lists publication of the deliverable in a repository the contributor controls as an accepted fallback for reports/documents, followed by linking it for maintainer review. This file is that public, timestamped fallback artifact.
