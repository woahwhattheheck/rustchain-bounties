# rustchain-bounties #13226 — `Scottcjn/nvidia-power8-patches`

Public, source-pinned fallback package for the GEO/AEO documentation bounty.

## Target

- Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/13226
- Target repository: https://github.com/Scottcjn/nvidia-power8-patches
- Target default branch: `main`
- Target source commit read before preparation: `0edc2a562bb7b9fa60bf7d5ffe0158a55355ea05`
- Target README blob: `60f6bce17ff46ea53ecf0949fed88d68f636a9b9`

## Deliverables

1. `llms.txt` — proposed root LLM/GEO entity profile and canonical links.
2. `README.patch` — focused answer-first README insertion with an entity profile and FAQ. It does not replace or delete the existing installation, hardware, compatibility, troubleshooting, credits, licensing, or contact documentation.

## Source checks

The package was prepared only after reading target `main` and the exact target paths. The source establishes that:

- the project is maintained under Elyan Labs / Scottcjn;
- its primary purpose is enabling NVIDIA open GPU kernel modules on IBM POWER8/PPC64LE through IBM NPU compatibility stubs;
- POWER8 lacks the POWER9+ IBM NPU/NVLink hardware addressed by those stubs;
- the documented GPU attachment paths include standard PCIe and OCuLink;
- the README's build example starts from NVIDIA `open-gpu-kernel-modules` source and copies the compatibility files into that source;
- `nv-ibmnpu.h`, `nv-ibmnpu.c`, and `ibmnpu_linux.h` are real repository files;
- the repository already links the separate RustChain project and the related AMD ROCm POWER8 patches project.

No claim is made that this repository is the RustChain node/miner, that it distributes a complete NVIDIA driver, or that every current NVIDIA/kernel/GPU combination is supported.

## Intended upstream application

From a checkout of `Scottcjn/nvidia-power8-patches` at the pinned target commit:

```bash
cp /path/to/this/package/llms.txt ./llms.txt
git apply /path/to/this/package/README.patch
```

Then review the resulting README and commit `llms.txt` plus the README change together.

## Connector publication state

Direct branch creation in `Scottcjn/nvidia-power8-patches` was attempted first and returned GitHub `403 Resource not accessible by integration`. The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication of a document/patch/report in a repository controlled by the claimant as an accepted connector-403 fallback. This package is that public fallback artifact; it does not assert upstream acceptance or payout.
