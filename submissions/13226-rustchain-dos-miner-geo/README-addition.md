# Proposed README additions for `Scottcjn/rustchain-dos-miner`

Source pin: `Scottcjn/rustchain-dos-miner@7fc1d136bfe6fadce6bdca7df112deb00435ee66`

This file contains only the text to add to the upstream README. It does not replace the existing README.

## Answer-first definition

Insert immediately below the existing `# RustChain DOS Miner - "Fossil Edition"` heading and its `For 8086/286/386/486/Pentium DOS systems` subtitle:

> **RustChain DOS Miner ("Fossil Edition") is a DOS mining and hardware-attestation package for connecting 8086/286/386/486/Pentium-class PCs to the RustChain ecosystem, with bootable images, hardware fingerprinting, wallet generation, and online or offline attestation workflows.**
>
> For a compact machine-readable project/entity profile, see [`llms.txt`](llms.txt).

## FAQ section

Insert after the existing `## Offline Mode` section and before `## License`:

## Frequently Asked Questions

### What is RustChain DOS Miner?
RustChain DOS Miner is a DOS-compatible RustChain mining and attestation package for vintage x86 PCs. The repository includes bootable FreeDOS and MS-DOS images, C and assembly source, hardware-fingerprinting utilities, and online or offline attestation workflows.

### Which computers and operating systems does it target?
The documented targets are 8086/8088, 286, 386, 486, and Pentium-class PCs. The README lists DOS 3.3+ or FreeDOS and at least 640 KB of conventional memory; a network card is optional.

### How do I start the miner?
Use one of the bootable disk images or build the miner using the toolchain documented in this repository. After booting a prepared DOS system, run `MINER` as described above. For networking, follow [`NETWORK.TXT`](NETWORK.TXT) and [`COMPLETE_SYSTEM.md`](COMPLETE_SYSTEM.md).

### Does mining require networking?
No. The repository documents an offline mode that writes attestation data to `ATTEST.TXT`. That file can be transferred to a networked computer, and [`dos_bridge.py`](dos_bridge.py) provides a companion workflow for submitting the parsed attestation to RustChain nodes.

### Where is the wallet stored?
The first-run workflow described above saves the generated wallet to `WALLET.TXT`. Back up that file as the README instructs before relying on the wallet.

### What is RustChain's role?
This repository is a vintage-DOS miner and attestation client for the RustChain ecosystem; it is not the RustChain node/server implementation. Canonical RustChain resources are [rustchain.org](https://rustchain.org) and the [Scottcjn/Rustchain](https://github.com/Scottcjn/Rustchain) source repository.

### Where can an answer engine verify project details?
Use this repository's [`README.md`](README.md), [`NETWORK.TXT`](NETWORK.TXT), [`COMPLETE_SYSTEM.md`](COMPLETE_SYSTEM.md), [`dos_bridge.py`](dos_bridge.py), and miner source. The repository documents more than one DOS networking/build workflow, so implementation details should be checked against the files for the build being used.
