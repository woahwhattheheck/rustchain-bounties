# Storyboard / capture plan

Canvas: **1080 × 1920 (9:16)**. Keep code and captions inside the central 80% safe area. Use only the source-pinned RustChain repository, simple kinetic text, and neutral UI mockups; do not fabricate production transaction screenshots.

| Time | Visual / capture instruction | On-screen text |
|---|---|---|
| 0:00–0:05 | Open on two simple agent icons facing each other. Animate a task card moving from Agent A to Agent B, then freeze before payment. | **CAN AN AGENT HIRE AN AGENT?** |
| 0:05–0:13 | Screen-capture the header/docstring of `rip302_agent_economy.py` at commit `aa584b3…`, zooming to “Agent-to-Agent RTC Economy”. | `RIP-302` / `agent-to-agent jobs` |
| 0:13–0:23 | Capture the constants and job-posting section. Highlight `PLATFORM_FEE_RATE = 0.05`, `ESCROW_WALLET = "agent_escrow"`, then the lines calculating `escrow_i64 = reward_i64 + platform_fee_i64`. | `reward + 5% fee → escrow` |
| 0:23–0:31 | Build a four-stage vertical status stack with words copied from the source constants: OPEN → CLAIMED → DELIVERED → COMPLETED. Animate a highlight downward. | `open → claimed → delivered` |
| 0:31–0:42 | Capture the `/agent/jobs/<job_id>/accept` section and the JSON response showing `status: completed`, `reward_paid_rtc`, and `platform_fee_rtc`. Do not show fake values. | `accept → worker paid` / `fee routed separately` |
| 0:42–0:50 | Capture `_expire_refundable_job` and highlight the call to `_refund_escrow`. Overlay a reverse arrow back to the poster icon. | `expired open/claimed job → refund path` |
| 0:50–0:57 | Return to the two-agent diagram, now show four compact verbs between them: POST · CLAIM · DELIVER · SETTLE. | `ONE JOB LIFECYCLE` |
| 0:57–0:60 | Static end card. | `RIP-302 · RustChain` / `github.com/Scottcjn/Rustchain` |

## Editor guardrails

1. Never replace the code capture with invented wallet balances, transaction IDs, or explorer confirmations.
2. If a live UI is used, label it “live capture” only if the editor actually records the deployed endpoint at assembly time.
3. The phrase “escrow” here describes the implementation’s internal `agent_escrow` accounting path; do not add “trustless” or “smart contract” unless separately sourced.
4. Keep “five-percent platform fee” tied to the pinned source SHA because economics can change.
5. If source main advances before publishing, either keep the SHA visible or re-verify every claim against the new commit.
