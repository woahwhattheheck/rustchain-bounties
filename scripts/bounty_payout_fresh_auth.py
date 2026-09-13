#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the payout sweep with a final fresh GitHub authorization fence.

The legacy payout script intentionally snapshots a candidate list so a large
backlog can be processed in one run.  Candidate discovery is not authority to
move money: a maintainer may revoke ``bounty-eligible`` or close a claim after
that snapshot.  This launcher keeps the existing implementation byte-for-byte
except for one fail-closed fence inserted immediately before ``transfer()``.

The transform is deliberately exact and singular.  If the payout source drifts
so the known transfer call is absent or duplicated, the launcher refuses to
execute rather than silently running without the fence.
"""
from __future__ import annotations

from pathlib import Path

_TRANSFER_MARKER = "    ok,resp=transfer(wallet,memo,idem,amount)"

_FRESH_AUTH_FENCE = '''    # Final money-movement authority must be current, not the enumeration snapshot.
    # Re-read the issue immediately before transfer so a revoked eligibility label
    # or a claim closed while this run was processing cannot still move RTC.
    auth_now=json.loads(gh(["issue","view",num,"-R",REPO,"--json","comments,labels,state"]))
    auth_state=auth_now.get("state")
    auth_labels_raw=auth_now.get("labels")
    auth_comments=auth_now.get("comments")
    if auth_state != "OPEN":
        print(f"::notice::skip #{num}: issue is no longer open at pre-transfer fence")
        continue
    if not isinstance(auth_labels_raw,list) or not isinstance(auth_comments,list):
        raise RuntimeError(f"#{num} pre-transfer authorization response is malformed")
    if any(not isinstance(c,dict) for c in auth_comments):
        raise RuntimeError(f"#{num} pre-transfer comments are malformed")
    auth_labels={
        label.get("name") for label in auth_labels_raw
        if isinstance(label,dict) and isinstance(label.get("name"),str)
    }
    eligible_now=("bounty-eligible" in auth_labels) or any(
        "Verified eligible" in (c.get("body") or "")
        and _is_trusted(_comment_author_login(c)[0])
        for c in auth_comments
    )
    if not eligible_now:
        print(f"::notice::skip #{num}: payout eligibility was revoked before transfer")
        continue
    ok,resp=transfer(wallet,memo,idem,amount)'''


def build_fresh_source(source: str) -> str:
    """Return payout source with exactly one final authorization fence inserted."""
    count = source.count(_TRANSFER_MARKER)
    if count != 1:
        raise RuntimeError(
            f"expected exactly one payout transfer marker, found {count}; refusing unfenced execution"
        )
    return source.replace(_TRANSFER_MARKER, _FRESH_AUTH_FENCE, 1)


def main() -> int:
    payout = Path(__file__).with_name("bounty_payout.py")
    source = payout.read_text(encoding="utf-8")
    patched = build_fresh_source(source)
    code = compile(patched, str(payout), "exec")
    globals_for_payout = {
        "__name__": "__main__",
        "__file__": str(payout),
        "__package__": None,
    }
    exec(code, globals_for_payout, globals_for_payout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
