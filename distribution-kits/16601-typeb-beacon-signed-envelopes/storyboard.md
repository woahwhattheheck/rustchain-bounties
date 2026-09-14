# Storyboard — Signed, Not Trusted

Target: 16:9, 1080p or 4K capture. Narration follows `script.md`. Keep terminal text at least 42 px equivalent after scaling.

| Time | Visual | Exact capture instruction |
|---|---|---|
| 00:00–00:08 | Cold open | Full-screen title card using `thumbnail.png`: “SIGNED, NOT TRUSTED”. Add four small labels: Identity / Integrity / Freshness / Replay. |
| 00:08–00:24 | Four questions | Animate four questions one at a time over a simple JSON envelope graphic. Do not show invented metrics. |
| 00:24–00:42 | Envelope anatomy | Open `docs/MINIMUM_ENVELOPE.md` at the “Minimal valid v2 envelope” block on the pinned commit. Zoom to `v`, `kind`, `agent_id`, `ts`, `nonce`, `pubkey`, `sig`. |
| 00:42–01:08 | Canonical signing | Split screen: left `docs/MINIMUM_ENVELOPE.md` “What exactly gets signed”; right `beacon_skill/codec.py` at `_canonical_json()` and the signing payload. Highlight “everything except sig”. |
| 01:08–01:30 | Identity binding | Show `verify_envelope()` in `beacon_skill/codec.py`. Highlight `agent_id_from_pubkey(...)` and the comparison to claimed `agent_id`. |
| 01:30–01:52 | Unknown key case | Keep `verify_envelope()` visible. Highlight embedded `pubkey`, fallback `known_keys`, and the `None` return when no key is available. Caption: “Unverifiable ≠ valid.” |
| 01:52–02:10 | Replay threat | Duplicate one envelope card visually. Put green “signature valid” on both, then red “same nonce” on the second. This is a diagram, not a live network claim. |
| 02:10–02:45 | Guard constants | Open `beacon_skill/guard.py`. Highlight `DEFAULT_MAX_AGE_S = 900`, `DEFAULT_MAX_FUTURE_SKEW_S = 120`, `DEFAULT_MAX_NONCES = 50000`, then the stale/future/replay branches. |
| 02:45–03:05 | Interop test 1 | Show a three-row test board: valid once → `ok`; identical second send → `replay_nonce`; tampered field → `signature_invalid`. Source is the cross-language checklist in `MINIMUM_ENVELOPE.md`. |
| 03:05–03:30 | Interop test 2 | Add fourth row: unknown sender without usable public key → `signature_unverifiable`. Show the result-code table beside it. |
| 03:30–03:44 | Terminal A | Record a terminal running `beacon identity new`, then `beacon webhook serve --port 8402`. Use a disposable local test identity; never expose a real private key or mnemonic. |
| 03:44–03:59 | Terminal B | Record `beacon webhook send http://127.0.0.1:8402/beacon/inbox --kind hello --text "Hello from my agent"` exactly as documented. |
| 03:59–04:12 | Inbox | Record `beacon inbox list --limit 1`. If the local environment differs, use the repository's loopback smoke path rather than staging a fake success screen. |
| 04:12–04:28 | Close | Four checkmarks: key→ID binding; signed payload; time window; single-use nonce. End card: “Verify the envelope. Then apply application policy.” |

## Production notes

- All code/doc captures must show the pinned source commit in the browser URL or a visible commit label.
- Do not display private keys, seed phrases, auth tokens, wallets, or unrelated browser tabs.
- Do not imply that a valid Beacon signature authorizes a payment, tool call, or business action by itself. This package covers envelope authenticity/freshness/replay only.
- If a live command output cannot be reproduced, show the source-defined expected reason code and label it “spec example”; never fabricate a terminal success.
