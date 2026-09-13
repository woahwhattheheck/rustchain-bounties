from pathlib import Path
import re
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "confirm-pending.yml"


def confirmation_step() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "- name: Drain all past-void-window pending transfers"
    try:
        return text.split(marker, 1)[1]
    except IndexError as exc:
        raise AssertionError(f"missing confirmation workflow step: {marker}") from exc


class ConfirmPendingWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.step = confirmation_step()

    def assert_step_matches(self, pattern: str) -> None:
        self.assertIsNotNone(
            re.search(pattern, self.step, flags=re.DOTALL),
            msg=f"workflow step did not match required fail-closed contract: {pattern}",
        )

    def test_shell_fails_fast(self) -> None:
        self.assertIn("set -euo pipefail", self.step)

    def test_response_counters_are_validated(self) -> None:
        self.assertIn("not nonnegative_int(stale)", self.step)
        self.assertIn("not nonnegative_int(confirmed)", self.step)
        self.assertIn("measured is False", self.step)

    def test_zero_progress_with_stale_backlog_is_red(self) -> None:
        self.assert_step_matches(
            r'if \[ "\$confirmed" -eq 0 \]; then.*?Pending confirmation made no progress.*?exit 1'
        )

    def test_safety_cap_with_stale_backlog_is_red(self) -> None:
        self.assert_step_matches(
            r'if \[ "\$last_stale" -ne 0 \]; then.*?Pending confirmation safety cap exhausted.*?exit 1'
        )

    def test_success_message_asserts_zero_backlog(self) -> None:
        self.assertIn('stale backlog is zero', self.step)
        self.assertNotIn('no progress this iter; stopping', self.step)


if __name__ == "__main__":
    unittest.main()
