#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("packet_verify", HERE / "verify.py")
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class PacketVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("verify.py", "receipt.json", "bottube-x402-wallet-json.patch"):
            shutil.copy2(HERE / name, self.root / name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_canonical_packet_passes(self) -> None:
        result = VERIFY.verify(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(result["head"], VERIFY.EXPECTED_HEAD)
        self.assertFalse(result["authority"]["award_observed"])

    def test_patch_byte_tamper_fails(self) -> None:
        path = self.root / VERIFY.PATCH_NAME
        path.write_bytes(path.read_bytes() + b"\n# tamper\n")
        with self.assertRaisesRegex(VERIFY.VerificationError, "digest mismatch"):
            VERIFY.verify(self.root)

    def test_extra_diff_path_fails_even_with_rebound_digest(self) -> None:
        path = self.root / VERIFY.PATCH_NAME
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\ndiff --git a/extra.py b/extra.py\n--- a/extra.py\n+++ b/extra.py\n",
            encoding="utf-8",
        )
        receipt_path = self.root / VERIFY.RECEIPT_NAME
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        import hashlib

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        receipt["artifact"]["sha256"] = digest
        receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        old = VERIFY.EXPECTED_PATCH_SHA256
        try:
            VERIFY.EXPECTED_PATCH_SHA256 = digest
            with self.assertRaisesRegex(VERIFY.VerificationError, "path set/order mismatch|additional diff"):
                VERIFY.verify(self.root)
        finally:
            VERIFY.EXPECTED_PATCH_SHA256 = old

    def test_award_minting_fails(self) -> None:
        path = self.root / VERIFY.RECEIPT_NAME
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["authority"]["award_observed"] = True
        path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(VERIFY.VerificationError, "award_observed"):
            VERIFY.verify(self.root)

    def test_duplicate_json_key_fails(self) -> None:
        path = self.root / VERIFY.RECEIPT_NAME
        raw = path.read_text(encoding="utf-8")
        raw = raw.replace(
            '"schema": "rustchain-bounty-evidence/v1",',
            '"schema": "rustchain-bounty-evidence/v1",'
            '"schema": "rustchain-bounty-evidence/v1",',
            1,
        )
        path.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(VERIFY.VerificationError, "duplicate JSON key"):
            VERIFY.verify(self.root)


if __name__ == "__main__":
    unittest.main()
