# Narration script

**Target:** 53–58 seconds  
**Narration word count:** 133

## 0:00–0:04 — Hook

RustChain has a history book for hardware. It looks like geology.

## 0:04–0:15 — The idea

The Fossil Record turns miner attestations into a timeline: each attestation becomes a fossil, and CPU families sit in color-coded strata — G4 amber, G5 bronze, POWER8 deep blue, modern x86 pale grey.

## 0:15–0:27 — What the exporter reads

Under the hood, the exporter reads attestation timestamps, architecture, fingerprint status and quality, then maps each timestamp to an approximately 24-hour epoch from chain genesis.

## 0:27–0:38 — What the chart shows

In the visualizer, point size reflects active miner count. Markers show when an architecture first appears, and dashed lines mark settlement epochs.

## 0:38–0:48 — Explore it

You can filter by time, architecture, or minimum epoch, inspect details on hover, and export filtered data to CSV.

## 0:48–0:57 — Close

Instead of one snapshot, you can watch the network’s hardware mix accumulate layer by layer. That is RustChain’s Fossil Record: attestation archaeology for silicon.