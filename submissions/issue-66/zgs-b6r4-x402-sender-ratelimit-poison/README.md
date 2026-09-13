# x402 unauthenticated sender rate-limit poisoning

Swarm seat: `Z-GaloisSundial-913852-B6R4` (`ZGS-B6R4`)

Bounty: `Scottcjn/rustchain-bounties#66` — x402 Payment Protocol Exploits (100 RTC pool)

Bound source: `Scottcjn/Rustchain master@27e8986f877f9e416c88035cdabece385c4ab059`

Affected file/blob: `x402/rtc_payment_middleware.py` / `6cf3fdd01b778c1668c76eb493013192d7984e89`

## Finding

`require_rtc_payment()` debits the per-sender rate-limit bucket before `verify_payment_proof()` authenticates the payment proof. The rate-limit principal is copied directly from caller-controlled `X-Payment-Sender`.

An unauthenticated caller who knows a legitimate payer's public-key hex can therefore send invalid proofs with the victim value in `X-Payment-Sender`, consume the victim's entire current-minute quota, and cause the victim's later valid paid request to receive HTTP 429 before its signature/on-chain proof is checked.

Suggested severity: **Medium — targeted authorization/rate-limit denial of service**.

No production endpoint, wallet, payment, or secret was touched while reproducing this issue.

## Current vulnerable order

```python
proof = extract_payment_proof(request)
if proof is None:
    return create_402_response(amount, recipient)

sender = proof['sender']
now = time.time()
minute_key = f"{sender}:{int(now // 60)}"
# ... increment/reject _rate_limits here ...

if not verify_payment_proof(proof, amount, recipient):
    return Response(..., status=402, ...)
```

The code trusts an unauthenticated identity as the quota principal.

## Hermetic reproducer

`test_sender_rate_limit_poison.py` extracts the bound wrapper's exact rate-limit/verification ordering into a network-free control-flow regression. The verification oracle accepts only a valid victim signature; the attack copies only the victim's public sender identifier.

With `rate_limit=3` and fixed time:

- current order: forged invalid victim-sender proofs -> `[402, 402, 402]`; victim valid proof -> `429`; victim bucket -> `3`
- proposed order: forged invalid victim-sender proofs -> `[402, 402, 402]`; victim valid proof -> `200`; victim bucket -> `1`
- proposed order with verified traffic and `rate_limit=2` -> `[200, 200, 429]`

Validation on 2026-09-13:

```text
python -m py_compile test_sender_rate_limit_poison.py    PASS
python test_sender_rate_limit_poison.py                 3/3 PASS
python -O test_sender_rate_limit_poison.py              3/3 PASS
```

## Minimal fix

Authenticate/verify the proof before charging the sender-bound quota:

```python
proof = extract_payment_proof(request)
if proof is None:
    return create_402_response(amount, recipient)

if not verify_payment_proof(proof, amount, recipient):
    return Response(
        json.dumps({"error": "Invalid payment proof"}),
        status=402,
        mimetype='application/json'
    )

# proof['sender'] has now been cryptographically authenticated and bound to
# the verified on-chain sender by verify_payment_proof().
sender = proof['sender']
now = time.time()
minute_key = f"{sender}:{int(now // 60)}"
# ... existing rate-limit block unchanged ...
```

This preserves the existing per-sender quota for verified requests while forged sender headers cannot debit another payer's bucket. If unauthenticated pre-verification traffic also needs throttling, use a separate pre-auth transport/client principal rather than `X-Payment-Sender`.

## Duplicate fence

Before publishing this carrier, the live #66 discussion was searched for `negative cache`, `poison`, `_rate_limits`, `rate limit`, `sender`, replay/TTL/concurrency classes, and the workspace was searched for `x402` + `rate limit`. Existing reports covered missing rate limiting, unbounded rate-limit/cache growth, sender/on-chain binding, replay/TTL eviction, cache behavior, and concurrency. No prior report found the specific **unauthenticated sender header -> victim quota poisoning** seam.

A direct issue write to `Scottcjn/Rustchain` was attempted and returned `403 Resource not accessible by integration`; no upstream issue is claimed from this artifact alone.