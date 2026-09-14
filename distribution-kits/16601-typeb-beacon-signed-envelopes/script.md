# Signed, Not Trusted: How Beacon Verifies Agent-to-Agent Task Envelopes

**Target runtime:** ~4:20 at 135–145 words/minute  
**Format:** narrated technical explainer with terminal + code captures  
**Source pin:** `Scottcjn/beacon-skill@ca658f39bf018e66096e038bb6208b78814811e5`

## 00:00–00:24 — Hook

Two software agents can exchange a JSON message in a millisecond. The hard part is not moving the bytes. It is answering four questions: who signed this message, did any field change after signing, is the message still fresh, and have I already accepted this exact message once? Beacon version 2 answers those questions with a signed envelope built around Ed25519 identity, a timestamp, and a single-use nonce. [S1][S2]

## 00:24–01:08 — What is actually inside the envelope?

A minimally interoperable Beacon v2 envelope carries a protocol version, message kind, `agent_id`, Unix timestamp, nonce, signature, and normally the sender's public key. Application fields can ride beside them. Beacon does not sign only a little header: it signs the full envelope payload except the `sig` field, so changing an application field after signing invalidates verification. [S1]

The Python codec canonicalizes that payload by sorting JSON keys, using compact separators, encoding UTF-8, and then signing those bytes with Ed25519. When a receiver verifies the message, it reconstructs those same canonical bytes. [S2]

## 01:08–01:52 — Identity is bound to the public key

A signature by itself is not enough if the sender can claim somebody else's name. Beacon derives the claimed `bcn_...` agent identifier from the Ed25519 public key and checks that the result matches the `agent_id` carried in the envelope. The verifier then checks the Ed25519 signature over the canonical payload. A mismatch in either identity binding or signature returns a failed verification instead of silently accepting the message. [S1][S2]

If the envelope has no embedded public key, the receiver can use a trusted key already cached for that `agent_id`. If it has neither, Beacon does not treat the sender as valid just because an ID string is present; the envelope is unverifiable. [S1][S2]

## 01:52–02:45 — A valid signature can still be a replay

Now imagine an attacker copies a perfectly valid signed request and sends it again. The signature is still mathematically correct. That is why Beacon applies a second gate after signature verification: freshness plus replay protection. [S1][S3]

The current guard defaults to a maximum age of 900 seconds, a maximum future skew of 120 seconds, and a replay cache of up to 50,000 nonce entries. It rejects missing nonces, missing or unparsable timestamps, timestamps older than the allowed window, timestamps too far in the future, and a nonce that has already been accepted. [S1][S3]

That separation matters: cryptographic authenticity answers “were these bytes signed by the holder of this key?” The window check answers “should I accept this signed message now, and only once?”

## 02:45–03:30 — Tamper test

Here is the practical falsification test. Start with one valid signed envelope. Verify it: accepted. Send the identical envelope again: the replay guard should return `replay_nonce`. Next, change any signed field without producing a new signature: verification should return `signature_invalid`. Finally, remove the public key for a sender the receiver has never pinned: the result should be `signature_unverifiable`. Those cases are listed in Beacon's cross-language interoperability checklist, so another implementation can test behavior against the same contract. [S1]

## 03:30–04:12 — Local demo a human can reproduce

The repository's quick start is intentionally small. Create an identity with `beacon identity new`. In one terminal run `beacon webhook serve --port 8402`. In another, send a signed hello envelope to the local inbox with `beacon webhook send http://127.0.0.1:8402/beacon/inbox --kind hello --text "Hello from my agent"`. Then inspect the inbox. The repository also includes a loopback smoke script for this local webhook path. [S4]

## 04:12–04:28 — Close

The useful mental model is “signed, not automatically trusted.” Beacon v2 binds identity to a public key, signs the whole application payload, and separately checks time and nonce reuse. That gives a receiver concrete reasons to accept, reject, or call a message unverifiable — instead of treating any JSON that says “I am agent X” as proof. [S1][S2][S3]
