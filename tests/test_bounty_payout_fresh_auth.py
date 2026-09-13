from pathlib import Path
import json
import unittest

from scripts.bounty_payout_fresh_auth import build_fresh_source


REPO_ROOT = Path(__file__).resolve().parents[1]
PAYOUT = REPO_ROOT / "scripts" / "bounty_payout.py"


_FIXTURE = r'''
import json
transfers=[]
def gh(args):
    return json.dumps(AUTH_NOW)
def _comment_author_login(c):
    a=c.get("author") if isinstance(c,dict) else None
    return ((a or {}).get("login"), a)
def _is_trusted(login):
    return bool(login) and login.lower() == "scottcjn"
def transfer(wallet,memo,idem,amount):
    transfers.append((wallet,memo,idem,amount))
    return True, {"ok": True}
for i in [{"number": 73, "labels": [{"name": "bounty-eligible"}]}]:
    num=str(i["number"])
    labels={l["name"] for l in i.get("labels",[])}
    coms=[]
    eligible=("bounty-eligible" in labels) or any(
        "Verified eligible" in (c.get("body") or "")
        and _is_trusted(_comment_author_login(c)[0])
        for c in coms)
    if not eligible:
        continue
    wallet="claimant"
    memo=f"claim #{num}"
    idem=f"claim-{num}"
    amount=3.0
    ok,resp=transfer(wallet,memo,idem,amount)
'''


def run_fixture(auth_now):
    namespace={"AUTH_NOW": auth_now}
    exec(compile(build_fresh_source(_FIXTURE), "<fresh-auth-fixture>", "exec"), namespace, namespace)
    return namespace["transfers"]


class FreshPayoutAuthorizationTests(unittest.TestCase):
    def test_real_payout_source_has_one_transformable_transfer(self):
        source=PAYOUT.read_text(encoding="utf-8")
        patched=build_fresh_source(source)
        self.assertNotEqual(source, patched)
        compile(patched, str(PAYOUT), "exec")
        self.assertIn("payout eligibility was revoked before transfer", patched)

    def test_revoked_label_blocks_transfer(self):
        self.assertEqual(
            run_fixture({"state": "OPEN", "labels": [], "comments": []}),
            [],
        )

    def test_closed_issue_blocks_transfer_even_if_label_remains(self):
        self.assertEqual(
            run_fixture({
                "state": "CLOSED",
                "labels": [{"name": "bounty-eligible"}],
                "comments": [],
            }),
            [],
        )

    def test_current_label_preserves_transfer(self):
        transfers=run_fixture({
            "state": "OPEN",
            "labels": [{"name": "bounty-eligible"}],
            "comments": [],
        })
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0][0], "claimant")

    def test_current_trusted_verified_comment_preserves_transfer(self):
        transfers=run_fixture({
            "state": "OPEN",
            "labels": [],
            "comments": [{
                "body": "Verified eligible — maintainer review complete",
                "author": {"login": "scottcjn"},
            }],
        })
        self.assertEqual(len(transfers), 1)

    def test_untrusted_verified_comment_does_not_authorize_transfer(self):
        self.assertEqual(
            run_fixture({
                "state": "OPEN",
                "labels": [],
                "comments": [{
                    "body": "Verified eligible",
                    "author": {"login": "attacker"},
                }],
            }),
            [],
        )

    def test_malformed_authorization_response_fails_closed(self):
        with self.assertRaises(RuntimeError):
            run_fixture({"state": "OPEN", "labels": None, "comments": []})

    def test_source_drift_refuses_unfenced_execution(self):
        with self.assertRaisesRegex(RuntimeError, "found 0"):
            build_fresh_source("print('different payout implementation')\n")
        with self.assertRaisesRegex(RuntimeError, "found 2"):
            build_fresh_source(_FIXTURE + "\n" + _FIXTURE)


if __name__ == "__main__":
    unittest.main()
