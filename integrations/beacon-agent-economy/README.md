# RIP-302 Beacon Agent Economy integration

Implementation for `Scottcjn/rustchain-bounties#685` Tier 2: **Beacon skill that
posts/claims jobs (75 RTC)**.

This is a small installable adapter rather than a rewrite of Beacon. It targets
the current RIP-302 v2 job API and is designed to be vendored into or imported
by `Scottcjn/beacon-skill`.

## Scope

- browse and inspect jobs;
- signed job creation;
- claim and deliver;
- reputation and marketplace stats;
- JSON-schema-like action declarations for an agent/tool router;
- no private signing key in an action schema, function parameter, or wire body;
- no accept/dispute/cancel settlement tools in the agent-facing allowlist.

The default endpoint is `https://50.28.86.131`, matching the current RustChain
bounty submission guide. HTTP failures preserve the status, server code, and
complete decoded body.

## Run tests

```bash
python -m unittest discover -s tests -v
```

The test suite uses a fake HTTP session and therefore runs without a live node.
The contributor execution image used for this implementation could not connect
to `50.28.86.131:443`; no live-node success is claimed.

## Target integration

The intended upstream home is `Scottcjn/beacon-skill`. The current GitHub App
installation cannot create a fork or write to that repository, so this source
is published in the contributor-controlled bounty repo using the sponsor's
explicit `403 Resource not accessible by integration` fallback. The directory
is itself executable source, not a prose-only evidence packet.
