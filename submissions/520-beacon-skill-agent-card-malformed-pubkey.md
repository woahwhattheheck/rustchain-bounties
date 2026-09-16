# Bounty #520 Bug Hunter — Beacon agent-card verifier crashes on malformed public keys

## Target

- Bounty: `Scottcjn/rustchain-bounties#520` — Bug Hunter, 3 RTC per confirmed reproducible bug
- Repository: `Scottcjn/beacon-skill`
- Source pin: `4f0431b03a67917bc0c0bda65d6150e42b10255d`
- File: `beacon_skill/agent_card.py`
- Function: `verify_agent_card()`

## Summary

`verify_agent_card()` is documented as the boolean verifier for internet-facing `/.well-known/beacon.json` agent cards. It correctly returns `False` when required signature/key fields are missing and delegates signature parsing to `AgentIdentity.verify()`, which catches malformed cryptographic input. But before that protected verification step, it executes:

```python
expected_id = agent_id_from_pubkey(bytes.fromhex(pubkey_hex))
```

A truthy malformed `public_key_hex` therefore raises from `bytes.fromhex()` instead of producing the verifier's normal `False` result.

This disagrees with `docs/AGENT_CARD.md`, whose discovery-client reject checklist says clients should reject/quarantine a card when `public_key_hex` is invalid hex or not an Ed25519 public key and then states: “These checks are implemented by `beacon_skill.agent_card.verify_agent_card` and exposed through `beacon agent-card verify`.”

## Reproduction

Environment used for the deterministic probe:

```text
Linux-6.18.44-x86_64-with-glibc2.41
Python 3.13.5
cryptography 46.0.4
```

The relevant source logic was exercised unchanged against three malformed values:

```python
for value in ["not-hex", "abc", 123]:
    card = {
        "beacon_version": "1.0.0",
        "agent_id": "bcn_deadbeefdead",
        "public_key_hex": value,
        "signature": "00",
    }
    try:
        print(repr(value), verify_agent_card(card))
    except Exception as exc:
        print(repr(value), type(exc).__name__, str(exc))
```

Observed:

```text
'not-hex' ValueError non-hexadecimal number found in fromhex() arg at position 0
'abc' ValueError non-hexadecimal number found in fromhex() arg at position 3
123 TypeError fromhex() argument must be str, not int
```

Expected: each malformed card is rejected with `False` rather than raising.

## Why this is a real behavior gap

The source explicitly describes agent cards as `/.well-known/beacon.json` discovery data. The verifier docstring says it “Returns True if the signature is valid and agent_id matches pubkey,” and the project documentation says invalid-hex/non-key cards are rejected by this verifier. An untrusted remote document can therefore turn ordinary invalid-card handling into an exception path for callers that rely on the boolean API.

The current `tests/test_agent_card.py` covers:

1. a generated valid card;
2. a valid card with a tampered name, which returns `False`; and
3. JSON round-trip of a valid card.

It has no malformed-key test, so this boundary is presently uncovered.

## Suggested repair

Keep all public-key parsing inside the verifier's failure boundary. For example, validate that `public_key_hex` is a string containing exactly 64 hex characters before deriving the ID, or wrap decode + ID derivation in `try/except (TypeError, ValueError)` and return `False`. Preserve `AgentIdentity.verify()` as the final Ed25519 length/signature check.

Suggested regression cases:

- non-hex string (`"not-hex"`);
- odd-length hex (`"abc"`);
- truthy non-string (`123`);
- valid hex with the wrong Ed25519 key length.

All should return `False` without escaping an exception.

## Duplicate / ownership check

Before publication I searched `Scottcjn/beacon-skill` issues for `agent card public_key_hex malformed verify_agent_card ValueError` and `public_key_hex ValueError`; both returned no matches. I also searched the shared coordination/delegation Slack corpus for `verify_agent_card` and found no existing lane or report for this defect.

## Submission-path receipt

A proper issue creation attempt in `Scottcjn/beacon-skill` was made first and returned GitHub `403 Resource not accessible by integration`. The current sponsor guide at `Scottcjn/rustchain-bounties@bdade1a48a0f6b345a0a4a93c7cfa62076d89337` explicitly documents controlled-repository publication as an accepted fallback for this connector-specific 403. This file is that public, timestamped fallback artifact. No payout or sponsor acceptance is asserted here.
