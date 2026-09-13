# Bounty #16471 — docstring held-sweep starvation finding

Claimant: `woahwhattheheck`

Payout destination: GitHub handle `woahwhattheheck`

Audited upstream commit: `c2d3f22c33cfaf8b2ff9de3412e1460e64fe70a4`

## Finding

The scheduled docstring sweep can silently starve `awaiting-merge` claims beyond the first Search API page while reporting 60 successful adjudications.

`.github/workflows/docstring-gate.yml` fetches held claims with one request capped at `per_page=60` and does not paginate:

```sh
held=$(gh api -X GET search/issues \
        -f q="repo:${GH_REPO} is:issue is:open label:awaiting-merge" \
        -f per_page=60 --jq '.items[].number' 2>/dev/null || true)
```

The same loop stops after 60 attempts. Separately, `scripts/docstring_gate.py` never removes `awaiting-merge` when a formerly held claim later verifies; it only adds `bounty-eligible` and `docstring-verified`. On later sweeps, those terminal claims hit the initial `already adjudicated; skipping` branch and return `0`, while the workflow counts every `rc == 0` as another `adjudicated` claim.

Concrete path:

1. 61 open claims carry `awaiting-merge`.
2. The first 60 later merge and verify, but retain `awaiting-merge`.
3. Claim 61 becomes merge-ready outside the single 60-row response.
4. A later sweep can fetch the same 60 already-terminal held claims. Each returns zero immediately.
5. The workflow increments `adjudicated` 60 times, hits its 60-attempt break, prints `attempted 60 claim(s): adjudicated 60, failed 0`, and exits green.
6. Claim 61 was never fetched, so later payable work can remain invisible behind stale terminal queue members while every scheduled run reports success.

This is distinct from the already-reported GitHub-inventory failure path and the closed-PR `awaiting-merge` loop: all API reads may succeed here. The defect is the composition of stale queue membership, no pagination, the 60-attempt ceiling, and treating an already-terminal skip as a completed adjudication.

## Suggested remediation

- Remove `awaiting-merge` on terminal adjudication, or exclude terminal labels from the held search.
- Paginate held/fresh searches to exhaustion.
- Distinguish `processed`, `deferred`, and `already-terminal` gate outcomes rather than counting any zero exit as `adjudicated`.

Public immutable evidence copy: https://github.com/woahwhattheheck/startup-credits/blob/cffa13dc53c9967b8439773ca9560850214ec7dd/bounty-evidence/rustchain-16471-docstring-held-sweep-starvation.md

Direct issue-comment submission returned `403 Resource not accessible by integration`; this PR/file route is documented by `docs/HOW_TO_SUBMIT_A_BOUNTY.md` as a fallback for that connector limitation.
