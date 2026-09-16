#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Sweep un-adjudicated PR-review claims through the #73 gate.

The event gate only runs when a claim is opened/edited. This scheduled safety
net redrives claims that missed that instant and gives older `needs-human`
claims one quiet retry against the current gate implementation.

Safety properties:
  * authoritative discovery paginates every open issue and fails closed;
  * MAX_PER_RUN bounds adjudication, never discovery;
  * retry work has reserved capacity whenever both new and stranded queues are
    non-empty, so normal new-claim growth cannot suppress retries;
  * each stranded claim receives at most one automatic retry per retry-marker
    version. The durable issue label is written BEFORE the retry. Even a
    persistently unresolved or failing low-numbered claim therefore cannot
    monopolize future sweeps. A future gate repair deliberately bumps
    RETRY_MARKER_LABEL to reopen the stranded population for one new pass;
  * retry markers are scheduling evidence only, not payout/verdict labels.
    The normal gate still owns `needs-human`, `gate-processed`, and
    `bounty-eligible`.

Env: GITHUB_TOKEN, GH_REPO, TARGET_REPO, CAP, RATE_RTC, MAX_PER_RUN,
     PROCESSED_LABEL, RETRY_MARKER_LABEL. GITHUB_RUN_NUMBER is supplied by
     Actions and is used only to alternate classes when MAX_PER_RUN == 1.
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
RETRY_MARKER_LABEL = os.environ.get(
    "RETRY_MARKER_LABEL", "gate-backfill-retry-v1"
)
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
    """Validate and flatten `gh api --paginate --slurp` issue pages."""
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
    return [item for item in items if "pull_request" not in item]


def list_unprocessed(gate):
    """Return (never_adjudicated, stranded_retryable) claim numbers.

    A `needs-human` claim is retryable exactly once per RETRY_MARKER_LABEL
    version. The marker is intentionally independent from `gate-processed`:
    historical unresolved claims normally already carry that gate label.
    """
    proc = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{REPO}/issues?state=open&per_page=100&sort=created&direction=asc",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:200]
        print(
            f"::error::gh issue enumeration failed (exit {proc.returncode}): {detail}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        issues = _flatten_issue_pages(json.loads(proc.stdout or "[]"))
    except (json.JSONDecodeError, ValueError) as exc:
        print(
            f"::error::could not parse complete issue enumeration: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    never, stranded = [], []
    for issue in issues:
        labels = {label["name"] for label in issue.get("labels", [])}
        if not gate.is_review_claim(issue.get("title") or ""):
            continue
        if "bounty-eligible" in labels:
            continue
        if "needs-human" in labels:
            if RETRY_MARKER_LABEL not in labels:
                stranded.append(issue["number"])
            continue
        if PROCESSED_LABEL not in labels:
            never.append(issue["number"])
    return sorted(never), sorted(stranded)


def _rotation_run_number():
    """Return the Actions run number used for the cap==1 class alternator."""
    raw = os.environ.get("GITHUB_RUN_NUMBER", "0")
    try:
        run_number = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"GITHUB_RUN_NUMBER must be an integer, got {raw!r}"
        ) from exc
    if run_number < 0:
        raise ValueError("GITHUB_RUN_NUMBER must be >= 0")
    return run_number


def select_batch(never, stranded, max_per_run, run_number):
    """Select a bounded batch with hard cross-class liveness.

    For cap >= 2, whenever both queues are non-empty at least one slot is
    reserved for each class. Retry claims use up to one quarter of the batch
    by default; unused capacity spills to the other class. For cap == 1 the
    run number alternates which class gets the sole slot.

    Within the stranded class, durable RETRY_MARKER_LABEL state provides
    progress across runs: selected claims are marked before adjudication and
    therefore leave the retryable queue even if they remain unresolved.
    Queue growth cannot re-phase a claim behind an ephemeral modulo cursor.
    """
    if max_per_run <= 0:
        raise ValueError("MAX_PER_RUN must be > 0")
    if run_number < 0:
        raise ValueError("run_number must be >= 0")

    never = sorted(never)
    stranded = sorted(stranded)
    if not never and not stranded:
        return [], []
    if not never:
        return [], stranded[:max_per_run]
    if not stranded:
        return never[:max_per_run], []

    if max_per_run == 1:
        return (
            (never[:1], [])
            if run_number % 2 == 0
            else ([], stranded[:1])
        )

    retry_budget = min(len(stranded), max(1, max_per_run // 4))
    new_budget = min(len(never), max_per_run - retry_budget)
    selected_new = never[:new_budget]
    selected_retry = stranded[:retry_budget]

    remaining = max_per_run - len(selected_new) - len(selected_retry)
    if remaining:
        more_new = never[len(selected_new): len(selected_new) + remaining]
        selected_new.extend(more_new)
        remaining -= len(more_new)
    if remaining:
        selected_retry.extend(
            stranded[len(selected_retry): len(selected_retry) + remaining]
        )
    return selected_new, selected_retry


def ensure_retry_marker_label():
    """Create/update the durable scheduling label before any retry attempt."""
    proc = subprocess.run(
        [
            "gh",
            "label",
            "create",
            RETRY_MARKER_LABEL,
            "--repo",
            REPO,
            "--color",
            "5319e7",
            "--description",
            "Automatic PR-review gate backfill retry attempted for this scheduler version",
            "--force",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:200]
        print(
            f"::error::could not ensure retry marker label "
            f"{RETRY_MARKER_LABEL!r}: {detail}",
            file=sys.stderr,
        )
        return False
    return True


def mark_retry_attempt(number):
    """Persist retry scheduling progress before running the gate.

    The marker is not a verdict. Writing it before adjudication is deliberate:
    a claim whose gate attempt repeatedly fails must not pin every later retry
    behind itself. The workflow goes red on that failure, while later claims
    remain able to advance on subsequent scheduled runs. Bumping the marker
    version reopens all still-needs-human claims for a later repair pass.
    """
    proc = subprocess.run(
        [
            "gh",
            "issue",
            "edit",
            str(number),
            "--repo",
            REPO,
            "--add-label",
            RETRY_MARKER_LABEL,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:200]
        print(
            f"::warning::could not persist retry marker on #{number}: {detail}"
        )
        return False
    return True


def adjudicate(number, retry=False):
    env = {**os.environ, "ISSUE_NUMBER": str(number)}
    if retry:
        env["RETRY_NEEDS_HUMAN"] = "1"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "pr_review_gate.py")],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    ok = result.returncode == 0
    if not ok:
        print(
            f"::warning::gate failed on #{number}: "
            f"{(result.stderr or '').strip()[:200]}"
        )
    return ok


def main():
    try:
        run_number = _rotation_run_number()
        if MAX_PER_RUN <= 0:
            raise ValueError("MAX_PER_RUN must be > 0")
    except ValueError as exc:
        print(
            f"::error::invalid backfill scheduling configuration: {exc}",
            file=sys.stderr,
        )
        return 2

    gate = _load_gate()
    never, stranded = list_unprocessed(gate)
    total = len(never) + len(stranded)
    batch_new, batch_retry = select_batch(
        never, stranded, MAX_PER_RUN, run_number
    )
    print(
        f"gate-backfill: {len(never)} never-adjudicated, "
        f"{len(stranded)} retryable needs-human; processing "
        f"{len(batch_new)}+{len(batch_retry)} "
        f"(run={run_number}, retry-marker={RETRY_MARKER_LABEL})"
    )

    done = 0
    failures = 0
    for number in batch_new:
        if adjudicate(number):
            done += 1
        else:
            failures += 1

    if batch_retry and not ensure_retry_marker_label():
        failures += len(batch_retry)
    else:
        for number in batch_retry:
            if not mark_retry_attempt(number):
                failures += 1
                continue
            if adjudicate(number, retry=True):
                done += 1
            else:
                failures += 1

    processed = len(batch_new) + len(batch_retry)
    remaining = total - processed
    print(f"gate-backfill: adjudicated {done}/{processed}")
    if remaining > 0:
        print(
            f"::notice::{remaining} claims still pending "
            f"(MAX_PER_RUN={MAX_PER_RUN}); reserved-class scheduling "
            "and durable retry markers advance future runs."
        )

    if failures:
        print(
            f"::error::{failures} of {processed} selected claims failed "
            "adjudication or retry-progress persistence"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
