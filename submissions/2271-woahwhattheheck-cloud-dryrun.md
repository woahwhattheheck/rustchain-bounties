# RustChain bounty #2271 — cloud Linux miner dry-run report

**Claimant / RTC wallet ID:** `woahwhattheheck`  
**Bounty:** https://github.com/Scottcjn/rustchain-bounties/issues/2271  
**RustChain source pin:** `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`  
**Exact miner path:** `miners/linux/rustchain_linux_miner.py`  
**Exact miner blob:** `7509335dc97d55b866caa3dfbea59192021a0e2b`

## Method

The automation cloud used for this report cannot resolve public DNS directly, so a normal `git clone` of GitHub and the miner's read-only `https://rustchain.org/health` probe are unavailable from this runtime. To avoid pretending a stale or invented source tree was tested, I fetched the fresh RustChain `main` commit and exact miner source through the GitHub connector, verified the current `--dry-run` implementation and its helper paths, and executed that exact current dry-run code path locally in an isolated Linux container.

The execution directory intentionally contained only the fetched dry-run code path rather than a materialized repository checkout. As a result, the miner's normal import fallback reported `fingerprint_checks.py` unavailable. That limitation is recorded below rather than hidden. No attestation, enrollment, mining loop, wallet persistence, or network-state mutation was performed. The only network operation attempted by `dry_run()` was its read-only health probe, which failed at DNS resolution.

## Environment

- OS / kernel: Linux `6.18.44` x86_64
- CPU: Intel(R) Xeon(R) Platinum 8272CL CPU @ 2.60GHz
- Logical cores visible to the runtime: 5
- Memory visible to the runtime: 5 GB
- Python: 3.13.5
- Runtime class: cloud/containerized Linux environment

## Dry-run output

```text
[WARN] fingerprint_checks.py not found - fingerprint attestation disabled
======================================================================
RustChain Local Linux Miner
RIP-PoA Hardware Fingerprint + Serial Binding v2.0
======================================================================
Node: https://rustchain.org
Wallet: woahwhattheheck
Serial present: yes
======================================================================

[DRY-RUN] RustChain Linux Miner preflight
[DRY-RUN] No mining or network state will be modified
[DRY-RUN] Node URL: https://rustchain.org
[DRY-RUN] Wallet: woahwhattheheck
[DRY-RUN] Hostname: localhost
[DRY-RUN] CPU: Intel(R) Xeon(R) Platinum 8272CL CPU @ 2.60GHz
[DRY-RUN] Cores: 5
[DRY-RUN] Memory(GB): 5
[DRY-RUN] MAC count: 1
[DRY-RUN] Serial present: yes
[DRY-RUN] Fingerprint checks available: no
[WARN] Cannot connect to bootstrap node while running dry-run health probe (attempt 1/3): name resolution failed for rustchain.org
[WARN] Retrying in 2s...
[WARN] Cannot connect to bootstrap node while running dry-run health probe (attempt 2/3): name resolution failed for rustchain.org
[WARN] Retrying in 4s...
[WARN] Cannot connect to bootstrap node while running dry-run health probe (attempt 3/3): name resolution failed for rustchain.org
[ERROR] Cannot connect to bootstrap node.
[ERROR] Check network connectivity and the RustChain node URL, then retry.
```

**Process exit code:** `0`.

That exit status matches the current source: when the bounded read-only health probe exhausts its retries, `_get()` returns `None`; `dry_run()` then returns `True`, and `main()` maps `True` to exit code 0. This is useful compatibility evidence for isolated/cloud environments even though the health endpoint itself could not be reached.

## Submission transport

A direct comment submission to bounty #2271 through the installed GitHub App returned `403 Resource not accessible by integration`. The sponsor's current submission guide explicitly allows publishing a report in a repository controlled by the claimant and linking it when the deliverable is a document/report, with a pull-request carrier or operator/PAT comment as subsequent routes. This file is the immutable public fallback artifact for that transport failure.
