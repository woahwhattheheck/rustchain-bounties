# Bug report: ShaprAI lifecycle mutators bypass Sanctuary graduation and retirement invariants

**Bounty:** Scottcjn/rustchain-bounties#520 — Bug Hunter (3 RTC, multi-claim)  
**Target repository:** `Scottcjn/shaprai`  
**Pinned target commit:** `feb71994943437b3aabb8e1eb4c06fd8b93cf46f`  
**Affected files:** `shaprai/core/lifecycle.py`, `shaprai/sanctuary/educator.py`, `tests/core/test_lifecycle.py`  
**Lifecycle source:** https://github.com/Scottcjn/shaprai/blob/feb71994943437b3aabb8e1eb4c06fd8b93cf46f/shaprai/core/lifecycle.py  
**Sanctuary source:** https://github.com/Scottcjn/shaprai/blob/feb71994943437b3aabb8e1eb4c06fd8b93cf46f/shaprai/sanctuary/educator.py

## Summary

ShaprAI describes its lifecycle as:

```text
CREATED -> TRAINING -> SANCTUARY -> GRADUATED -> DEPLOYED -> RETIRED
```

and `SanctuaryEducator.graduate()` only marks an agent `GRADUATED` after `evaluate_progress()` says it is ready. That readiness check requires all Sanctuary lessons plus an average score at or above `ELYAN_CLASS_THRESHOLD`.

However, the generic lifecycle mutators do not enforce those invariants:

- `transition_state()` accepts **any** `AgentState` from **any** current state and simply writes it to the manifest;
- `deploy_agent()` unconditionally writes `DEPLOYED`, regardless of current state or `sanctuary.graduated`;
- therefore a freshly-created agent can be marked `GRADUATED` without completing Sanctuary, and a `RETIRED` agent can be moved back to `DEPLOYED` with no explicit reactivation workflow.

This also permits contradictory manifests such as `state: graduated` while `sanctuary.graduated: false`.

## Affected source

At the pinned target commit, `transition_state()` contains no predecessor or gate validation:

```python
def transition_state(name, new_state, agents_dir=None):
    ...
    manifest = _load_manifest(name, agents_dir)
    old_state = manifest["state"]
    manifest["state"] = new_state.value
    manifest.setdefault("state_history", []).append(
        {
            "from": old_state,
            "to": new_state.value,
            "timestamp": time.time(),
        }
    )
    _save_manifest(name, manifest, agents_dir)
    return manifest
```

`deploy_agent()` similarly overwrites the lifecycle state directly:

```python
manifest = _load_manifest(name, agents_dir)
manifest["state"] = AgentState.DEPLOYED.value
manifest["platforms"] = platforms
```

In contrast, `SanctuaryEducator.graduate()` explicitly performs the gate first:

```python
progress = self.evaluate_progress(name)

if not progress["graduation_ready"]:
    return False

manifest = _load_manifest(name, self.agents_dir)
manifest["state"] = AgentState.GRADUATED.value
manifest.setdefault("sanctuary", {})["graduated"] = True
```

`evaluate_progress()` defines `graduation_ready` as all lessons completed **and** the average score meeting `ELYAN_CLASS_THRESHOLD`.

## Reproduction

On a checkout of the pinned revision:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import yaml

from shaprai.core.lifecycle import AgentState, deploy_agent, transition_state

with TemporaryDirectory() as td:
    agents_dir = Path(td)
    agent_dir = agents_dir / "demo"
    agent_dir.mkdir()

    # Represents a fresh, explicitly non-graduated agent.
    (agent_dir / "manifest.yaml").write_text(yaml.safe_dump({
        "name": "demo",
        "state": "created",
        "sanctuary": {
            "graduated": False,
            "lessons_completed": [],
            "scores": {},
        },
    }))

    skipped = transition_state("demo", AgentState.GRADUATED, agents_dir)
    print("after direct graduation:", skipped["state"], skipped["sanctuary"]["graduated"])

    transition_state("demo", AgentState.RETIRED, agents_dir)
    revived = deploy_agent("demo", ["github"], agents_dir)
    print("after redeploying retired agent:", revived["state"], revived["sanctuary"]["graduated"])
```

Observed behavior from the pinned implementation:

```text
after direct graduation: graduated False
after redeploying retired agent: deployed False
```

The first result shows the Sanctuary quality gate can be bypassed while leaving the manifest internally contradictory. The second shows retirement is not terminal: `deploy_agent()` revives the retired, still-non-graduated manifest.

A deterministic local execution of the pinned state-update logic produced the same output on the environment listed below.

## Existing tests miss the invariant

`tests/core/test_lifecycle.py` checks happy-path persistence but does not test invalid predecessors or consistency with Sanctuary graduation. In particular, its current `test_deploy_agent` creates an agent and immediately calls `deploy_agent()` from the `CREATED` state, so the test suite currently codifies the unchecked overwrite rather than asserting the documented lifecycle sequence.

That makes this easy to regress unnoticed: all current lifecycle tests can pass while the graduation and retirement invariants remain bypassable.

## Expected behavior

Lifecycle-changing entry points should share one transition policy instead of independently overwriting `manifest["state"]`.

At minimum:

1. `GRADUATED` must not be writable through a generic state setter unless the Sanctuary graduation requirements are satisfied (or the generic setter should disallow that state entirely and require `SanctuaryEducator.graduate()`).
2. `deploy_agent()` should require the appropriate pre-deployment state, normally `GRADUATED`.
3. `RETIRED` should be terminal unless the project intentionally provides a separately named, explicit reactivation path.
4. `state == GRADUATED` should not coexist with `sanctuary.graduated == False`.
5. Regression tests should cover illegal skips, redeploy-after-retirement, and state/Sanctuary consistency.

A small allowed-transition map (plus a special gate for graduation) would make the policy explicit and testable.

## Environment / verification context

- Target source pin: `feb71994943437b3aabb8e1eb4c06fd8b93cf46f`
- `shaprai/core/lifecycle.py` blob: `d2a3e5967cc6539776c9d017351fde44594948dd`
- `shaprai/sanctuary/educator.py` blob: `ffcb522bd3631deec7e73c4993c86aea797fa739`
- `tests/core/test_lifecycle.py` blob: `17ae64fed61f279ed27ca5f32fd10cb53f68d459`
- Linux 6.18.44 x86_64
- Python 3.13.5
- PyYAML 6.0.3
- Project metadata: ShaprAI `0.1.0`, Python `>=3.10`

## Duplicate / collision check

Before taking the lane:

- fresh target main was pinned at `feb71994943437b3aabb8e1eb4c06fd8b93cf46f`;
- GitHub issue search for lifecycle-state / transition / deploy-retired reports in `Scottcjn/shaprai` returned no match;
- GitHub PR search for the same lifecycle-transition defect returned no match;
- all-access Slack searches for `shaprai` and `shaprai lifecycle` returned no existing lane;
- the exact lane was announced in both coordination and delegations before publication work began.

## Submission-path note

A proper bug issue in `Scottcjn/shaprai` was attempted first and returned:

```text
403 Resource not accessible by integration
```

The `/claim` comment on bounty #520 returned the same connector-specific 403.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publishing a deliverable in a repository controlled by the contributor as a supported fallback for this GitHub-App error, followed by linking the public artifact; it also suggests trying a file pull request when issue comments are blocked. This report is the public, timestamped artifact under that documented fallback. No sponsor acceptance or payout is asserted here.
