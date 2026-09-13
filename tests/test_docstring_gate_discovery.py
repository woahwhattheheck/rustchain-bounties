# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import textwrap


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "scripts" / "docstring_gate_discovery.sh"


def _stub_gh(tmp_path: Path, *, fail_match: str = "") -> Path:
    gh = tmp_path / "gh"
    gh.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import sys

            args = " ".join(sys.argv[1:])
            fail_match = {fail_match!r}
            if fail_match and fail_match in args:
                print("simulated provider failure", file=sys.stderr)
                raise SystemExit(17)

            if "label:awaiting-merge" in args and "-label:awaiting-merge" not in args:
                print("42")
                print("7")
            else:
                print("13")
                print("7")
            """
        )
    )
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    return gh


def _run(tmp_path: Path, *, fail_match: str = "") -> subprocess.CompletedProcess[str]:
    _stub_gh(tmp_path, fail_match=fail_match)
    env = os.environ.copy()
    env["GH_REPO"] = "acme/bounties"
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        ["bash", str(DISCOVERY)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_discovery_returns_sorted_unique_candidates(tmp_path):
    result = _run(tmp_path)

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["7", "13", "42"]
    assert result.stderr == ""


def test_awaiting_merge_search_failure_is_not_empty_success(tmp_path):
    result = _run(tmp_path, fail_match="label:awaiting-merge")

    assert result.returncode != 0
    assert result.stdout == ""
    assert "candidate discovery failed" in result.stderr
    assert "simulated provider failure" not in result.stderr


def test_fresh_search_failure_is_not_empty_success(tmp_path):
    result = _run(tmp_path, fail_match="-label:bounty-eligible")

    assert result.returncode != 0
    assert result.stdout == ""
    assert "candidate discovery failed" in result.stderr
    assert "simulated provider failure" not in result.stderr


def test_workflow_has_no_fail_open_candidate_search_fallback():
    workflow = (ROOT / ".github" / "workflows" / "docstring-gate.yml").read_text()

    assert "2>/dev/null || true" not in workflow
    assert "if ! candidates=$(bash scripts/docstring_gate_discovery.sh); then" in workflow
    assert "candidate discovery failed; no zero-work success will be reported" in workflow
