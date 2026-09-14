# RustChain #398 — Step 2: Mock Signature Mode reproduction

**Claimant / payout identity:** `woahwhattheheck`  
**Quest lane:** Step 2 — Reproduce a Known Fix (15 RTC)  
**Known fix selected:** Mock Signature Mode  
**Upstream baseline reviewed:** `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35`  
**Date:** 2026-09-14

## Scope

This is a local/static reproduction of the fixed Mock Signature Mode failure class. I did not probe or alter a live RustChain node. The analysis is pinned to the upstream commit above and to these exact paths:

- `node/rustchain_v2_integrated_v2.2.1_rip200.py`
- `node/wsgi.py`
- `node/tests/test_mock_signature_guard.py`

Permalinks:

- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/rustchain_v2_integrated_v2.2.1_rip200.py
- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/wsgi.py
- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/tests/test_mock_signature_guard.py

## Attack before the fix

The sensitive path is `POST /headers/ingest_signed`. Normal operation resolves one or more registered candidate Ed25519 public keys for the claimed miner identity, derives or accepts the message, and verifies the submitted signature against those keys.

The endpoint deliberately retains a testnet compatibility branch:

```python
accepted = False
verified_pubkey_hex = None
if TESTNET_ALLOW_MOCK_SIG and len(sig_hex) == 128:
    METRICS_SNAPSHOT["rustchain_ingest_mock_accepted_total"] = (
        METRICS_SNAPSHOT.get("rustchain_ingest_mock_accepted_total", 0) + 1
    )
    accepted = True
    verified_pubkey_hex = candidate_pubkeys[0]
else:
    # normal Ed25519 verification path
```

That condition checks only the feature flag and signature-string length. If mock mode is enabled, a 128-character signature-shaped value does not need to be a valid Ed25519 signature. Therefore the historical failure mode was operational/configuration-driven: if a production process could start with `TESTNET_ALLOW_MOCK_SIG = True`, an attacker able to submit a header for an identity with a registered candidate header key could bypass signature authentication with an arbitrary 128-character value.

This is not an arbitrary-unregistered-miner bypass: key resolution occurs before the mock branch, so a candidate registered key still needs to exist. The security loss is that possession of the corresponding private key is no longer proven.

## The fix in current code

Current `main` applies two fail-closed controls around that compatibility branch.

First, production defaults are secure in `rustchain_v2_integrated_v2.2.1_rip200.py`:

```python
TESTNET_ALLOW_INLINE_PUBKEY = False
TESTNET_ALLOW_MOCK_SIG = False
_MOCK_SIG_ALLOWED_ENVS = {
    "test", "testing", "dev", "development", "local", "testnet"
}
```

Second, `enforce_mock_signature_runtime_guard()` rejects a process that tries to enable mock signatures outside those explicit non-production runtimes:

```python
def enforce_mock_signature_runtime_guard():
    runtime_env = (
        os.environ.get("RC_RUNTIME_ENV")
        or os.environ.get("RUSTCHAIN_ENV")
        or "production"
    ).strip().lower()
    if TESTNET_ALLOW_MOCK_SIG and runtime_env not in _MOCK_SIG_ALLOWED_ENVS:
        raise RuntimeError(
            "TESTNET_ALLOW_MOCK_SIG must not be enabled outside test/dev runtimes"
        )
```

The production WSGI entry point enforces this before database initialization:

```python
spec.loader.exec_module(rustchain_main)
rustchain_main.enforce_mock_signature_runtime_guard()
rustchain_main.enforce_hardware_binding_runtime_guard()

app = rustchain_main.app
init_db = rustchain_main.init_db
DB_PATH = rustchain_main.DB_PATH
init_db()
```

That ordering matters. A misconfigured production process fails at startup instead of initializing and serving a route in mock-accept mode.

The focused regression suite, `node/tests/test_mock_signature_guard.py`, covers three properties: production plus mock signatures raises; an explicit test runtime may use mock signatures; and WSGI invokes the mock-signature guard before `init_db()`.

## Local reproduction

This execution environment could not resolve `github.com` through its shell network, so a full checkout and dependency-driven official pytest run was not possible here. I therefore fetched the exact files above through the GitHub connector at the pinned SHA and ran an isolated source-faithful harness containing the current guard decision and mock-accept decision unchanged.

Observed output:

```text
production guard blocks mock mode: PASS | RuntimeError: TESTNET_ALLOW_MOCK_SIG must not be enabled outside test/dev runtimes
test runtime permits mock mode: PASS | None
test runtime reaches mock branch for 128-char signature: PASS | mock-accepted
production default routes signature to real verifier: PASS | ed25519-verify
production default fails closed when PyNaCl unavailable: PASS | fail-closed-no-nacl
SUMMARY: 5/5 source-faithful checks passed
```

The third check used a deliberately non-cryptographic 128-character value (`"x" * 128`). With mock mode enabled in a test runtime, the branch accepted it solely because its length was 128. With the production default, the same value is routed to the real verifier instead.

## Why the fix is sufficient for the known failure

For the vulnerability class described by the quest — accidentally exposing testnet mock-signature behavior in production — the fix is sufficient because it closes the dangerous configuration at the service boundary. Production defaults to real Ed25519 verification, and the normal WSGI startup refuses to run if someone flips the mock flag without also declaring a recognized test/dev runtime.

This converts the dangerous state from “production service is live but silently skips signature verification” into “production process does not start.” It also preserves the intended compatibility behavior for controlled test and development environments.

## Residual risk / defense in depth

The startup guard is a configuration safety boundary, not a sandbox. `TESTNET_ALLOW_MOCK_SIG` remains a mutable Python module global — the regression test itself temporarily sets it to `True`. If an attacker already has arbitrary Python execution inside the node process after startup, they could potentially mutate the flag after the startup guard has run. That prerequisite is substantially stronger than the original remote header-submission condition, so it does not invalidate the known fix, but it is a useful defense-in-depth boundary.

A stronger follow-up would make mock-signature acceptance consult an immutable startup configuration or re-check runtime policy at the point of use, so post-start mutation cannot activate the bypass even after full in-process compromise of ordinary mutable state.

## Conclusion

The known Mock Signature Mode issue is reproduced and understood: the compatibility branch treats any 128-character signature as accepted when its test-only flag is active. Current RustChain `main` defaults that flag off and adds a production startup guard, exercised from WSGI before initialization, which is an appropriate fail-closed fix for accidental production enablement. The remaining mutable-global concern is defense in depth rather than a recurrence of the original configuration failure.
