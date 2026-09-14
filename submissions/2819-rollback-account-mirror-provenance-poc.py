#!/usr/bin/env python3
"""Reproducer for RustChain #2819: rollback_genesis leaves stale mirror provenance.

Run from a clean checkout of Scottcjn/Rustchain pinned to:
  aa584b344a766f6c0f8613ba7198d1cc7ffbae35

Example:
  RUSTCHAIN_ROOT=/path/to/Rustchain python3 2819-rollback-account-mirror-provenance-poc.py

The final assertion is expected to fail on the pinned revision.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

PINNED_MAIN = "aa584b344a766f6c0f8613ba7198d1cc7ffbae35"
ADMIN_KEY = "2819-local-regression-key"
WALLET = "RTC" + "1" * 40


def main() -> int:
    root = Path(os.environ.get("RUSTCHAIN_ROOT", ".")).resolve()
    node_dir = root / "node"
    if not (node_dir / "utxo_genesis_migration.py").is_file():
        raise SystemExit(
            "Set RUSTCHAIN_ROOT to a checkout of Scottcjn/Rustchain at " + PINNED_MAIN
        )

    sys.path.insert(0, str(node_dir))
    from utxo_genesis_migration import migrate, rollback_genesis

    fd, db_path = tempfile.mkstemp(prefix="rtc-2819-", suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE balances (miner_id TEXT PRIMARY KEY, amount_i64 INTEGER NOT NULL)"
        )
        # Account model uses 1e6 units per RTC. One RTC is enough to create one
        # deterministic genesis box plus one account_mirror_boxes provenance row.
        conn.execute(
            "INSERT INTO balances (miner_id, amount_i64) VALUES (?, ?)",
            (WALLET, 1_000_000),
        )
        conn.commit()
        conn.close()

        result = migrate(db_path)
        assert "error" not in result, result

        conn = sqlite3.connect(db_path)
        before = {
            "boxes": conn.execute("SELECT COUNT(*) FROM utxo_boxes").fetchone()[0],
            "genesis_txs": conn.execute(
                "SELECT COUNT(*) FROM utxo_transactions WHERE tx_type='genesis'"
            ).fetchone()[0],
            "mirror_rows": conn.execute(
                "SELECT COUNT(*) FROM account_mirror_boxes"
            ).fetchone()[0],
        }
        conn.close()
        print("before rollback:", before)
        assert before == {"boxes": 1, "genesis_txs": 1, "mirror_rows": 1}

        os.environ["RC_ADMIN_KEY"] = ADMIN_KEY
        deleted = rollback_genesis(db_path, admin_key=ADMIN_KEY)
        print("rollback deleted boxes:", deleted)

        conn = sqlite3.connect(db_path)
        after = {
            "boxes": conn.execute("SELECT COUNT(*) FROM utxo_boxes").fetchone()[0],
            "genesis_txs": conn.execute(
                "SELECT COUNT(*) FROM utxo_transactions WHERE tx_type='genesis'"
            ).fetchone()[0],
            "mirror_rows": conn.execute(
                "SELECT COUNT(*) FROM account_mirror_boxes"
            ).fetchone()[0],
        }
        stale = conn.execute(
            "SELECT box_id, account_wallet, value_nrtc, created_epoch "
            "FROM account_mirror_boxes"
        ).fetchall()
        conn.close()

        print("after rollback:", after)
        print("stale provenance rows:", stale)

        assert after["boxes"] == 0
        assert after["genesis_txs"] == 0
        # Regression assertion: a complete rollback should also remove the
        # provenance rows that belong to the deleted genesis boxes.
        assert after["mirror_rows"] == 0, (
            "BUG: rollback_genesis deleted genesis boxes/transactions but left "
            f"{after['mirror_rows']} account_mirror_boxes row(s)"
        )
        return 0
    finally:
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
