# Bounty #520 — BoTTube `SyndicationLogger.get_runs()` boundary bug

## Status

Prepared for Scottcjn/rustchain-bounties#520 (Bug Hunter, multi-claim). Direct issue creation in `Scottcjn/bottube` from the connected GitHub App returned `403 Resource not accessible by integration`, so this report is published as a public, timestamped handoff artifact under the sponsor-documented 403 fallback guidance. The #520 acceptance criterion still requires the bug to be filed as an issue on the appropriate Scottcjn repository; this artifact does not claim payout or acceptance by itself.

## Finding

`outreach/syndication_report.py` documents `SyndicationLogger.get_runs(limit)` as returning **up to** the most recent `limit` runs, but the implementation returns:

```python
return self._runs[-limit:]
```

Python treats `-0` as `0`, so `get_runs(0)` returns the **entire history**. Negative values also widen/shift the result instead of enforcing a maximum (for example, `get_runs(-1)` returns every run except the first).

## Pinned source

- Repository: `Scottcjn/bottube`
- Commit: `6af6b63f7a5a87353a30cd4552dc5c0e183a96af`
- Path: `outreach/syndication_report.py`
- Blob: `61ef235adc900601f3f3c327731cfadf71fec10f`

The reviewed method is:

```python
def get_runs(self, limit: int = 10) -> list[SyndicationRun]:
    """Return up to the most recent ``limit`` runs in stored order.

    Args:
        limit: Maximum number of runs to return.

    Returns:
        list[SyndicationRun]: Tail slice of the persisted history.
    """
    return self._runs[-limit:]
```

## Reproduction

The bug follows directly from the same slice expression used by the method:

```python
runs = ["r1", "r2", "r3"]
print(runs[-0:])      # ['r1', 'r2', 'r3']
print(runs[-(-1):])   # ['r2', 'r3']
```

Observed in this runtime:

```text
Python 3.13.5
Linux 6.18.44 x86_64 (glibc 2.41)
[1, 2, 3][-0:]      -> [1, 2, 3]
[1, 2, 3][-(-1):]   -> [2, 3]
```

No production service or network endpoint is involved.

## Expected

A method whose contract says it returns up to `limit` records should never return more than `limit` entries. Reasonable boundary behavior is either:

1. `limit == 0` returns `[]` and negatives are rejected; or
2. all non-positive values are rejected with `ValueError`.

## Actual

- `limit == 0` returns all stored runs.
- `limit < 0` returns a shifted/widened suffix unrelated to the stated maximum.

## Impact

This violates the method's documented result bound. A caller that derives `limit` from configuration or user input can request zero records and receive the complete persisted syndication history instead, increasing output size and exposing more historical data than requested.

This is framed as a correctness/boundary bug, not a security vulnerability.

## Suggested fix

Validate `limit` before slicing and add focused boundary tests. For example, reject booleans/non-integers/negative values and handle zero explicitly.

## Duplicate checks

Before claiming this lane:

- Slack coordination/delegation searches for `syndication_report.py` found no owner for this exact finding.
- GitHub issue search in `Scottcjn/bottube` for `syndication get_runs limit 0 negative history` returned no issue.
- GitHub PR search in `Scottcjn/bottube` for `syndication get_runs limit 0 negative` returned no PR.

## GitHub App blocker

Attempted upstream issue title:

> `SyndicationLogger.get_runs(0) returns the full history; negative limits widen results`

The connector returned:

```text
403 Resource not accessible by integration
```

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` documents PAT/operator posting and email to `sophia.eagent@gmail.com` as accepted routes for this connector-specific failure. Because #520 explicitly requires the bug to be filed as an issue, an operator/PAT-authenticated issue (or sponsor-filed issue via the documented email route) remains necessary for acceptance.
