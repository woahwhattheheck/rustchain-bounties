#!/usr/bin/env python3
"""Reproduce the zero-output mining_reward block-slot liveness bug.

Usage:
    python3 2819-zero-output-mining-reward-slot-poisoning-poc.py /path/to/Rustchain

The checkout should be Scottcjn/Rustchain at
 aa584b344a766f6c0f8613ba7198d1cc7ffbae35
for the source revision audited by the accompanying report.
"""

import os
import sqlite3
import sys
import tempfile


if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} <Rustchain checkout>")

checkout = os.path.abspath(sys.argv[1])
node_dir = os.path.join(checkout, "node")
if not os.path.isfile(os.path.join(node_dir, "utxo_db.py")):
    raise SystemExit(f"missing {os.path.join(node_dir, 'utxo_db.py')}")

sys.path.insert(0, node_dir)
from utxo_db import UtxoDB, UNIT  # noqa: E402


fd, db_path = tempfile.mkstemp(prefix="rtc-zero-mint-", suffix=".db")
os.close(fd)

try:
    db = UtxoDB(db_path)
    db.init_tables()

    height = 424242
    empty_reward = {
        "tx_type": "mining_reward",
        "inputs": [],
        "outputs": [],
        "fee_nrtc": 0,
        "timestamp": 1_700_000_000,
        "_allow_minting": True,
    }

    first = db.apply_transaction(empty_reward, block_height=height)
    assert first is True, (
        "current bug not reproduced: zero-output mining_reward returned "
        f"{first!r}"
    )

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT tx_id, tx_type, outputs_json, block_height
            FROM utxo_transactions
            WHERE tx_type = 'mining_reward' AND block_height = ?
            """,
            (height,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, "empty reward was not persisted"
    assert row[1] == "mining_reward", row
    assert row[2] == "[]", row
    assert row[3] == height, row

    recipient = "RTC" + ("a" * 40)
    legitimate_reward = {
        "tx_type": "mining_reward",
        "inputs": [],
        "outputs": [{"address": recipient, "value_nrtc": UNIT}],
        "fee_nrtc": 0,
        "timestamp": 1_700_000_001,
        "_allow_minting": True,
    }

    second = db.apply_transaction(legitimate_reward, block_height=height)
    assert second is False, (
        "expected legitimate reward to be blocked by the consumed height slot, "
        f"got {second!r}"
    )
    assert db.get_balance(recipient) == 0, "legitimate reward unexpectedly landed"

    print(
        "REPRODUCED: empty authorized mining_reward consumed the only reward "
        f"slot for block {height}"
    )
finally:
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass
