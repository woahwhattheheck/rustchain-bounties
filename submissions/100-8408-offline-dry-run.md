# RustChain #8408 — offline Linux miner dry-run patch

**Paid lane:** `Scottcjn/rustchain-bounties#100` (improvement PR reward, 10 RTC if accepted)

**Target issue:** `Scottcjn/Rustchain#8408` — Linux miner `--dry-run` still performs two link-local cloud-metadata probes and a three-attempt node health probe.

**Pinned source:** `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

**Verified target blobs:**

- `miners/linux/rustchain_linux_miner.py` — `7509335dc97d55b866caa3dfbea59192021a0e2b`
- `miners/linux/fingerprint_checks.py` — `02cc1aecf96dc6bf173c714135ff6481137bd0af`

## Proposed behavior

Keep existing `--dry-run` behavior backward-compatible, and add an explicit `--offline` modifier that is only valid together with `--dry-run`.

`--dry-run --offline` should:

1. retain all local hardware and anti-emulation checks;
2. skip only the two `169.254.169.254` cloud-metadata probes inside anti-emulation;
3. skip the RustChain `/health` probe entirely;
4. keep the existing ephemeral-key/no-key-persistence behavior of dry-run;
5. reject `--offline` without `--dry-run`, so normal mining can never accidentally weaken its anti-VM checks.

This avoids changing existing online dry-run semantics while providing the fully offline preflight requested in #8408.

## Ready-to-apply diff

```diff
diff --git a/miners/linux/fingerprint_checks.py b/miners/linux/fingerprint_checks.py
--- a/miners/linux/fingerprint_checks.py
+++ b/miners/linux/fingerprint_checks.py
@@
-def check_anti_emulation() -> Tuple[bool, Dict]:
+def check_anti_emulation(allow_network: bool = True) -> Tuple[bool, Dict]:
@@
-    # --- Cloud metadata endpoint check ---
-    # AWS, GCP, Azure, DigitalOcean all use 169.254.169.254
-    try:
-        import urllib.request
-        req = urllib.request.Request(
-            "http://169.254.169.254/",
-            headers={"Metadata": "true"}
-        )
-        resp = urllib.request.urlopen(req, timeout=1)
-        cloud_body = resp.read(512).decode("utf-8", errors="replace").lower()
-        cloud_provider = "unknown_cloud"
-        if "latest" in cloud_body or "meta-data" in cloud_body:
-            cloud_provider = "aws_or_gcp"
-        if "azure" in cloud_body or "microsoft" in cloud_body:
-            cloud_provider = "azure"
-        vm_indicators.append("cloud_metadata:{}".format(cloud_provider))
-    except:
-        pass
-
-    # --- AWS IMDSv2 check (token-based, t3/t4 Nitro instances) ---
-    try:
-        import urllib.request
-        token_req = urllib.request.Request(
-            "http://169.254.169.254/latest/api/token",
-            headers={"X-aws-ec2-metadata-token-ttl-seconds": "5"},
-            method="PUT"
-        )
-        token_resp = urllib.request.urlopen(token_req, timeout=1)
-        if token_resp.status == 200:
-            vm_indicators.append("cloud_metadata:aws_imdsv2")
-    except:
-        pass
+    if allow_network:
+        # --- Cloud metadata endpoint check ---
+        # AWS, GCP, Azure, DigitalOcean all use 169.254.169.254.
+        try:
+            import urllib.request
+            req = urllib.request.Request(
+                "http://169.254.169.254/",
+                headers={"Metadata": "true"}
+            )
+            resp = urllib.request.urlopen(req, timeout=1)
+            cloud_body = resp.read(512).decode("utf-8", errors="replace").lower()
+            cloud_provider = "unknown_cloud"
+            if "latest" in cloud_body or "meta-data" in cloud_body:
+                cloud_provider = "aws_or_gcp"
+            if "azure" in cloud_body or "microsoft" in cloud_body:
+                cloud_provider = "azure"
+            vm_indicators.append("cloud_metadata:{}".format(cloud_provider))
+        except:
+            pass
+
+        # --- AWS IMDSv2 check (token-based, t3/t4 Nitro instances) ---
+        try:
+            import urllib.request
+            token_req = urllib.request.Request(
+                "http://169.254.169.254/latest/api/token",
+                headers={"X-aws-ec2-metadata-token-ttl-seconds": "5"},
+                method="PUT"
+            )
+            token_resp = urllib.request.urlopen(token_req, timeout=1)
+            if token_resp.status == 200:
+                vm_indicators.append("cloud_metadata:aws_imdsv2")
+        except:
+            pass
@@
     data = {
         "vm_indicators": vm_indicators,
         "indicator_count": len(vm_indicators),
         "is_likely_vm": len(vm_indicators) > 0,
+        "cloud_metadata_checks": "enabled" if allow_network else "skipped_offline",
     }
@@
-def validate_all_checks(include_rom_check: bool = True) -> Tuple[bool, Dict]:
+def validate_all_checks(include_rom_check: bool = True,
+                        allow_network: bool = True) -> Tuple[bool, Dict]:
@@
-        ("anti_emulation", "Anti-Emulation Checks", check_anti_emulation),
+        (
+            "anti_emulation",
+            "Anti-Emulation Checks",
+            lambda: check_anti_emulation(allow_network=allow_network),
+        ),
     ]

diff --git a/miners/linux/rustchain_linux_miner.py b/miners/linux/rustchain_linux_miner.py
--- a/miners/linux/rustchain_linux_miner.py
+++ b/miners/linux/rustchain_linux_miner.py
@@
 class LocalMiner:
     def __init__(self, wallet=None, wart_address=None, wart_pool=None,
                  bzminer_path=None, manage_bzminer=False, verbose=False, show_payload=False,
-                 persist_key=True):
+                 persist_key=True, offline=False):
         self.node_url = NODE_URL
+        self.offline = offline
@@
     def _run_fingerprint_checks(self):
         """Run 6 hardware fingerprint checks for RIP-PoA"""
         print("\n[FINGERPRINT] Running 6 hardware fingerprint checks...")
         try:
-            passed, results = validate_all_checks()
+            passed, results = validate_all_checks(allow_network=not self.offline)
@@
     def dry_run(self):
         """Preview miner setup without attesting/enrolling/mining."""
         print("\n[DRY-RUN] RustChain Linux Miner preflight")
         print("[DRY-RUN] No mining or network state will be modified")
+        if self.offline:
+            print("[DRY-RUN] Offline mode: cloud metadata and node health HTTP probes disabled")
@@
-        # Optional health probe (read-only)
-        try:
-            url = f"{self.node_url}/health"
-            if self.verbose:
-                print(f"[DRY-RUN] GET {url}")
-                print(f"[DRY-RUN] Headers: {{'User-Agent': 'RustChain-Miner/2.2.1'}}")
-            r = self._get("/health", "running dry-run health probe", timeout=8, verify=TLS_VERIFY)
-            if r is None:
-                return True
-            print(f"[DRY-RUN] Health probe: HTTP {r.status_code}")
-            if self.verbose:
-                print(f"[DRY-RUN] Response headers: {dict(r.headers)}")
-            if r.ok:
-                data = r.json()
-                print(f"[DRY-RUN] Node version: {data.get('version', 'n/a')}")
-                if self.show_payload:
-                    import json
-                    print(f"[DRY-RUN] Response body: {json.dumps(data, indent=2)}")
-        except Exception as e:
-            print(f"[DRY-RUN] Health probe failed: {e}")
-            if self.verbose:
-                import traceback
-                traceback.print_exc()
+        if self.offline:
+            print("[DRY-RUN] Health probe: skipped (--offline)")
+        else:
+            # Optional health probe (read-only)
+            try:
+                url = f"{self.node_url}/health"
+                if self.verbose:
+                    print(f"[DRY-RUN] GET {url}")
+                    print(f"[DRY-RUN] Headers: {{'User-Agent': 'RustChain-Miner/2.2.1'}}")
+                r = self._get("/health", "running dry-run health probe", timeout=8, verify=TLS_VERIFY)
+                if r is None:
+                    return True
+                print(f"[DRY-RUN] Health probe: HTTP {r.status_code}")
+                if self.verbose:
+                    print(f"[DRY-RUN] Response headers: {dict(r.headers)}")
+                if r.ok:
+                    data = r.json()
+                    print(f"[DRY-RUN] Node version: {data.get('version', 'n/a')}")
+                    if self.show_payload:
+                        import json
+                        print(f"[DRY-RUN] Response body: {json.dumps(data, indent=2)}")
+            except Exception as e:
+                print(f"[DRY-RUN] Health probe failed: {e}")
+                if self.verbose:
+                    import traceback
+                    traceback.print_exc()
@@
     parser.add_argument(
         "--dry-run",
         action="store_true",
         help="Run preflight checks only; print hardware fingerprint info; do not start mining",
     )
+    parser.add_argument(
+        "--offline",
+        action="store_true",
+        help="With --dry-run, skip cloud metadata and node health HTTP probes",
+    )
     parser.add_argument("--verbose", action="store_true", help="Enable verbose output showing API endpoints, headers, and response details")
     parser.add_argument("--show-payload", action="store_true", help="Show request payload in dry-run mode")
     args = parser.parse_args(argv)
+
+    if args.offline and not args.dry_run:
+        parser.error("--offline requires --dry-run")
@@
         verbose=args.verbose,
         show_payload=args.show_payload,
         persist_key=not args.dry_run,
+        offline=args.offline,
     )

diff --git a/tests/test_linux_miner_offline_dry_run.py b/tests/test_linux_miner_offline_dry_run.py
new file mode 100644
--- /dev/null
+++ b/tests/test_linux_miner_offline_dry_run.py
@@
+import importlib.util
+import sys
+import urllib.request
+from pathlib import Path
+
+import pytest
+
+
+ROOT = Path(__file__).resolve().parents[1]
+LINUX_MINER_DIR = ROOT / "miners" / "linux"
+
+
+def _load_module(name, path):
+    spec = importlib.util.spec_from_file_location(name, path)
+    module = importlib.util.module_from_spec(spec)
+    sys.modules[name] = module
+    spec.loader.exec_module(module)
+    return module
+
+
+def test_anti_emulation_offline_skips_metadata_http(monkeypatch):
+    fingerprint = _load_module(
+        "offline_test_fingerprint_checks",
+        LINUX_MINER_DIR / "fingerprint_checks.py",
+    )
+    attempted = []
+
+    def fail_urlopen(request, *args, **kwargs):
+        attempted.append(getattr(request, "full_url", str(request)))
+        raise AssertionError("offline mode attempted metadata HTTP")
+
+    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)
+    _, data = fingerprint.check_anti_emulation(allow_network=False)
+
+    assert attempted == []
+    assert data["cloud_metadata_checks"] == "skipped_offline"
+
+
+def test_anti_emulation_online_keeps_metadata_probes(monkeypatch):
+    fingerprint = _load_module(
+        "online_test_fingerprint_checks",
+        LINUX_MINER_DIR / "fingerprint_checks.py",
+    )
+    attempted = []
+
+    def record_and_block(request, *args, **kwargs):
+        attempted.append(getattr(request, "full_url", str(request)))
+        raise OSError("blocked in test")
+
+    monkeypatch.setattr(urllib.request, "urlopen", record_and_block)
+    fingerprint.check_anti_emulation(allow_network=True)
+
+    assert attempted == [
+        "http://169.254.169.254/",
+        "http://169.254.169.254/latest/api/token",
+    ]
+
+
+def test_offline_requires_dry_run(monkeypatch):
+    sys.path.insert(0, str(LINUX_MINER_DIR))
+    try:
+        miner = _load_module(
+            "offline_test_linux_miner_cli",
+            LINUX_MINER_DIR / "rustchain_linux_miner.py",
+        )
+        with pytest.raises(SystemExit) as exc:
+            miner.main(["--offline"])
+        assert exc.value.code == 2
+    finally:
+        if sys.path and sys.path[0] == str(LINUX_MINER_DIR):
+            sys.path.pop(0)
+
+
+def test_dry_run_offline_skips_health_probe(monkeypatch):
+    sys.path.insert(0, str(LINUX_MINER_DIR))
+    try:
+        miner = _load_module(
+            "offline_test_linux_miner_dry_run",
+            LINUX_MINER_DIR / "rustchain_linux_miner.py",
+        )
+        monkeypatch.setattr(miner, "FINGERPRINT_AVAILABLE", False)
+        monkeypatch.setattr(miner, "CRYPTO_AVAILABLE", False)
+        monkeypatch.setattr(miner, "get_hardware_serial", lambda *args, **kwargs: None)
+
+        instance = miner.LocalMiner(
+            wallet="test-wallet",
+            persist_key=False,
+            offline=True,
+        )
+        instance._get_hw_info = lambda: instance.hw_info.update({
+            "hostname": "test-host",
+            "cpu": "test-cpu",
+            "cores": 1,
+            "memory_gb": 1,
+            "macs": [],
+            "serial": None,
+            "probe_warning": "",
+        }) or instance.hw_info
+
+        def fail_get(*args, **kwargs):
+            raise AssertionError("offline dry-run attempted node HTTP")
+
+        instance._get = fail_get
+        assert instance.dry_run() is True
+    finally:
+        if sys.path and sys.path[0] == str(LINUX_MINER_DIR):
+            sys.path.pop(0)
```

## Regression intent

The tests are intentionally split across the two outbound surfaces reported in #8408:

- `urllib.request.urlopen` must receive **zero calls** when anti-emulation runs with `allow_network=False`;
- the miner's `_get()` health path must receive **zero calls** under `--dry-run --offline`;
- online anti-emulation still attempts the exact two metadata URLs, proving normal mining behavior is unchanged;
- `--offline` without `--dry-run` exits at argument validation instead of weakening a real mining session.

## Publication / connector blocker

The GitHub connection can read the sponsor repository and exposes branch/file/commit/PR write actions, but the authenticated installation does not own a `woahwhattheheck/Rustchain` fork. Creating a feature branch directly in `Scottcjn/Rustchain` from the pinned main SHA returned `403 Resource not accessible by integration` twice. The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents controlled-repository publication as a fallback for a patch after this connector-specific 403, so this artifact preserves the exact proposal publicly and immutably for an operator or maintainer to apply.

No sponsor-main mutation occurred.