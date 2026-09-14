# Storyboard

Production target: 16:9, 1920×1080 master, 4–5 minutes. Every terminal/code shot should use the pinned RustChain commit `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`. Never substitute production balances, wallet IDs, or live telemetry for the illustrative values below.

| Time | Shot | Exact capture / construction | On-screen copy |
|---|---|---|---|
| 0:00–0:12 | Cold open split screen | Left: simple account card `wallet A → 12.5 RTC`. Right: three boxes adding to 12.5. Animate an arrow between models, then flash a duplicate copy in red for 0.5s as the risk. | `Same value. Different state model.` |
| 0:12–0:30 | Repo title | GitHub source tree at pinned commit; highlight `node/utxo_genesis_migration.py` and `node/utxo_db.py`. | `Migration is a protocol event.` |
| 0:30–0:48 | Deterministic rules | Capture the migration module docstring and constants. Crop to the rules: sorted wallet order, one genesis box, SHA-256 tx ID, height 0. | `Sort → scale → derive → box` |
| 0:48–1:05 | Deterministic ID diagram | Build locally: `miner_id` → `"rustchain_genesis:" + miner_id` → SHA-256 → `tx_id` → `box_id`. Do not show a real wallet; use `RTC_EXAMPLE`. | `Same snapshot → same boxes` |
| 1:05–1:23 | Dry-run read-only | Capture `_open_readonly()` and the comment in `migrate()` that warns not to call `_conn()` during preview. Box `mode=ro`. | `DRY RUN = observation only` |
| 1:23–1:40 | Preview root | Capture `_state_root_from_boxes(preview_boxes)` path. Animate three sample boxes feeding a single root glyph. Label samples `illustrative`. | `Preview hashes what would be created` |
| 1:40–1:58 | Lock first | Capture `BEGIN IMMEDIATE`, then the checks for existing genesis and non-genesis state. Use a lock icon; no lock animation should imply a network consensus lock—it is the SQLite write transaction. | `Lock the snapshot before copying value` |
| 1:58–2:15 | Balance snapshot | Capture `load_account_balances(..., conn=conn)` and comment explaining the consistent snapshot. Show a frozen account table with made-up values tagged `example`. | `One snapshot, not a moving target` |
| 2:15–2:38 | Mirror provenance | Capture creation/insertion into `account_mirror_boxes`. Draw an account row and a genesis box connected by a dotted line labeled `same economic value`. | `Provenance: this box mirrors this account` |
| 2:38–2:55 | Per-wallet invariant | Capture `_check_mirror_provenance()` comment / query. Show `mirror unspent ≤ account balance` as the invariant, not as a measured live value. | `Check wallets, not only totals` |
| 2:55–3:12 | UTXO transfer anatomy | Capture `apply_transaction()` signature/docstring, duplicate-input guard, and ordinary no-input/no-output rejection in quick cuts. | `Spend objects, not a mutable number` |
| 3:12–3:35 | Conservation | Capture `(output_total + fee) != input_total`. Build an animation: input box `10` → receiver `7` + change `2` + fee `1`. Tag numbers `illustrative`. | `outputs + fee = inputs` |
| 3:35–3:52 | State root | Capture `compute_state_root()` docstring and sorted `ORDER BY box_id ASC`. Draw a small 3-leaf tree; note cardinality is mixed into leaves and odd layers use domain-separated padding. | `One deterministic fingerprint of unspent state` |
| 3:52–4:05 | Integrity result | Capture `integrity_check()` fields and the call to `_check_mirror_provenance`. Build a checklist, not a fabricated live response. | `total • count • root • model agreement • provenance` |
| 4:05–4:25 | Guarded rollback | Capture `_require_rollback_authorization()`, `BEGIN IMMEDIATE`, non-genesis refusal, and mempool eviction comments. Blur any local secret if one is present; do not type an admin key on screen. | `Rollback is privileged state mutation` |
| 4:25–4:50 | Close | Return to account card → UTXO boxes. The value label stays constant while the representation changes. End on pinned source link and repo name. | `Change the shape. Preserve ownership. Prove the result.` |

## Editor guardrails

- All account balances, wallet IDs, box IDs, roots, and transfer values created for the storyboard are **illustrative** unless captured verbatim from a public fixture/test; label illustrative values on-screen.
- Do not claim the UTXO migration, dual-write mode, or rollback path is currently active in production. This package describes source behavior at the pinned commit.
- Do not expose `RC_ADMIN_KEY`, private keys, signatures, cookies, environment dumps, or private database contents.
- Use only repo captures, locally generated diagrams, and the bundled original thumbnails. No stock footage is required.