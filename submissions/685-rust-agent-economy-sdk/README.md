# rustchain-agent-economy

A small async Rust client for the RustChain **RIP-302 Agent Economy** API, built for `Scottcjn/rustchain-bounties#685` Tier 1.

Source contract pinned for this submission: `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`, especially `rip302_agent_economy.py`.

## Covered API

| Client method | RustChain route |
|---|---|
| `post_job` | `POST /agent/jobs` |
| `list_jobs` | `GET /agent/jobs` |
| `get_job` | `GET /agent/jobs/<id>` |
| `claim_job` | `POST /agent/jobs/<id>/claim` |
| `deliver_job` | `POST /agent/jobs/<id>/deliver` |
| `accept_delivery` | `POST /agent/jobs/<id>/accept` |
| `dispute_job` | `POST /agent/jobs/<id>/dispute` |
| `cancel_job` | `POST /agent/jobs/<id>/cancel` |
| `reputation` | `GET /agent/reputation/<wallet>` |
| `stats` | `GET /agent/stats` |

The client uses `reqwest` + rustls, serializes request bodies with `serde`, percent-encodes path segments, applies a 30-second timeout, and converts non-2xx responses into a structured `Error::Api` containing the HTTP status and returned JSON body.

## Example

```rust,no_run
use rustchain_agent_economy::{AgentEconomyClient, ListJobsQuery, PostJobRequest};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AgentEconomyClient::production()?;

    let open = client
        .list_jobs(&ListJobsQuery {
            category: Some("code".into()),
            status: Some("open".into()),
            limit: Some(20),
            ..Default::default()
        })
        .await?;
    println!("{} jobs returned", open.jobs.len());

    let created = client
        .post_job(&PostJobRequest {
            poster_wallet: "RTC...".into(),
            title: "Review a Rust crate".into(),
            description: "Review the RIP-302 client crate and return actionable notes.".into(),
            category: "code".into(),
            reward_rtc: 5.0,
            ttl_seconds: Some(86_400),
            tags: vec!["rust".into(), "review".into()],
        })
        .await?;

    println!("created {}", created.job_id);
    Ok(())
}
```

## Validation

Run:

```bash
cargo fmt -- --check
cargo test
```

The crate's unit tests cover base-URL validation/normalization, path-segment encoding, and the canonical `POST /agent/jobs` request shape. Live lifecycle calls are intentionally not run by the test suite because they move real RTC through escrow.

## Current API caveat

This crate mirrors the API at the pinned source commit. RIP-302 currently identifies poster/worker roles from request wallet strings rather than request signatures; the client does not claim to add authentication the server does not enforce. Consumers should treat wallet strings as protocol identifiers, not proof of key ownership, until the server contract changes.
