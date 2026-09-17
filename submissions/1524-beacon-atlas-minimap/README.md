# RustChain bounty #1524 — Beacon Atlas minimap (Track B, 15 RTC)

Public fallback deliverable for `Scottcjn/rustchain-bounties#1524`, Track B **Minimap** only.

## Source pin and deconflict

- Upstream: `Scottcjn/Rustchain`
- Upstream main inspected: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`
- Target: `site/beacon/`
- Fresh code search at that SHA found no `minimap` symbol or file under `site/beacon/`.
- Existing source contracts verified before implementation:
  - `scene.js` exports `getCamera()` and `onAnimate()`.
  - `cities.js` exports `getCityCenter(cityId)`.
  - `agents.js` exports `getAgentPosition(agentId)`.
  - `index.html` builds cities and agents before calling `startLoop()`.

## Deliverable

This directory contains:

- `minimap-model.mjs` — dependency-free coordinate/bounds model for the X/Z Atlas plane.
- `minimap.js` — DOM/canvas minimap renderer using live city/agent positions and the current Three.js camera.
- `beacon_minimap.test.mjs` — Node built-in regression coverage for bounds, projection, clipping, and missing-position handling.

The minimap is intentionally read-only and scope-limited. It renders:

- all known agents as dim green points;
- city centers as amber squares;
- the current camera location as a cyan triangle;
- a north-up full-Atlas overview with responsive desktop/mobile sizing;
- a redraw cap of 10 Hz so the HUD does not add per-frame canvas work.

It injects its own narrowly-scoped CSS so the upstream integration changes only one existing file.

## Upstream integration

Copy the two runtime files into `site/beacon/`:

```text
site/beacon/minimap-model.mjs
site/beacon/minimap.js
```

Copy the test to:

```text
tests/beacon_minimap.test.mjs
```

Then make exactly two edits in `site/beacon/index.html`.

Add this import next to the existing UI/sound imports:

```js
import { initMinimap } from './minimap.js';
```

After `initUI()` and `initSoundControls(...)`, before `startLoop()`, initialize the minimap:

```js
initMinimap();
```

No backend, contract, wallet, payout, or other Beacon behavior changes are required.

## Verification

Focused model regression command after placing the files in the upstream tree:

```bash
node --test tests/beacon_minimap.test.mjs
```

Expected: four passing tests.

Browser smoke check:

1. Serve `site/beacon/` with `python3 -m http.server 8080`.
2. Load the Atlas after the existing boot sequence completes.
3. Confirm `[ATLAS MAP]` appears in the lower-right corner.
4. Confirm amber city marks and green agent marks cover the same X/Z footprint as the 3D Atlas.
5. Rotate/pan/zoom the camera and confirm the cyan camera marker updates without changing Atlas controls.
6. At a mobile viewport, confirm the minimap shrinks and does not intercept touch input (`pointer-events: none`).

## Submission state

A direct `/claim` comment on `Scottcjn/rustchain-bounties#1524` returned GitHub App `403 Resource not accessible by integration`. The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly lists publication in a controlled repository as a supported fallback for a document, patch, or report when the integration cannot write to sponsor repositories. This package is the public, timestamped fallback artifact; upstream acceptance and payout are not asserted here.
