# Source map

All factual claims in the script and storyboard are pinned to `Scottcjn/beacon-skill` commit `ca658f39bf018e66096e038bb6208b78814811e5`.

## 1. Beacon supports signed RTC payments

Immutable source:
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/SKILL.md

Relevant public statements:
- Beacon is an agent-to-agent protocol for social coordination, crypto payments, and P2P mesh.
- Its feature list says it can send RustChain RTC payments using signed Ed25519 transfers.
- The documented CLI example is `beacon rustchain pay RTCabc123... 1.5 --memo "bounty: #21"`.

## 2. RTC address derivation and wallet key type

Immutable source:
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/beacon_skill/transports/rustchain.py

Relevant implementation:
- `RustChainKeypair.generate()` creates an Ed25519 keypair.
- `_rtc_address_from_public_key_bytes()` hashes the public key with SHA-256, keeps the first 40 hexadecimal characters, and prefixes them with `RTC`.

## 3. What the signed transfer contains

Same immutable source:
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/beacon_skill/transports/rustchain.py

`RustChainClient.sign_transfer()` constructs a payload containing:
- `from`
- `to`
- `amount`
- `memo`
- `nonce`

It serializes that dictionary with sorted keys and compact separators, signs the resulting bytes with the Ed25519 private key, and returns the signature plus public transfer fields.

## 4. Where the signed payload is sent

Same immutable source:
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/beacon_skill/transports/rustchain.py

`RustChainClient.transfer_signed()` submits the payload with HTTP POST to `/wallet/transfer/signed`.

## 5. Key-custody wording

Immutable source:
https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/SKILL.md

The security section says Beacon uses password-protected keystores by default and does not put plaintext private keys in config. The short therefore says the private key “stays local”; it does not claim that keys can never be exported or that RustChain itself provides custody.

## Editorial boundaries

This kit does **not** claim that a live transfer was executed during production. It describes and visually traces the public, runnable Beacon payment path. The storyboard explicitly tells the publisher not to execute the example unless they choose an authorized disposable/test wallet and amount.
