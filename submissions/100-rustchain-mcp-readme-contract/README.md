# Bounty #100 — rustchain-mcp README contract repair

Target: `Scottcjn/rustchain-mcp`

Pinned upstream base: `4b402e5a74575798610b4db8f7c4902682fc85f0`

Source issues:
- https://github.com/Scottcjn/rustchain-mcp/issues/279 — BoTTube heading says 5 tools while the section lists 7.
- https://github.com/Scottcjn/rustchain-mcp/issues/280 — bounty example calls nonexistent `get_bounties(status="open", min_reward=100)` instead of the implemented `bounty_search(..., min_rtc=...)` contract.

## Deliverable

`rustchain-mcp-readme-contract.patch` is a focused patch against the pinned upstream commit. It:

1. changes `BoTTube Platform (5 tools)` to `BoTTube Platform (7 tools)`;
2. rewrites the bounty example to call `bounty_search(min_rtc=100)` and consume `result["bounties"]` / `rtc_reward`, matching the implementation and existing ecosystem tests;
3. adds `tests/test_readme_tool_contract.py`, a small documentation-contract regression that rejects the stale `get_bounties` call and verifies the BoTTube heading count matches its listed tools.

The standalone proposed test file is also included here as `test_readme_tool_contract.py` for easy inspection.

## Fresh-source evidence

At the pinned upstream base:

- `README.md` blob: `533da3f749158654c198bac93606eeeb51a79f5f`.
- `rustchain_mcp/server.py` defines `bounty_search(keyword="", min_rtc: float = 0, max_rtc: float = 0, ...)`.
- `tests/test_ecosystem_tools.py` already treats the return value as a mapping with `result["bounties"]` and each bounty's `rtc_reward`.

## Validation

The proposed documentation transformation was checked against the exact README excerpts fetched from the pinned upstream commit. The regression logic passes on the corrected excerpt with exactly 7 listed `bottube_*` tools and rejects the old `get_bounties(...)` call.

A full checkout-based pytest run could not be performed in this runtime because its shell environment cannot resolve `github.com`; all source reads and publication were therefore performed through the GitHub connector against the pinned commit.

## Submission state

The connected GitHub App has read-only access to `Scottcjn/rustchain-mcp` and no fork of that repository exists under `woahwhattheheck`, so it cannot create the normal upstream PR branch directly. This public artifact is the sponsor-documented fallback for a connector-specific 403/no-write condition and is intended to be applied as a normal focused PR when a user-authenticated GitHub route is available.
