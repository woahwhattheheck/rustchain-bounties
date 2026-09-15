# Source contract

Submission target: `Scottcjn/rustchain-bounties#685` Tier 1 — Rust client crate.

Pinned upstream: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`.

Authoritative route implementation:
- `rip302_agent_economy.py`
  - `POST /agent/jobs`
  - `GET /agent/jobs`
  - `GET /agent/jobs/<job_id>`
  - `POST /agent/jobs/<job_id>/claim`
  - `POST /agent/jobs/<job_id>/deliver`
  - `POST /agent/jobs/<job_id>/accept`
  - `POST /agent/jobs/<job_id>/dispute`
  - `POST /agent/jobs/<job_id>/cancel`
  - `GET /agent/reputation/<wallet_id>`
  - `GET /agent/stats`

Bounty contract:
- `Scottcjn/rustchain-bounties#685`, Tier 1: “Build a client library for the Agent Economy API in any language”, explicitly including a Rust client crate for 50 RTC.

Design choices:
- The write request structs use the exact server field names (`poster_wallet`, `worker_wallet`, `deliverable_url`, `deliverable_hash`, `result_summary`, `rating`, `reason`).
- Job listing exposes the current filters (`category`, `status`, `limit`, `offset`, `min_reward`).
- Success responses whose shape is stable in the route implementation are strongly typed. Variable/expanding job, reputation and stats payloads preserve all fields via `serde_json::Map` to avoid silently discarding forward-compatible server fields.
- Any non-2xx result is surfaced as `Error::Api { status, message, body }`; transport failures are distinct.
