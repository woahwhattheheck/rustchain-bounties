# Assembly / edit map

Target: ~4:50, 16:9, 1080p or better. Narration follows `script.md`; visual details follow `storyboard.md`.

| Segment | Time | Visual lane | Edit notes |
|---|---:|---|---|
| Hook | 0:00–0:30 | Account vs UTXO diagram → pinned repo tree | Open on the model change, not cryptocurrency marketing. Hard cut to source at “protocol event.” |
| Deterministic bridge | 0:30–1:05 | Migration docstring/constants → tx-id diagram | Keep each source crop on screen long enough to read the highlighted line. |
| Read-only preview | 1:05–1:40 | `_open_readonly` → preview boxes → root | Use a small `illustrative` bug on generated boxes/IDs. |
| Locked snapshot | 1:40–2:15 | `BEGIN IMMEDIATE` → existing-state guards → balance load | Lock icon should be labeled `SQLite write transaction`, not “consensus lock.” |
| Mirror provenance | 2:15–2:55 | `account_mirror_boxes` source → account/box relationship → per-wallet invariant | This is the conceptual center; give the dotted provenance line a full beat before adding the invariant. |
| UTXO conservation | 2:55–3:35 | `apply_transaction` guards → 10 = 7+2+1 animation | Never show a real wallet or live transfer. |
| Root + integrity | 3:35–4:05 | deterministic tree → `integrity_check()` fields | Avoid implying a Merkle root alone proves model equality; show the provenance check separately. |
| Guarded rollback | 4:05–4:25 | auth gate → write lock → stale mempool cleanup | Never show an admin key value. |
| Close | 4:25–4:50 | Same value, new representation → source pin | End card: `Source: Scottcjn/Rustchain@aa584b3` + `Author: woahwhattheheck`. |

## Audio / pacing

- Narration: clean, conversational, 145–155 wpm.
- No background music is required. If added by the publisher, keep it low enough that code terms remain intelligible.
- Use short UI clicks or soft transitions only; avoid “hacker” sound effects that imply exploits.

## Caption notes

Render open captions. Preserve exact identifiers in monospace: `miner_id`, `BEGIN IMMEDIATE`, `account_mirror_boxes`, `output_total + fee = input_total`, `compute_state_root()`, `RC_ADMIN_KEY`.

## Final verification before export

1. All code captures show commit `aa584b344a766f6c0f8613ba7198d1cc7ffbae35` or an immutable URL to it.
2. Every generated numeric example is visibly labeled `illustrative`.
3. No production-activation claim is added in voiceover, captions, description, or thumbnail.
4. No secrets or private telemetry appear in terminal footage.
5. Credits retain `woahwhattheheck` as author under the #16601 terms.