# Bounty #1524 — Track C: Agent-to-agent messaging (50 RTC)

Upstream target: `Scottcjn/Rustchain`

Pinned source base: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

This package is the documented public-repository fallback for the Track C **Agent-to-agent messaging (50 RTC)** lane. Direct branch creation in `Scottcjn/Rustchain` was attempted first through the GitHub connector and returned `403 Resource not accessible by integration`.

## What this implements

The implementation adds an authenticated Atlas mailbox instead of reusing the existing human-to-agent LLM chat endpoint.

- `POST /beacon/api/agent-messages` sends one message from a registered Beacon agent to another.
- `POST /beacon/api/agent-messages/query` returns only the authenticated agent's mailbox, optionally filtered to one peer.
- The routes reuse RustChain's existing `_authenticate_contract_agent` Ed25519 request-signature scheme (`X-Agent-Id`, timestamp, nonce, body hash, signature), including its replay protection.
- A new `beacon_agent_messages` table stores `from_agent`, `to_agent`, content, timestamps, and future read-receipt state.
- `site/beacon/agent-messages.js` is a browser helper that requires an injected `signRequest` callback; Atlas never reads or stores an agent private key.
- `site/beacon/chat.js` gains an `A2A` button only when `globalThis.beaconAgentSession = { agentId, signRequest }` is present. Normal `TX` user-to-agent chat remains unchanged.
- Focused tests cover valid signed delivery, recipient retrieval, mailbox impersonation rejection, missing signatures, and nonce replay.

## Files in this fallback package

- `apply_agent_messages.py` — fail-closed patcher for the exact pinned RustChain source. It checks the upstream HEAD by default, requires every source anchor to match exactly once, refuses to overwrite the two new files, and then applies the scoped changes.
- `agent-messages.js` — exact new Atlas browser helper payload.
- `test_beacon_agent_messages.py` — exact focused upstream test payload.

## Apply

From a clean checkout of the pinned RustChain commit:

```bash
python /path/to/apply_agent_messages.py /path/to/Rustchain
python -m pytest -q tests/test_beacon_agent_messages.py
node --check site/beacon/agent-messages.js
node --check site/beacon/chat.js
```

The patcher refuses a different Git HEAD unless `--skip-head-check` is explicitly supplied. That escape hatch exists only for isolated patcher testing and should not be used for submission.

## Security properties

The sender cannot choose another agent identity and sign as itself: the existing `_authenticate_contract_agent` gate compares `X-Agent-Id` to the allowed `from_agent`, verifies the registered Ed25519 public key, signs the exact method/path/body hash/timestamp/nonce tuple, and reserves the nonce. Mailbox queries are also POSTs with the queried `agent_id` inside the signed body so peer/identity parameters are not mutable unsigned query-string state.

Messages are returned only after authentication as one of their participants. The UI helper deliberately delegates signing to an existing Beacon session rather than accepting or persisting raw private keys.

## Verification performed in this run

Fresh connector reads verified the pinned upstream main, `node/beacon_api.py`, `site/beacon/chat.js`, existing authentication helper usage, and the current Atlas test style before this package was produced. A second collision check immediately before publication found no other #1524 `Agent-to-agent messaging` claim in the bounty thread and only this run's two Slack lane announcements.

Local checks completed in the available execution environment:

- `python -m py_compile apply_agent_messages.py` — PASS.
- fail-closed patcher anchor test against exact captured upstream source anchors — PASS.
- `node --check agent-messages.js` — PASS.
- `python -m py_compile test_beacon_agent_messages.py` — PASS.

A full Flask route test could not be executed in the local tool container because that container does not have Flask installed and has no package-network access. The focused test is included for execution in the RustChain environment/CI, where Flask is an existing project dependency. This limitation is stated rather than presenting an unexecuted test as passing.

## Source evidence

At the pinned base, `site/beacon/chat.js` only posts `{agent_id, message, history}` to `/beacon/api/chat`, which is user-to-selected-agent LLM chat. `node/beacon_api.py` already has the reusable signed-agent request authenticator and nonce table used by contract writes. This patch intentionally composes those existing primitives instead of inventing a weaker token or browser-side key store.

## Submission state

The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents controlled-repository publication as a fallback when the harness integration receives GitHub 403. This public package satisfies that fallback publication step. The remaining sponsor-visible claim requires a user/PAT-authenticated comment or PR-link submission; the automation runtime has no email capability.