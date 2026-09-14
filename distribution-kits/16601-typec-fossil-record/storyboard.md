# Storyboard and capture plan

## Format

- Canvas: 1080 × 1920 (9:16)
- Final duration: 57 seconds maximum
- Keep primary UI/code inside the center 80% safe area so platform chrome does not cover labels.
- Use only source captures from the pinned RustChain commit and original text overlays.

## Reproducible capture setup

```bash
git clone https://github.com/Scottcjn/Rustchain.git
cd Rustchain
git checkout aa584b344a766f6c0f8613ba7198d1cc7ffbae35
python3 -m http.server 8000 --directory fossils
```

Open `http://127.0.0.1:8000/index.html` in a browser. With this static-server setup, the history API is unavailable and the page's own JavaScript falls back to generated sample data. Keep a visible `SAMPLE DATA — UI DEMO` overlay on every shot containing generated values. The `Load Sample Data` button can also be used to reset the demo.

## Shot 1 — 0:00–0:04

**Narration:** “RustChain has a history book for hardware. It looks like geology.”

Capture the top of `fossils/index.html`: the `🦕 The Fossil Record` heading and `Attestation Archaeology Visualizer` subtitle. Slow 3% push-in. Add an original lower-third: `HARDWARE HISTORY, AS STRATA`.

## Shot 2 — 0:04–0:15

**Narration:** the color-coded strata sentence.

Scroll to the visualization and legend. Crop vertically so the architecture bands and several points dominate the phone frame. Pan across the legend entries for G4, G5, POWER8, and x86_64. Keep `SAMPLE DATA — UI DEMO` pinned at the top. Do not call any generated point count, reward, multiplier, or date a live-network measurement.

## Shot 3 — 0:15–0:27

**Narration:** exporter fields and approximately 24-hour epoch mapping.

Use a clean terminal capture from the pinned commit:

```bash
git show aa584b344a766f6c0f8613ba7198d1cc7ffbae35:fossils/fossil_record_export.py
```

Zoom first on the `miner_attest_recent` SELECT fields (`miner`, `device_arch`, `device_family`, `ts_ok`, `fingerprint_passed`, `entropy_score`, `warthog_bonus`), then on `calculate_epoch()` and its `86400` divisor. Use short original callouts: `ATTESTATION FIELDS` and `~24H EPOCHS`.

## Shot 4 — 0:27–0:38

**Narration:** point size, first-appearance markers, settlement lines.

Return to the visualizer. Hover one point long enough for the tooltip to appear. Then move over the chart while the edit overlays three concise labels: `SIZE = ACTIVE MINERS`, `✨ = FIRST APPEARANCE`, `DASHED = SETTLEMENT MARKERS`. Keep the sample-data disclosure visible.

## Shot 5 — 0:38–0:48

**Narration:** filters, hover, CSV export.

Capture the controls in one continuous take: change `Time Range`, open `Architecture`, adjust `Min Epoch`, then hover a point and end with the `Export CSV` button in frame. Do not need to save or open the exported file on camera.

## Shot 6 — 0:48–0:57

**Narration:** closing sentence.

Use a slow vertical move across the layered visualization. Fade to an original end card:

```text
THE FOSSIL RECORD
Attestation archaeology for silicon
Source: github.com/Scottcjn/Rustchain
```

Small footer: `Source pinned in description · sample UI footage labeled`.

## Edit notes

- No music is required. If music is added by the publisher, use material it owns or has licensed.
- Avoid synthetic “live” numbers. The source includes a sample-data generator; generated demo values are not network telemetry.
- Do not imply that architecture colors or visual depth affect consensus or reward. They are visualization choices.
- A human editor can execute the entire visual plan with the pinned public repository plus a browser and terminal; no private credentials or production access are needed.