#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local reproduction for RustChain bounty #2819.

Run from a Scottcjn/Rustchain checkout (or pass --node-dir) at commit
 aa584b344a766f6c0f8613ba7198d1cc7ffbae35.

The default 100 rows is intentionally modest. This creates only a temporary
SQLite database and does not contact a node or network.
"""

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100,
                        help="pending transactions to populate (default: 100)")
    parser.add_argument("--node-dir", default="node",
                        help="path containing utxo_db.py (default: ./node)")
    return parser.parse_args()


def metadata_blob(size=7000):
    return "x" * size


def make_outputs(owner_prefix, blob, count=18):
    """Build valid outputs that push normalized tx JSON near the 256 KiB cap."""
    return [
        {
            "address": f"{owner_prefix}-{i:02d}",
            "value_nrtc": 1_000,
            "tokens_json": json.dumps([blob], separators=(",", ":")),
            "registers_json": json.dumps({"R4": blob}, separators=(",", ":")),
        }
        for i in range(count)
    ]


def mint(db, address, value_nrtc, height):
    return db.apply_transaction(
        {
            "tx_type": "mining_reward",
            "inputs": [],
            "outputs": [{"address": address, "value_nrtc": value_nrtc}],
            "fee_nrtc": 0,
            "timestamp": 1_700_000_000 + height,
            "_allow_minting": True,
        },
        block_height=height,
    )


def main():
    args = parse_args()
    if args.rows < 1:
        raise SystemExit("--rows must be positive")

    node_dir = os.path.abspath(args.node_dir)
    sys.path.insert(0, node_dir)
    try:
        from utxo_db import UtxoDB, UNIT, MAX_TX_DATA_JSON_BYTES
    except ImportError as exc:
        raise SystemExit(
            f"Could not import utxo_db from {node_dir}; run from a RustChain "
            "checkout or pass --node-dir"
        ) from exc

    blob = metadata_blob()
    outputs_per_tx = 18
    source_value = outputs_per_tx * 1_000

    tmp = tempfile.NamedTemporaryFile(prefix="rc2819-", suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        db = UtxoDB(db_path)
        db.init_tables()

        print(f"Populating {args.rows} valid pending transactions...")
        first_stored_size = None
        for i in range(args.rows):
            source = f"src-{i:06d}"
            height = i + 1
            if not mint(db, source, source_value, height):
                raise RuntimeError(f"mint failed at row {i}")
            boxes = db.get_unspent_for_address(source)
            if len(boxes) != 1:
                raise RuntimeError(f"expected one source box at row {i}")

            tx = {
                "tx_id": f"probe-{i:06d}",
                "tx_type": "transfer",
                "inputs": [{"box_id": boxes[0]["box_id"]}],
                "outputs": make_outputs(f"sink-{i:06d}", blob, outputs_per_tx),
                "fee_nrtc": 0,
                "timestamp": 1_800_000_000 + i,
            }
            if not db.mempool_add(tx):
                raise RuntimeError(f"mempool_add failed at row {i}")

            if i == 0:
                conn = sqlite3.connect(db_path)
                try:
                    first_stored_size = conn.execute(
                        "SELECT LENGTH(tx_data_json) FROM utxo_mempool WHERE tx_id = ?",
                        (tx["tx_id"],),
                    ).fetchone()[0]
                finally:
                    conn.close()
                if first_stored_size > MAX_TX_DATA_JSON_BYTES:
                    raise RuntimeError("stored row unexpectedly exceeds configured cap")

        conn = sqlite3.connect(db_path)
        try:
            count, total_bytes = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(LENGTH(tx_data_json)), 0) "
                "FROM utxo_mempool"
            ).fetchone()
        finally:
            conn.close()

        print(f"mempool rows:             {count:,}")
        print(f"first tx_data_json bytes: {first_stored_size:,}")
        print(f"total tx_data_json bytes: {total_bytes:,} ({total_bytes / 1048576:.2f} MiB)")
        print(f"configured per-row cap:   {MAX_TX_DATA_JSON_BYTES:,} bytes")

        # A separate ordinary successful spend. Its input is unrelated to every
        # pending transaction above. apply_transaction() nevertheless invokes
        # _evict_stale_data_input_txs(), which parses the full unrelated pool to
        # discover whether any tx_data_json contains a matching data_input.
        trigger_height = args.rows + 10
        if not mint(db, "trigger-src", UNIT, trigger_height):
            raise RuntimeError("trigger mint failed")
        trigger_box = db.get_unspent_for_address("trigger-src")[0]
        trigger_tx = {
            "tx_type": "transfer",
            "inputs": [{"box_id": trigger_box["box_id"], "spending_proof": "local-test"}],
            "outputs": [{"address": "trigger-dst", "value_nrtc": UNIT}],
            "fee_nrtc": 0,
            "timestamp": 1_900_000_000,
        }

        start = time.perf_counter()
        ok = db.apply_transaction(trigger_tx, block_height=trigger_height + 1)
        elapsed = time.perf_counter() - start
        if not ok:
            raise RuntimeError("ordinary trigger spend failed")

        print(f"ordinary spend elapsed:   {elapsed:.6f} s")
        print("The pending rows are unrelated to the spend; their JSON is still scanned.")
        print("Repeat with increasing --rows in an isolated checkout to observe linear growth.")

    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
