#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Sweep un-adjudicated PR-review claims through the #73 gate.

WHY THIS EXISTS
---------------
`pr-review-gate.yml` fires on `issues: [opened, edited]`. That adjudicates a
claim exactly once, at the instant it is filed, and never again. Any claim
that missed that instant -- filed while the gate was failing, filed before the
gate existed, or edited in a way that did not re-trigger -- was invisible
forever. It sat open with no label, no verdict, and no reply.

That single trigger config produced a backlog of 104 silent claims with a
median age of 82 days, across 44 real contributors. `bounty_payout.py` only
pays claims the gate has labelled, so silence there meant no payout, which
meant contributors stopped showing up.

This sweep is the safety net: it re-drives the same gate over anything that
was never adjudicated, so a missed webhook costs a few hours instead of
forever.

SAFETY
------
  - The gate itself is idempotent: it skips issues it has already labelled or
    closed. Re-running is harmless.
  - Discovery paginates ALL open issues. MAX_PER_RUN bounds adjudication work,
    not discovery; otherwise an issue outside a discovery cap can be stranded
    forever while the run reports a clean queue.
  - Bounded per run (MAX_PER_RUN, default 60) so one sweep cannot exhaust the
    API budget. When the bound truncates the queue, the remainder is REPORTED,
    not silently dropped -- a silent cap reads as "everything is handled".
  - Bounded batches rotate with GitHub Actions' persistent GITHUB_RUN_NUMBER,
    so a permanently unresolved prefix cannot consume every scheduled sweep.
    The rotation covers the combined never-adjudicated + stranded queue, so
    neither class can starve the other merely by remaining ahead in sort order.
  - Only touches issues whose title is a review claim, per the gate's own
    `is_review_claim`, so it cannot wander into unrelated issues.

Env: GITHUB_TOKEN, GH_REPO, TARGET_REPO, CAP, RATE_RTC, MAX_PER_RUN,
     PROCESSED_LABEL. GITHUB_RUN_NUMBER is supplied automatically by Actions;
     local/off-Actions invocations use rotation seed 0.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = os.environ.get("GH_REPO", "Scottcjn/rustchain-bounties")
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "60"))
PROCESSED_LABEL = os.environ.get("PROCESSED_LABEL", "gate-processed")
SCRIPT_DIR = Path(__file__).resolve().parent


def _load_gate():
    """Import pr_review_gate for its is_review_claim() classifier only."""
    spec = importlib.util.spec_from_file_location(
        "pr_review_gate_mod", SCRIPT_DIR / "pr_review_gate.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _flatten_issue_pages(raw):
    """Validate and flatten `gh api --paginate --slurp` issue pages.

    `gh api --slurp` wraps each REST page in an outer list. Accept a flat list
    too so fixtures and older gh builds remain compatible, but reject any mixed
    or non-list shape: partial discovery is never an authoritative queue.
    """
    if not isinstance(raw, list):
        raise ValueError("issue enumeration must be a JSON list")
    if not raw:
        return []
    if all(isinstance(page, list) for page in raw):
        items = [item for page in raw for item in page]
    elif all(isinstance(item, dict) for item in raw):
        items = raw
    else:
        raise ValueError("issue enumeration returned a mixed/unexpected shape")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError("issue enumeration contained a non-object item")
    # REST /issues includes pull requests; `gh issue list` did not. Preserve
    # issue-only semantics explicitly after switching to exhaustive REST pages.
    return [item for item in items if "pull_request" not in item]


def list_unprocessed(gate):
    """Open review claims that carry neither the processed label nor a verdict.

    Authoritative issue enumeration must fail CLOSED. A failed `gh api`, bad
    JSON, unexpected shape, or incomplete pagination must NOT be read as "zero
    open claims" -- that would silently strand every unprocessed claim while
    this safety-net run reports success.

    IMPORTANT: discovery is deliberately unbounded by MAX_PER_RUN. The repo can
    have more than 1,000 open issues; a fixed `gh issue list --limit 1000`
    silently hid older review claims outside that window. We page the REST
    `/issues` collection to exhaustion, then bound only adjudication below.
    """
    proc = subprocess.run(
        ["gh", "api", "--paginate", "--slurp",
         f"repos/{REPO}/issues?state=open&per_page=100&sort=created&direction=asc"],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:200]
        print(f"::error::gh issue enumeration failed (exit {proc.returncode}): {detail}",
              file=sys.stderr)
        sys.exit(1)
    try:
        issues = _flatten_issue_pages(json.loads(proc.stdout or "[]"))
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"::error::could not parse complete issue enumeration: {exc}", file=sys.stderr)
        sys.exit(1)

    never, stranded = [], []
    for i in issues:
        labels = {l["name"] for l in i.get("labels", [])}
        if not gate.is_review_claim(i.get("title") or ""):
            continue
        if "bounty-eligible" in labels:
            continue                       # adjudicated and payable; done
        if "needs-human" in labels:
            # Unresolved, not decided. These are stranded by construction:
            # once flagged, the gate's idempotency check skipped them forever,
            # so every later fix to the gate left its own past victims behind.
            # Re-adjudicating is how a fix reaches them. Retries stay silent
            # unless the verdict improves, so this costs no notification noise.
            stranded.append(i["number"])
        elif PROCESSED_LABEL not in labels:
            never.append(i["number"])
    return sorted(never), sorted(stranded)


def _rotation_run_number():
    """Return the durable Actions run counter used as the fair-queue cursor.

    Scheduled and workflow_dispatch runs always receive GITHUB_RUN_NUMBER from
    Actions. A local invocation has no durable scheduler state, so seed zero is
    explicit rather than pretending local reruns provide cross-run fairness.
    """
    raw = os.environ.get("GITHUB_RUN_NUMBER", "0")
    try:
        run_number = int(raw)
    except ValueError as exc:
        raise ValueError(f"GITHUB_RUN_NUMBER must be an integer, got {raw!r}") from exc
    if run_number < 0:
        raise ValueError("GITHUB_RUN_NUMBER must be >= 0")
    return run_number


def select_batch(never, stranded, max_per_run, run_number):
    """Select one bounded batch without allowing a stable prefix to starve tail.

    The combined queue keeps the historical never-adjudicated-first ordering as
    its canonical ordering, then rotates the *bounded window* by a durable
    Actions run counter. Advancing by one full batch per run means a static
    queue is covered in consecutive chunks (wrapping at the end); a permanently
    unresolved first batch therefore cannot be selected forever.

    Returns (new_claim_numbers, retry_claim_numbers). The two lists are split
    only after fair selection so one class cannot monopolize every run simply
    by occupying the front of the canonical queue.
    """
    if max_per_run <= 0:
        raise ValueError("MAX_PER_RUN must be > 0")
    if run_number < 0:
        raise ValueError("run_number must be >= 0")

    queue = [(False, n) for n in sorted(never)] + [(True, n) for n in sorted(stranded)]
    total = len(queue)
    if not total:
        return [], []

    if total > max_per_run:
        start = (run_number * max_per_run) % total
        rotated = queue[start:] + queue[:start]
        selected = rotated[:max_per_run]
    else:
        selected = queue

    batch_new = [number for retry, number in selected if not retry]
    batch_retry = [number for retry, number in selected if retry]
    return batch_new, batch_retry


def adjudicate(number, retry=False):
    env = {**os.environ, "ISSUE_NUMBER": str(number)}
    if retry:
        env["RETRY_NEEDS_HUMAN"] = "1"
    r = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "pr_review_gate.py")],
        capture_output=True, text=True, timeout=120, env=env,
    )
    ok = r.returncode == 0
    if not ok:
        print(f"::warning::gate failed on #{number}: {(r.stderr or '').strip()[:200]}")
    return ok


def main():
    try:
        run_number = _rotation_run_number()
        if MAX_PER_RUN <= 0:
            raise ValueError("MAX_PER_RUN must be > 0")
    except ValueError as exc:
        print(f"::error::invalid backfill scheduling configuration: {exc}", file=sys.stderr)
        return 2

    gate = _load_gate()
    never, stranded = list_unprocessed(gate)
    total = len(never) + len(stranded)
    batch_new, batch_retry = select_batch(never, stranded, MAX_PER_RUN, run_number)
    print(f"gate-backfill: {len(never)} never-adjudicated, {len(stranded)} stranded "
          f"on needs-human; processing {len(batch_new)}+{len(batch_retry)} "
          f"(fair rotation run={run_number})")

    done = 0
    for n in batch_new:
        if adjudicate(n):
            done += 1
    for n in batch_retry:
        if adjudicate(n, retry=True):
            done += 1

    processed = len(batch_new) + len(batch_retry)
    remaining = total - processed
    print(f"gate-backfill: adjudicated {done}/{processed}")
    if remaining > 0:
        # Never let a bound look like completion.
        print(f"::notice::{remaining} claims still pending "
              f"(MAX_PER_RUN={MAX_PER_RUN}); fair rotation advances next run.")

    # Fail the run when adjudications failed.
    #
    # This used to `return 0` unconditionally, so all 60 claims in a batch could
    # fail and the workflow still went green. These are precisely the claims the
    # safety net exists to rescue from being stranded, so a green run reporting
    # "adjudicated 0/60" was the worst possible outcome: the backlog looked
    # handled while nothing had been. Reported by @AInoAKARI under #16471.
    failed = processed - done
    if failed:
        print(f"::error::{failed} of {processed} adjudications FAILED; "
              f"the claims they cover are still unresolved")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
