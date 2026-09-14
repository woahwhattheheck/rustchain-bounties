# 9:16 storyboard and exact capture instructions

Target canvas: 1080×1920, 30 fps. Keep all essential text inside the center 80% safe area. Total target length: 46–55 seconds.

## 0:00–0:04 — Hook

Visual: solid background or terminal blur with large centered text:

`AI AGENT → AI AGENT PAYMENT`

Second line: `SIGNED. PROGRAMMATIC. RTC.`

Narration: “This is an AI agent paying another AI agent — without a checkout page.”

## 0:04–0:12 — Show the public feature

Visual: screen capture of `Scottcjn/beacon-skill` `SKILL.md`, zoomed to the bullets that say Beacon can send RustChain RTC payments using signed Ed25519 transfers.

On-screen label: `Beacon + RustChain`

Narration: “Beacon's RustChain transport can create an Ed25519 wallet and derive an RTC address from its public key.”

## 0:12–0:21 — One-line payment command

Visual: terminal capture. Type, but do not execute unless using an authorized disposable/test wallet:

```text
beacon rustchain pay RTCabc123... 1.5 --memo "bounty: #21"
```

On-screen callouts animate over `RTCabc123...`, `1.5`, and `--memo` as `recipient`, `amount`, `job reference`.

Narration: “The payment command is one line: beacon rustchain pay an RTC address, an amount, and an optional memo.”

## 0:21–0:35 — What gets signed

Visual: capture `beacon_skill/transports/rustchain.py`, function `sign_transfer()`. Highlight in sequence:

1. `from`, `to`, `amount`, `memo`, `nonce`
2. `json.dumps(... sort_keys=True, separators=(",", ":"))`
3. `sk.sign(msg).hex()`

On-screen label: `deterministic payload → Ed25519 signature`

Narration: “Under the hood, the client builds the sender, recipient, amount, memo, and nonce; serializes that data deterministically; signs it with Ed25519...”

## 0:35–0:43 — Send the signed payload

Visual: remain in the same source file and move to `transfer_signed()`. Highlight the POST to `/wallet/transfer/signed`.

On-screen label: `POST /wallet/transfer/signed`

Narration: “...then posts the signed payload to `/wallet/transfer/signed`.”

## 0:43–0:50 — Key custody / practical use

Visual: split card. Left: `PRIVATE KEY: LOCAL`. Right: `MEMO: bounty: #21`.

Narration: “The private key stays local. So an agent can put the job reference in the memo and send RTC programmatically.”

## 0:50–0:55 — End card

Visual: `AGENT ECONOMY > CHATBOT DEMO` then smaller line `Source: github.com/Scottcjn/beacon-skill`.

Narration: “Agent-to-agent coordination is already an economic protocol, not just chat.”

## Capture safety

- Never display a real private key, seed phrase, mnemonic, API token, or authenticated request header.
- The command capture can be non-executing; Type C requires a production-ready clip kit, not a live transfer.
- If the publisher chooses to execute a transfer, use only a wallet and amount they are authorized to use and record only public output needed for the clip.
- Use the immutable source URLs in `SOURCES.md` rather than a moving branch when capturing code.
