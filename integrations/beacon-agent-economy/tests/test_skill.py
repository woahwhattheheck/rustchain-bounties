import hashlib
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from beacon_agent_economy import (
    PRIVATE_KEY_ENV,
    AgentEconomyError,
    AgentEconomyHTTPError,
    BeaconAgentEconomySkill,
    canonical_create_message,
)


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = {} if body is None else body
        self.text = text

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeSession:
    def __init__(self, responses=None):
        self.headers = {}
        self.calls = []
        self.responses = list(
            responses or [FakeResponse(body={"ok": True})]
        )

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse(body={"ok": True})


PRIVATE_KEY = "00" * 32


def expected_wallet(private_key_hex=PRIVATE_KEY):
    key = Ed25519PrivateKey.from_private_bytes(
        bytes.fromhex(private_key_hex)
    )
    pub = key.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw
    )
    return "RTC" + hashlib.sha256(pub).hexdigest()[:40]


class BeaconAgentEconomyTests(unittest.TestCase):
    def make_skill(self, session=None, environ=None):
        return BeaconAgentEconomySkill(
            session=session or FakeSession(),
            environ=(
                environ
                if environ is not None
                else {PRIVATE_KEY_ENV: PRIVATE_KEY}
            ),
            nonce_factory=lambda: (
                "00112233445566778899aabbccddeeff"
            ),
        )

    def test_action_schema_never_exposes_private_key(self):
        schemas = self.make_skill().action_schemas()
        self.assertIn("post_job", schemas)
        properties = json.dumps(
            schemas["post_job"].get("properties", {})
        ).lower()
        self.assertNotIn("private_key_hex", properties)
        self.assertNotIn(PRIVATE_KEY_ENV.lower(), properties)

    def test_canonical_create_message_is_sorted_and_minified(self):
        self.assertEqual(
            canonical_create_message(
                "RTCabc", "CODE", 5.0, "nonce"
            ),
            (
                b'{"action":"agent_post_job","category":"code",'
                b'"nonce":"nonce","poster":"RTCabc",'
                b'"reward_rtc":5.0}'
            ),
        )

    def test_post_job_reads_key_from_environment_and_never_sends_it(
        self,
    ):
        session = FakeSession(
            [FakeResponse(body={"job_id": "job_1"})]
        )
        skill = self.make_skill(session=session)
        result = skill.post_job(
            title="Review a Beacon patch",
            description=(
                "Review the Agent Economy integration "
                "and return concise findings."
            ),
            reward_rtc=5,
            category="code",
            tags=["beacon", "rip-302"],
        )
        self.assertEqual(result["job_id"], "job_1")
        method, url, kwargs = session.calls[-1]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/agent/jobs"))
        body = kwargs["json"]
        self.assertEqual(
            body["poster_wallet"], expected_wallet()
        )
        self.assertEqual(
            body["nonce"],
            "00112233445566778899aabbccddeeff",
        )
        self.assertEqual(len(body["poster_pubkey"]), 64)
        self.assertEqual(len(body["poster_sig"]), 128)
        self.assertNotIn(
            "private_key", json.dumps(body).lower()
        )
        self.assertNotIn(PRIVATE_KEY, json.dumps(body))

    def test_post_job_rejects_wallet_signer_mismatch_before_http(
        self,
    ):
        session = FakeSession()
        skill = self.make_skill(session=session)
        with self.assertRaisesRegex(
            AgentEconomyError, "does not match"
        ):
            skill.post_job(
                title="Review a Beacon patch",
                description=(
                    "Review the Agent Economy integration "
                    "and return concise findings."
                ),
                reward_rtc=5,
                poster_wallet="RTC" + "0" * 40,
            )
        self.assertEqual(session.calls, [])

    def test_missing_signing_key_is_explicit_and_pre_http(self):
        session = FakeSession()
        skill = self.make_skill(
            session=session, environ={}
        )
        with self.assertRaisesRegex(
            AgentEconomyError, PRIVATE_KEY_ENV
        ):
            skill.post_job(
                title="Review a Beacon patch",
                description=(
                    "Review the Agent Economy integration "
                    "and return concise findings."
                ),
                reward_rtc=5,
            )
        self.assertEqual(session.calls, [])

    def test_browse_get_claim_and_reputation_routes_encode_ids(
        self,
    ):
        session = FakeSession(
            [
                FakeResponse(body={"jobs": []}),
                FakeResponse(body={"job": {}}),
                FakeResponse(body={"claimed": True}),
                FakeResponse(body={"trust_score": 100}),
            ]
        )
        skill = self.make_skill(session=session)
        skill.browse_jobs(
            category="Code",
            min_reward=2.5,
            limit=25,
            offset=50,
        )
        skill.get_job("job/a b")
        skill.claim_job("job/a b", "RTCworker")
        skill.get_reputation("RTC/a b")

        self.assertEqual(
            session.calls[0][2]["params"]["category"],
            "code",
        )
        self.assertEqual(
            session.calls[0][2]["params"]["min_reward"],
            2.5,
        )
        self.assertTrue(
            session.calls[1][1].endswith(
                "/agent/jobs/job%2Fa%20b"
            )
        )
        self.assertTrue(
            session.calls[2][1].endswith(
                "/agent/jobs/job%2Fa%20b/claim"
            )
        )
        self.assertEqual(
            session.calls[2][2]["json"],
            {"worker_wallet": "RTCworker"},
        )
        self.assertTrue(
            session.calls[3][1].endswith(
                "/agent/reputation/RTC%2Fa%20b"
            )
        )

    def test_deliver_requires_evidence_before_http(self):
        session = FakeSession()
        skill = self.make_skill(session=session)
        with self.assertRaisesRegex(
            AgentEconomyError,
            "deliverable_url or result_summary",
        ):
            skill.deliver_job(
                "job_1",
                "RTCworker",
                deliverable_hash="abc",
            )
        self.assertEqual(session.calls, [])

    def test_http_error_preserves_status_code_and_body(self):
        body = {
            "code": "job_not_open",
            "error": "job is already claimed",
            "detail": "x",
        }
        session = FakeSession(
            [FakeResponse(status_code=409, body=body)]
        )
        skill = self.make_skill(session=session)
        with self.assertRaises(
            AgentEconomyHTTPError
        ) as ctx:
            skill.claim_job("job_1", "RTCworker")
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual(
            ctx.exception.code, "job_not_open"
        )
        self.assertEqual(ctx.exception.body, body)

    def test_invoke_dispatches_allowlisted_skill_actions(self):
        session = FakeSession(
            [FakeResponse(body={"stats": "ok"})]
        )
        skill = self.make_skill(session=session)
        self.assertEqual(
            skill.invoke("get_stats"),
            {"stats": "ok"},
        )
        with self.assertRaisesRegex(
            AgentEconomyError, "unknown"
        ):
            skill.invoke(
                "accept_and_release_funds"
            )


if __name__ == "__main__":
    unittest.main()
