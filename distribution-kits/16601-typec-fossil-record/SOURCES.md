# Source map

All technical claims in this package are grounded against the immutable upstream source pin:

`Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

## Immutable source files

- Fossil Record overview and feature contract: https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/fossils/README.md  
  Blob: `1194a7e493740a7fa9375bf97b380b04df170558`
- Attestation exporter and epoch calculation: https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/fossils/fossil_record_export.py  
  Blob: `32da666b225e39c43436e4dd5545ac4a00d4606d`
- Fossil Record visualizer UI and sample-data fallback: https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/fossils/index.html  
  Blob: `5baf3f4f37c335b116201d7f35b4a4bae552b9c1`

## Claim-by-claim provenance

| Package claim | Upstream evidence |
|---|---|
| The Fossil Record is an “Attestation Archaeology Visualizer.” | `fossils/README.md` title and `fossils/index.html` page title/subtitle. |
| The visualization treats attestation history as geological-style strata and describes each attestation as a fossil. | `fossils/README.md` Overview and `fossils/index.html` About panel. |
| Architecture families have distinct visual colors such as G4 amber, G5 bronze, POWER8 deep blue, and modern x86 pale grey. | Architecture table in `fossils/README.md` and `ARCHITECTURES` in `fossils/index.html`. |
| The exporter reads miner identity, architecture/family, attestation timestamp, fingerprint pass state/quality, and multiplier-related fields. | `fetch_attestation_history()` SELECT from `miner_attest_recent` in `fossils/fossil_record_export.py`. |
| Epoch mapping is approximately 24 hours from the production genesis timestamp. | `calculate_epoch()` in `fossils/fossil_record_export.py` uses integer division by `86400`; its docstring says epochs are approximately 24 hours. |
| Point size represents active-miner count for that architecture/epoch. | Visualization design in `fossils/README.md`; About panel in `fossils/index.html`. |
| First-appearance markers identify when an architecture first joins the timeline. | Features list in `fossils/README.md`; About panel in `fossils/index.html`. |
| Settlement markers appear as dashed vertical lines; documentation specifies major settlement markers every 25 epochs. | Visualization design in `fossils/README.md`; `.epoch-marker` and About panel in `fossils/index.html`. |
| The UI supports time-range, architecture, and minimum-epoch filters plus hover/click details and CSV export. | Controls and feature list in `fossils/index.html` and `fossils/README.md`. |
| If the history API is unavailable, the standalone visualizer falls back to generated sample data. | `loadData()` in `fossils/index.html` catches a failed `/api/attestations/history` fetch and calls `generateSampleData()`. |

## Important non-claims

The package intentionally does **not** treat generated sample values as live RustChain measurements. In particular:

- sample miner counts are generated demonstration values;
- sample rewards and multipliers are generated demonstration values;
- sample timestamps/epoch distributions are generated demonstration values;
- the production exporter currently initializes `rtc_earned` to `0` in the `miner_attest_recent` path with a note that actual epoch rewards would need separate calculation.

No narration line depends on those sample values.