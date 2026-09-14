#!/usr/bin/env python3
"""Local-only PoC for rustchain-bounties #2819 mirror balance mismatch.

Run from a Scottcjn/Rustchain checkout pinned to:
  aa584b344a766f6c0f8613ba7198d1cc7ffbae35

Example:
  PYTHONPATH=node python submissions/2819-mirror-balance-spendability-mismatch-poc.py

No network access is used. The script creates and deletes a temporary SQLite DB.
"""

import os
import sqlite3
import tempfile

from utxo_db import UNIT, UtxoDB, address_to_proposition


def main() -> None:
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = handle.name
    handle.close()

    try:
        db = UtxoDB(db_path)
        db.init_tables()

        address = "RTC" + "a" * 40
        box_id = "11" * 32
        tx_id = "22" * 32
        value_nrtc = 25 * UNIT

        db.add_box({
            "box_id": box_id,
            "value_nrtc": value_nrtc,
            "proposition": address_to_proposition(address),
            "owner_address": address,
            "creation_height": 1,
            "transaction_id": tx_id,
            "output_index": 0,
        })

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                CREATE TABLE account_mirror_boxes (
                    box_id TEXT PRIMARY KEY,
                    account_wallet TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO account_mirror_boxes (box_id, account_wallet) VALUES (?, ?)",
                (box_id, address),
            )
            conn.commit()
        finally:
            conn.close()

        # These are the methods backing /utxo/balance and /utxo/boxes.
        reported_balance = db.get_balance(address)
        reported_count = db.count_unspent_for_address(address)
        listed = db.get_unspent_for_address(address)

        # This is the candidate source used by /utxo/transfer.
        candidates = db.get_coin_select_candidates(address)
        spendable_total = sum(row["value_nrtc"] for row in candidates)

        mismatch = (
            reported_balance > 0
            and reported_count > 0
            and len(listed) > 0
            and spendable_total == 0
            and len(candidates) == 0
        )

        print(f"reported_balance_nrtc={reported_balance}")
        print(f"reported_utxo_count={reported_count}")
        print(f"listed_box_count={len(listed)}")
        print(f"spendable_candidate_count={len(candidates)}")
        print(f"spendable_candidate_total_nrtc={spendable_total}")
        print(f"mismatch={mismatch}")

        assert reported_balance == 25 * UNIT
        assert reported_count == 1
        assert len(listed) == 1
        assert candidates == []
        assert mismatch
    finally:
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
