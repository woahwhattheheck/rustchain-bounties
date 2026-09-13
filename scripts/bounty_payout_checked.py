#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the payout sweep and fail the job if any transfer was detected failed.

`scripts/bounty_payout.py` deliberately continues after an individual transfer
failure so independent eligible claims still get a chance to pay. Historically
that also meant the process fell off the end with status 0. This runner keeps
that continue-the-sweep behaviour while converting the existing machine-readable
`::warning::pay failed #<n>:` records into a non-zero final status.

The child is the fresh-authorization launcher, which executes the legacy payout
sweep only after inserting its fail-closed final GitHub authorization fence at
the money-movement boundary.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_FAILED_TRANSFER = re.compile(r"^::warning::pay failed #(\d+):")


def run_checked(command: list[str], *, popen=subprocess.Popen) -> int:
    """Stream child output, retain failed claim ids, and return truthful status."""
    process = popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    failed_claims: list[str] = []
    seen: set[str] = set()
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        match = _FAILED_TRANSFER.match(line.rstrip("\n"))
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            failed_claims.append(match.group(1))

    child_status = process.wait()
    if child_status != 0:
        return child_status
    if failed_claims:
        rendered = ", ".join(f"#{claim}" for claim in failed_claims)
        print(
            f"::error::bounty payout completed with {len(failed_claims)} "
            f"failed transfer(s): {rendered}"
        )
        return 1
    return 0


def main() -> int:
    payout = Path(__file__).with_name("bounty_payout_fresh_auth.py")
    return run_checked([sys.executable, str(payout)])


if __name__ == "__main__":
    raise SystemExit(main())
