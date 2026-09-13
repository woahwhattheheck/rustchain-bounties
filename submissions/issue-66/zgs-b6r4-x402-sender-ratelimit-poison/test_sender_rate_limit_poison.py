import time
import unittest

_rate_limits = {}


def current_handle(proof, verify_payment_proof, rate_limit=3, now=None):
    """Faithful extraction of current wrapper order after proof extraction."""
    sender = proof['sender']
    now = time.time() if now is None else now
    minute_key = f"{sender}:{int(now // 60)}"
    if minute_key in _rate_limits:
        if _rate_limits[minute_key] >= rate_limit:
            return 429
        _rate_limits[minute_key] += 1
    else:
        _rate_limits[minute_key] = 1
    if not verify_payment_proof(proof):
        return 402
    return 200


def patched_handle(proof, verify_payment_proof, rate_limit=3, now=None):
    """Proposed order: authenticate/verify before charging sender quota."""
    if not verify_payment_proof(proof):
        return 402
    sender = proof['sender']
    now = time.time() if now is None else now
    minute_key = f"{sender}:{int(now // 60)}"
    if minute_key in _rate_limits:
        if _rate_limits[minute_key] >= rate_limit:
            return 429
        _rate_limits[minute_key] += 1
    else:
        _rate_limits[minute_key] = 1
    return 200


def verifier(proof):
    # The attacker can copy the public sender identifier but cannot forge the
    # victim's Ed25519 signature. This oracle models verify_payment_proof().
    return proof['signature'] == 'valid-victim-signature'


class TestSenderRateLimitPoison(unittest.TestCase):
    NOW = 1_800_000_000.0

    def setUp(self):
        _rate_limits.clear()

    def forged(self):
        return {'sender': 'victim-public-key', 'signature': 'invalid-attacker-signature'}

    def victim(self):
        return {'sender': 'victim-public-key', 'signature': 'valid-victim-signature'}

    def test_current_order_lets_forgery_exhaust_victim_bucket(self):
        self.assertEqual(
            [current_handle(self.forged(), verifier, now=self.NOW) for _ in range(3)],
            [402, 402, 402],
        )
        self.assertEqual(current_handle(self.victim(), verifier, now=self.NOW), 429)
        self.assertEqual(_rate_limits['victim-public-key:30000000'], 3)

    def test_patched_order_does_not_charge_forged_sender(self):
        self.assertEqual(
            [patched_handle(self.forged(), verifier, now=self.NOW) for _ in range(3)],
            [402, 402, 402],
        )
        self.assertEqual(patched_handle(self.victim(), verifier, now=self.NOW), 200)
        self.assertEqual(_rate_limits['victim-public-key:30000000'], 1)

    def test_patched_order_preserves_limit_for_verified_sender(self):
        self.assertEqual(
            [patched_handle(self.victim(), verifier, rate_limit=2, now=self.NOW) for _ in range(3)],
            [200, 200, 429],
        )


if __name__ == '__main__':
    unittest.main()
