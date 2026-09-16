# RustChain bounty #2784 — Linux/KVM miner dry-run hardware report

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/2784

This is a real execution report for the RustChain miner dry-run bounty. No payout or sponsor acceptance is asserted here.

## Source identity

Fresh `Scottcjn/Rustchain` main at execution time:

- Commit: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`
- `miners/linux/rustchain_linux_miner.py` Git blob: `7509335dc97d55b866caa3dfbea59192021a0e2b`
- `miners/linux/fingerprint_checks.py` Git blob: `02cc1aecf96dc6bf173c714135ff6481137bd0af`
- Miner version: `RustChain Miner v2.2.1-rip200`

The shell environment could not clone GitHub directly because outbound DNS was unavailable. The two source files were therefore reconstructed from the GitHub connector's exact pinned file reads. Before execution, each reconstructed file was verified using Git's blob-SHA formula (`sha1("blob <len>\0" + bytes)`), and both hashes matched the repository blob SHAs above exactly.

## Command and exit status

```bash
python3 rustchain_linux_miner.py \
  --dry-run \
  --verbose \
  --wallet woahwhattheheck-2784-dryrun
```

Exit code: `0`

Execution timestamp: `2026-09-16T07:46:19Z` (environment capture immediately before the run).

## Hardware / runtime

- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.18.44
- Python: 3.13.5
- Architecture: `x86_64`
- CPU: AMD EPYC 9V74 80-Core Processor
- CPUs visible to this environment: 5
- RAM visible to host tools: 5.8 GiB total
- RAM reported by miner: 5 GB
- Hypervisor: KVM
- Virtualization type: full
- Serial: present
- MAC count reported by miner: 1

## Fingerprint result

The current fingerprint suite was available and executed all 6 modern-hardware checks. Five passed; anti-emulation correctly rejected this virtualized/containerized runtime.

```text
[FINGERPRINT] Running 6 hardware fingerprint checks...
Running 6 Hardware Fingerprint Checks...
==================================================

[1/6] Clock-Skew & Oscillator Drift...
  Result: PASS

[2/6] Cache Timing Fingerprint...
  Result: PASS

[3/6] SIMD Unit Identity...
  Result: PASS

[4/6] Thermal Drift Entropy...
  Result: PASS

[5/6] Instruction Path Jitter...
  Result: PASS

[6/6] Anti-Emulation Checks...
  Result: FAIL

==================================================
OVERALL RESULT: FAILED
Failed checks: ['anti_emulation']
[FINGERPRINT] FAILED checks: ['anti_emulation']
[FINGERPRINT] WARNING: May receive reduced/zero rewards
```

A direct diagnostic call to the exact same pinned `check_anti_emulation()` implementation returned:

```json
{
  "passed": false,
  "data": {
    "vm_indicators": [
      "cpuinfo:hypervisor",
      "systemd_detect_virt:container-other"
    ],
    "indicator_count": 2,
    "is_likely_vm": true,
    "fail_reason": "vm_detected"
  }
}
```

## Dry-run output

```text
======================================================================
RustChain Local Linux Miner
RIP-PoA Hardware Fingerprint + Serial Binding v2.0
======================================================================
Node: https://rustchain.org
Wallet: woahwhattheheck-2784-dryrun
Serial present: yes
======================================================================

[DRY-RUN] RustChain Linux Miner preflight
[DRY-RUN] No mining or network state will be modified
[DRY-RUN] Verbose mode: ON
[DRY-RUN] Node URL: https://rustchain.org
[DRY-RUN] API endpoint: https://rustchain.org/health
[DRY-RUN] TLS verify: True
[DRY-RUN] Node URL: https://rustchain.org
[DRY-RUN] Wallet: woahwhattheheck-2784-dryrun
[DRY-RUN] Hostname: localhost
[DRY-RUN] CPU: AMD EPYC 9V74 80-Core Processor
[DRY-RUN] Cores: 5
[DRY-RUN] Memory(GB): 5
[DRY-RUN] MAC count: 1
[DRY-RUN] Serial present: yes
[DRY-RUN] Fingerprint checks available: yes
[DRY-RUN] Fingerprint pass status: False
[DRY-RUN] GET https://rustchain.org/health
[DRY-RUN] Headers: {'User-Agent': 'RustChain-Miner/2.2.1'}
[WARN] Cannot connect to bootstrap node while running dry-run health probe (attempt 1/3): ... Failed to resolve 'rustchain.org' ...
[WARN] Retrying in 2s...
[WARN] Cannot connect to bootstrap node while running dry-run health probe (attempt 2/3): ... Failed to resolve 'rustchain.org' ...
[WARN] Retrying in 4s...
[WARN] Cannot connect to bootstrap node while running dry-run health probe (attempt 3/3): ... Failed to resolve 'rustchain.org' ...
[ERROR] Cannot connect to bootstrap node.
[ERROR] Check network connectivity and the RustChain node URL, then retry.
```

The actual error text on all three health-probe attempts was a `requests` `NameResolutionError` for `rustchain.org` (`Temporary failure in name resolution`). The environment intentionally had no usable outbound DNS/network path, so this was expected infrastructure behavior rather than a miner crash. The miner still exited `0`; it did not attest, enroll, or start the mining loop.

## Confusing behavior / UX observation

The #2784 bounty description calls dry-run “safe: no network calls, no mining.” The current miner's `dry_run()` implementation does in fact perform an optional read-only `GET https://rustchain.org/health`. It does not mutate network state, but it is still a network call. In a network-isolated environment, the retry helper makes three attempts with 2-second and 4-second backoff before the otherwise-successful `0` exit.

That mismatch is the only confusing behavior encountered. The hardware probes and VM detection behaved as expected.