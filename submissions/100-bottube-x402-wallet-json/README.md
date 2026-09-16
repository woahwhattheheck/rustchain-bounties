# Bounty #100 — BoTTube x402 wallet JSON validation

Target: `Scottcjn/bottube`

Pinned upstream base: `6af6b63f7a5a87353a30cd4552dc5c0e183a96af`

Published source carrier: [woahwhattheheck/bottube#17](https://github.com/woahwhattheheck/bottube/pull/17)

Exact source head: `1e684920bf36f8fdfdded84f2ebf10028ca15269`

Advertised bounty lane: [Scottcjn/rustchain-bounties#100](https://github.com/Scottcjn/rustchain-bounties/issues/100), accepted-improvement tier `10 RTC`.

## Defect and repair

At the pinned upstream base, `POST /api/agents/me/coinbase-wallet` treated every truthy JSON value as a mapping and immediately called `.get()`. A JSON string or list therefore raised instead of returning a bounded client error. A mapping whose `coinbase_address` was a list reached later string operations and raised for the same reason.

The two-commit patch:

1. distinguishes absent/JSON-null input from a non-object JSON body;
2. rejects non-object JSON with HTTP `400` and `{"error":"JSON object required"}`;
3. rejects a non-string `coinbase_address` with HTTP `400`;
4. adds focused Flask-client regressions for a JSON string, JSON list, and list-valued wallet address.

Changed paths are exactly:

- `bottube_x402.py`
- `tests/test_bottube_x402_init_app_registration.py`

The public source PR reports `+29/-1`, two commits, and zero commits behind the pinned upstream base at publication time.

## Byte-frozen evidence

- Patch: `bottube-x402-wallet-json.patch`
- Patch SHA-256: `5876bb4019c8585b2588e93736e9dfa7393da4a15024e89e28bb6cd2c63514fb`
- Receipt: `receipt.json`
- Verifier: `verify.py`
- Hostile verifier tests: `test_verify.py`

Run:

```bash
python verify.py
python -m unittest -v test_verify.py
python -O -m unittest -v test_verify.py
```

`verify.py` rejects:

- any patch-byte change;
- any changed-path expansion;
- the wrong upstream base, source PR, or exact head;
- duplicate JSON keys or non-finite JSON;
- altered diff statistics or advertised tier;
- any packet that mints sponsor acceptance, award, or payment authority.

## Evidence boundary

This directory is a checkable carrier for the already-published source patch. It is **not** a substitute for applying and running the patch in a fresh full BoTTube checkout, and it does not prove upstream acceptance.

The source runtime could not claim checkout-based pytest because its shell could not resolve `github.com`; source reads and publication used the GitHub connector. This carrier therefore preserves the exact patch and its focused regression source, while making that execution boundary explicit.

The original paid-result seat retains patch/source authorship and the already Muse-elected external-writer role. `ZTL-P8V4` owns only this evidence conversion. This carrier sent no sponsor email/comment and performed no provider mutation.

No RTC award or payment is claimed. Only `@Scottcjn` or project automation with the repository's documented payout evidence can authorize disbursement.
