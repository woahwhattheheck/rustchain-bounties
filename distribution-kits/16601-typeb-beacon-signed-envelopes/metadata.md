# Metadata

## Primary title
**Signed, Not Trusted: How Beacon Verifies Agent-to-Agent Messages**

## Alternate titles
1. **Can an AI Agent Prove Who Sent This? Inside Beacon v2**
2. **Replay Blocked: Ed25519 Envelopes for Agent-to-Agent Messages**

## Description
AI agents can exchange JSON instantly, but receivers still need to verify identity, message integrity, freshness, and replay. This source-grounded walkthrough opens Beacon v2's signed envelope format, shows how its Ed25519 verifier binds a public key to a `bcn_...` agent ID, and follows the separate timestamp + nonce replay gate.

Source pin used for every technical claim:
`Scottcjn/beacon-skill@ca658f39bf018e66096e038bb6208b78814811e5`

Repository: https://github.com/Scottcjn/beacon-skill  
Minimum envelope contract: https://github.com/Scottcjn/beacon-skill/blob/ca658f39bf018e66096e038bb6208b78814811e5/docs/MINIMUM_ENVELOPE.md

This video explains the envelope-verification mechanism only. A valid signed envelope is not, by itself, authorization for a payment, tool call, or other external action.

## Chapters
00:00 Four questions every receiver must answer  
00:24 Anatomy of a Beacon v2 envelope  
01:08 Binding an agent ID to a public key  
01:52 Why signatures do not stop replay  
02:45 Tamper and replay falsification tests  
03:30 Reproducible local webhook demo  
04:12 What verification does—and does not—prove

## Tags
Beacon Protocol, AI agents, agent to agent, Ed25519, cryptography, replay protection, signed messages, MCP, webhook, open source, agent security

## One-line pitch
A 4.5-minute source-level explainer that turns “agent identity” from a label into a falsifiable verification flow: key binding, canonical Ed25519 signatures, time windows, and one-use nonces.
