# Bounty #2784 submission — miner dry-run hardware report

Claimant / miner_id: `woahwhattheheck`

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/2784

Direct issue-comment submission from the connected GitHub App returned `403 Resource not accessible by integration`, so this file is the sponsor-documented file/PR carrier for the completed report.

## Result

Tested fresh RustChain `main` at commit `8c79fba7561283ff8c880258152cd15e2610c312` using the current Linux miner:

```bash
python3 miners/linux/rustchain_linux_miner.py --dry-run --wallet woahwhattheheck --verbose --show-payload
```

Environment: GitHub-hosted Ubuntu 24.04.5 LTS, x86_64, AMD EPYC 9V74, 4 exposed vCPUs, 15 GiB RAM, Microsoft full hypervisor.

Fingerprint results:

- clock drift: PASS
- cache timing: PASS
- SIMD identity: PASS
- thermal drift entropy: PASS
- instruction path jitter: PASS
- anti-emulation: **FAIL**
- overall fingerprint: **FAILED / False**

This is the expected useful result for the hosted VM. `systemd-detect-virt` returned `microsoft`, the CPU flags included `hypervisor`, and the miner correctly rejected the virtualized environment even though the five non-anti-emulation checks passed.

The dry-run used an ephemeral keypair, saved no `miner_key.json`, performed no attestation/enrollment/mining, and the read-only `/health` probe returned HTTP 200 with node version `2.2.1-rip200`.

## Public reproducible evidence

- Full report: https://github.com/woahwhattheheck/rustchain-monitor/blob/9b9a4d835563fc128f3e49fc21c281f24d835551/evidence/rustchain-2784-miner-dryrun.md
- Successful workflow run: https://github.com/woahwhattheheck/rustchain-monitor/actions/runs/34786965667
- Evidence workflow commit: https://github.com/woahwhattheheck/rustchain-monitor/commit/ce36d27ba70bf9829b88ff93103c731b5676b8fe
- Raw log artifact: https://github.com/woahwhattheheck/rustchain-monitor/actions/runs/34786965667/artifacts/10326592744
- Artifact ZIP SHA-256: `24992f4908d03cbf9702774c2b3a7fd3e30d6708b4ae6dacf4bf186ca16bc0d9`

No source fix or sponsor-code mutation is claimed; this is a hardware/runtime compatibility report only.
