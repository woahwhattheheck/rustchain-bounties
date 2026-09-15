# Bug report — Beacon Atlas `calibration_history(limit)` boundary widens history

Bounty lane: `Scottcjn/rustchain-bounties#520` — Bug Hunter (3 RTC, multi-claim)

Upstream target: `Scottcjn/beacon-skill`

Source pin: `ca658f39bf018e66096e038bb6208b78814811e5`

Affected path: `beacon_skill/atlas.py`

Affected method: `AtlasManager.calibration_history()`

## Summary

`AtlasManager.calibration_history(agent_id, limit)` ends with:

```python
return entries[-limit:]
```

This has a boundary bug in Python: `-0 == 0`, so `limit=0` returns the entire matching calibration history instead of zero rows. Negative limits also silently shift the slice rather than behaving as a bounded “last N” query or being rejected.

This is distinct from the recently hardened `beacon_skill.storage.read_jsonl_tail()` path: `calibration_history()` performs its own independent slicing and does not call that helper.

## Reproduction environment

- OS/kernel: Linux 6.18.44 x86_64
- Python: 3.13.5
- Upstream source reviewed at: `Scottcjn/beacon-skill@ca658f39bf018e66096e038bb6208b78814811e5`

The reproduction below isolates the exact current parsing/filtering/slicing logic against a temporary `calibrations.jsonl`; it is not represented as a full-package checkout test.

## Minimal reproducer

```python
import json
import tempfile
from pathlib import Path

rows = [
    {"agent_a": "bcn_target", "agent_b": "bcn_peer1", "overall": 0.1, "ts": 1},
    {"agent_a": "bcn_other", "agent_b": "bcn_peer2", "overall": 0.2, "ts": 2},
    {"agent_a": "bcn_peer3", "agent_b": "bcn_target", "overall": 0.3, "ts": 3},
    {"agent_a": "bcn_target", "agent_b": "bcn_peer4", "overall": 0.4, "ts": 4},
]

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "calibrations.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def current_calibration_history(agent_id, limit=50):
        entries = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("agent_a") == agent_id or entry.get("agent_b") == agent_id:
                    entries.append(entry)
            except Exception:
                continue
        return entries[-limit:]

    for limit in (2, 1, 0, -1, -5):
        got = current_calibration_history("bcn_target", limit)
        print(f"limit={limit}: count={len(got)} ts={[e['ts'] for e in got]}")
```

Observed output:

```text
limit=2: count=2 ts=[3, 4]
limit=1: count=1 ts=[4]
limit=0: count=3 ts=[1, 3, 4]
limit=-1: count=2 ts=[3, 4]
limit=-5: count=0 ts=[]
```

The zero-limit case is the clearest contract violation: requesting zero rows returns all three matching rows. Negative limits are non-monotonic and likewise do not describe a sensible bounded-history contract.

## Expected behavior

A history `limit` should not return more rows when reduced to zero or made negative. A consistent boundary contract would be:

- `limit == 0` → `[]`
- `limit < 0` → reject with `ValueError` (matching the boundary policy already used by the hardened JSONL-tail helper), or explicitly reject at the caller boundary
- `limit > 0` → return at most the requested last N matching entries

## Impact

A caller that uses `0` as a natural “return no history” sentinel unexpectedly receives the complete per-agent calibration history. That can increase memory/output size and expose more historical interaction/calibration data than the caller asked for. Negative input can also widen or shift results instead of failing predictably.

Because Atlas implements this slice independently, hardening the shared storage helper does not fix this path.

## Suggested fix and regression coverage

Validate `limit` before reading/slicing, then add focused tests for:

1. `limit=0` returning an empty list;
2. a negative limit being rejected;
3. ordinary positive limits returning the last N matching entries;
4. a positive limit larger than the available history returning all available matching entries.

## Submission status

A direct GitHub-connector attempt to file this as an upstream `Scottcjn/beacon-skill` issue returned `403 Resource not accessible by integration`. An immediate exact-title search showed no ghost issue. This public, source-pinned report is published under the sponsor-documented connector-403 fallback so an operator/PAT-authenticated account can file the upstream issue verbatim and then link it on bounty #520.
