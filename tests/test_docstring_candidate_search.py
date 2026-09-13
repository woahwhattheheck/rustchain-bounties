#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression tests for fail-closed scheduled docstring candidate discovery."""

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "docstring_candidate_search.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "docstring-gate.yml"


class CandidateSearchTests(unittest.TestCase):
    def run_search(self, mode, gh_body, *, error_bytes="2000"):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_gh = tmp_path / "gh"
            fake_gh.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(gh_body), encoding="utf-8")
            fake_gh.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "GH_REPO": "owner/rustchain-bounties",
                    "PATH": f"{tmp}{os.pathsep}{env['PATH']}",
                    "DOCSTRING_DISCOVERY_TIMEOUT_SECONDS": "5",
                    "DOCSTRING_DISCOVERY_ERROR_BYTES": error_bytes,
                    "GH_ARGS_FILE": str(tmp_path / "args"),
                }
            )
            result = subprocess.run(
                ["bash", str(SCRIPT), mode],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            args_file = tmp_path / "args"
            args = args_file.read_text(encoding="utf-8") if args_file.exists() else ""
            return result, args

    def test_held_search_failure_is_nonzero(self):
        result, _ = self.run_search(
            "held",
            """
            echo 'simulated GitHub outage' >&2
            exit 17
            """,
        )
        self.assertEqual(result.returncode, 17)
        self.assertEqual(result.stdout, "")
        self.assertIn("candidate set is unknown", result.stderr)
        self.assertIn("simulated GitHub outage", result.stderr)

    def test_fresh_search_failure_is_nonzero(self):
        result, _ = self.run_search(
            "fresh",
            """
            echo 'simulated rate limit' >&2
            exit 22
            """,
        )
        self.assertEqual(result.returncode, 22)
        self.assertEqual(result.stdout, "")
        self.assertIn("fresh GitHub search exited 22", result.stderr)

    def test_empty_success_stays_empty_and_green(self):
        for mode in ("held", "fresh"):
            with self.subTest(mode=mode):
                result, _ = self.run_search(mode, "exit 0")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "\n")
                self.assertEqual(result.stderr, "")

    def test_success_preserves_candidate_numbers(self):
        result, _ = self.run_search(
            "held",
            """
            printf '17\\n42\\n'
            """,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "17\n42\n")

    def test_queries_preserve_held_and_fresh_contracts(self):
        body = "printf '%s\\n' \"$*\" > \"$GH_ARGS_FILE\"\nexit 0"
        held, held_args = self.run_search("held", body)
        fresh, fresh_args = self.run_search("fresh", body)
        self.assertEqual(held.returncode, 0)
        self.assertEqual(fresh.returncode, 0)
        self.assertIn("search/issues", held_args)
        self.assertIn("label:awaiting-merge", held_args)
        self.assertIn("-label:bounty-eligible", fresh_args)
        self.assertIn("-label:awaiting-merge", fresh_args)
        self.assertIn("-label:needs-human", fresh_args)
        self.assertIn("docstring", fresh_args)

    def test_failure_diagnostic_is_bounded(self):
        result, _ = self.run_search(
            "held",
            """
            python3 - <<'PY' >&2
            print('x' * 10000)
            PY
            exit 19
            """,
            error_bytes="256",
        )
        self.assertEqual(result.returncode, 19)
        self.assertLess(len(result.stderr), 700)
        self.assertIn("bounded to 256 bytes", result.stderr)

    def test_workflow_uses_fail_closed_helper_for_both_queries(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("scripts/docstring_candidate_search.sh held", text)
        self.assertIn("scripts/docstring_candidate_search.sh fresh", text)
        self.assertNotIn("2>/dev/null || true", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
