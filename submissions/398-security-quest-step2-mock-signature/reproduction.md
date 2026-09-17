# RustChain Security Quest #398 — Step 2: Mock Signature Mode

**Bounty:** https://github.com/Scottcjn/rustchain-bounties/issues/398  
**Track:** Step 2, “Reproduce a Known Fix” — Mock Signature Mode  
**Reward advertised by the bounty:** 15 RTC, subject to maintainer verification  
**Fresh source pin:** `Scottcjn/Rustchain@aa584b344a766f6c0f8613ba7198d1cc7ffbae35` (current `main` when this write-up was prepared on 2026-09-17)  
**Scope:** historical known vulnerability only; no claim of a new live vulnerability.

## Executive summary

The vulnerable condition was not that RustChain lacked a mock-signature guard entirely. A guard had been added, but for a period it was invoked only from the integrated node’s `if __name__ == "__main__":` startup path. Production is served through Gunicorn using the WSGI entry point (`gunicorn ... wsgi:app`), which imports the integrated node as a module. Under an import, `__name__` is not `"__main__"`, so that invocation never ran. If mock-signature mode was enabled, production WSGI startup could therefore proceed without the fail-closed configuration check.

The fix is deliberately small and well placed: the WSGI entry point calls `rustchain_main.enforce_mock_signature_runtime_guard()` immediately after loading the integrated node module and before exposing the Flask app or initializing the database. The current guard rejects `TESTNET_ALLOW_MOCK_SIG=True` unless the runtime environment is in the explicitly allowed test/dev set. Current `main` also hardcodes the production mock-signature flag to `False`, adding another layer of safety.

I reproduced the pre-fix and post-fix startup control flow locally. The pre-fix WSGI import reached `init_db()` and exposed `application` while a test stub reported mock signatures enabled. The fixed WSGI import stopped first with `RuntimeError: TESTNET_ALLOW_MOCK_SIG blocked by WSGI guard`; `init_db()` was not reached. I also executed the current guard logic directly: a `production` runtime was blocked while a `test` runtime was allowed.

## Source evidence

### 1. Original fail-closed guard

Commit [`248948bd68cac079163b886052a76a552699b547`](https://github.com/Scottcjn/Rustchain/commit/248948bd68cac079163b886052a76a552699b547), “fix: fail closed on mock signature mode outside test runtime,” introduced `enforce_mock_signature_runtime_guard()` and tests. Its patch also invoked the guard inside the integrated node’s `if __name__ == "__main__":` block.

That is sufficient for direct `python rustchain_v2_integrated_v2.2.1_rip200.py` execution, but not for a WSGI server that imports the module.

### 2. Pre-fix production WSGI path

Immediately before the dedicated WSGI fix, at parent commit [`810211f67b1235c99a874f4a7e743d5c76e79966`](https://github.com/Scottcjn/Rustchain/commit/810211f67b1235c99a874f4a7e743d5c76e79966), `node/wsgi.py` imported the integrated node and then immediately exposed `app`, read `DB_PATH`, and called `init_db()`; there was no mock-signature guard call between module import and application/database startup.

### 3. Dedicated WSGI fix

Commit [`6e19c549ed8bcc179fc216cce298c291b165d759`](https://github.com/Scottcjn/Rustchain/commit/6e19c549ed8bcc179fc216cce298c291b165d759), “fix: enforce mock signature guard during WSGI startup (#4535),” added exactly the missing enforcement point after `spec.loader.exec_module(rustchain_main)` and before the Flask app is exposed:

```python
rustchain_main.enforce_mock_signature_runtime_guard()
```

The same commit added `test_wsgi_startup_enforces_mock_signature_guard`, which copies `wsgi.py`, supplies a stub integrated node whose guard raises, and verifies the WSGI import raises before `init_db()` can run. That test directly captures the security boundary.

### 4. Current main

At fresh main `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`:

- `node/wsgi.py` loads the integrated module, immediately calls `enforce_mock_signature_runtime_guard()`, then calls the hardware-binding runtime guard, and only then exposes the app and initializes the DB.
- `node/rustchain_v2_integrated_v2.2.1_rip200.py` sets `TESTNET_ALLOW_MOCK_SIG = False` for production and defines `_MOCK_SIG_ALLOWED_ENVS = {"test", "testing", "dev", "development", "local", "testnet"}`.
- The current guard defaults an unspecified runtime to `production` and raises if mock signatures are enabled outside that allowlist.
- `node/tests/test_mock_signature_guard.py` still asserts both production rejection and WSGI startup enforcement.

Current source links:

- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/wsgi.py
- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/rustchain_v2_integrated_v2.2.1_rip200.py
- https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/node/tests/test_mock_signature_guard.py

## Attack before the fix

The attack prerequisite was an unsafe deployment/configuration in which mock-signature mode was enabled. Mock-signature functionality is intentionally incompatible with production trust: it substitutes a testing acceptance path for normal cryptographic verification. A fail-closed startup check is therefore the right defense.

The control-flow mistake made the defense incomplete:

1. The integrated node had a function that would reject mock signatures in a production runtime.
2. Its initial startup invocation lived under `if __name__ == "__main__":`.
3. Gunicorn starts the service by importing `wsgi:app`; imported modules do not execute their `__main__` block.
4. The pre-fix `wsgi.py` imported the node and proceeded directly to `app`, `init_db`, and service startup.
5. Therefore an unsafe mock-signature configuration could survive the production startup path without encountering the intended guard.

This is a defense-bypass caused by *where* the check ran, not by a bad predicate inside the guard itself.

## Local reproduction

I reproduced the WSGI boundary locally without contacting or changing a live RustChain node. The harness used the exact relevant pre-fix and fixed `wsgi.py` control flow and the same stub strategy used by the repository’s own regression test. The stub represented the dangerous state with `TESTNET_ALLOW_MOCK_SIG = True`; its guard raises, and `init_db()` prints if startup gets that far.

Observed output:

```text
=== PRE ===
INIT_DB_REACHED
IMPORT_RESULT=SUCCESS
APPLICATION_EXPOSED= True
=== POST ===
IMPORT_RESULT=BLOCKED
EXCEPTION= RuntimeError TESTNET_ALLOW_MOCK_SIG blocked by WSGI guard
```

Interpretation:

- **Pre-fix:** production-style WSGI import skipped the guard, reached DB initialization, and exposed the application.
- **Post-fix:** the same import stopped at the guard before DB initialization or application exposure.

I separately executed the current guard predicate with mock signatures forced on:

```text
production: BLOCKED: TESTNET_ALLOW_MOCK_SIG must not be enabled outside test/dev runtimes
test: ALLOWED
```

This matches the intended policy: fail closed by default in production, permit the test feature only in explicit non-production runtimes.

## Why the fix is sufficient

For the vulnerability described here, the WSGI fix closes the missing production startup path because the guard now runs in the entry point Gunicorn actually imports. Its placement is important: it executes immediately after loading the integrated module and before `init_db()`, route serving, or other application initialization.

The current guard is also fail-closed in three useful ways:

1. Missing runtime environment defaults to `production` rather than an allowed test mode.
2. The allowlist is explicit rather than accepting arbitrary values.
3. Current main has `TESTNET_ALLOW_MOCK_SIG = False` as the production code default.

The repository regression test protects the exact WSGI ordering by making `init_db()` fail if it is reached before the guard. That is stronger than merely unit-testing the guard function in isolation.

### Residual-risk note

A startup guard is only effective for entry points that call it. The history of this bug demonstrates that security configuration checks should either be centralized in a common initialization function used by every supported launcher or be enforced at module/config construction in a way that cannot be skipped by choosing a different entry point. The present production WSGI path is guarded, and current main additionally invokes both the mock-signature and hardware-binding guards before initialization.

## Conclusion

The known Mock Signature Mode fix is a classic startup-path hardening lesson: a correct security predicate placed only in a development launcher is not a production control. Commit `6e19c549...` moved enforcement into the WSGI path that production actually executes, and the maintained regression test ensures initialization cannot outrun the guard. My local reproduction confirms the vulnerable control flow succeeds before that one-line WSGI call and is blocked after it.

No production service was probed or modified for this reproduction, and this report does not claim a currently exploitable mock-signature vulnerability on fresh main.