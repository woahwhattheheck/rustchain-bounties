#!/usr/bin/env python3
"""Deterministic local reproduction for rustchain-bounties #2819.

Models the exact transfer_nonces schema plus reservation/monotonicity SQL used
by Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35. It shows
that the current successful path retains one row per accepted nonce forever,
while deleting superseded rows after success preserves stale-nonce rejection.
"""

import sqlite3

SCHEMA = """
CREATE TABLE transfer_nonces (
    from_address TEXT NOT NULL,
    nonce TEXT NOT NULL,
    used_at INTEGER NOT NULL,
    PRIMARY KEY (from_address, nonce)
)
"""

ADDRESS = "RTC0000000000000000000000000000000000000000"
N = 5000


def reserve_and_check(conn, nonce):
    conn.execute(
        "INSERT OR IGNORE INTO transfer_nonces "
        "(from_address, nonce, used_at) VALUES (?, ?, 0)",
        (ADDRESS, str(nonce)),
    )
    if conn.execute("SELECT changes()").fetchone()[0] != 1:
        conn.rollback()
        return False

    previous = conn.execute(
        "SELECT MAX(CAST(nonce AS INTEGER)) FROM transfer_nonces "
        "WHERE from_address = ? AND nonce != ?",
        (ADDRESS, str(nonce)),
    ).fetchone()[0]
    if previous is not None and int(previous) >= int(nonce):
        conn.rollback()
        return False
    return True


def current_success(conn, nonce):
    conn.execute("BEGIN")
    if not reserve_and_check(conn, nonce):
        return False
    conn.commit()
    return True


def bounded_success(conn, nonce):
    conn.execute("BEGIN")
    if not reserve_and_check(conn, nonce):
        return False
    conn.execute(
        "DELETE FROM transfer_nonces WHERE from_address = ? AND nonce != ?",
        (ADDRESS, str(nonce)),
    )
    conn.commit()
    return True


def run(success_fn):
    conn = sqlite3.connect(":memory:")
    conn.execute(SCHEMA)
    for nonce in range(1, N + 1):
        assert success_fn(conn, nonce)

    before_stale = conn.execute(
        "SELECT COUNT(*), MAX(CAST(nonce AS INTEGER)) "
        "FROM transfer_nonces WHERE from_address = ?",
        (ADDRESS,),
    ).fetchone()
    stale_accepted = success_fn(conn, 7)
    after_stale = conn.execute(
        "SELECT COUNT(*), MAX(CAST(nonce AS INTEGER)) "
        "FROM transfer_nonces WHERE from_address = ?",
        (ADDRESS,),
    ).fetchone()
    conn.close()
    return before_stale, stale_accepted, after_stale


def main():
    current = run(current_success)
    bounded = run(bounded_success)

    print("current rows/latest =", current[0])
    print("current stale nonce 7 accepted?", current[1])
    print("current after stale =", current[2])
    print("bounded rows/latest =", bounded[0])
    print("bounded stale nonce 7 accepted?", bounded[1])
    print("bounded after stale =", bounded[2])

    assert current == ((N, N), False, (N, N))
    assert bounded == ((1, N), False, (1, N))
    print("PASS: compaction bounds state without weakening stale-nonce rejection")


if __name__ == "__main__":
    main()
