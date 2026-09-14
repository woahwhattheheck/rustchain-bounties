# SOURCES

All technical claims are pinned to:

`Scottcjn/beacon-skill@ca658f39bf018e66096e038bb6208b78814811e5`

## [S1] Minimum interoperable envelope contract
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/docs/MINIMUM_ENVELOPE.md

Supports:
- required/recommended v2 fields;
- full payload except `sig` is signed;
- canonical JSON rules;
- key→`agent_id` verification;
- result codes including `signature_invalid`, `signature_unverifiable`, `replay_nonce`, `stale_ts`, `future_ts`;
- current default age/future-skew/cache values as documented;
- cross-language replay/tamper/unknown-key test checklist;
- v1 is retained for backward compatibility but lacks signed identity.

## [S2] Reference codec
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/beacon_skill/codec.py

Supports:
- `_canonical_json()` uses sorted keys + compact separators + UTF-8;
- nonce generator emits 12 hex characters;
- v2 encoder signs the payload without `sig`;
- verifier obtains embedded/cached key, derives expected agent ID, reconstructs canonical payload, and performs Ed25519 verification;
- invalid signature/identity returns false; absent usable key returns unverifiable (`None` at codec layer).

## [S3] Replay/freshness guard
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/beacon_skill/guard.py

Supports:
- `DEFAULT_MAX_AGE_S = 900`;
- `DEFAULT_MAX_FUTURE_SKEW_S = 120`;
- `DEFAULT_MAX_NONCES = 50000`;
- missing nonce/timestamp, stale/future timestamp, and reused nonce rejection;
- accepted nonce is persisted into the replay cache after checks.

## [S4] Repository quick start and loopback path
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/README.md

Supports:
- `beacon identity new`;
- local webhook receiver on port 8402;
- documented signed-envelope send command;
- inbox inspection;
- `scripts/webhook_loopback_smoke.sh` as the repository-provided local smoke path.

## Accuracy boundary

This kit deliberately does **not** claim that envelope verification alone grants authorization for payments, tool execution, procurement, or any other side effect. Those are application-policy decisions outside the minimum signed-envelope contract.
