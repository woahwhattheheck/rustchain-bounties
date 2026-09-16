# #520 Bug Hunter — `mlx-coffers` direct client can hang forever on peer EOF

Bounty: `Scottcjn/rustchain-bounties#520` — Bug Hunter, 3 RTC  
Target: `Scottcjn/mlx-coffers`  
Source pin: `326053b15909396b842c5eb625221dadc0673a47`  
Affected file: `distributed_matmul.py`  
Finding class: reproducible transport/liveness bug

## Summary

`distributed_matmul.MatmulConnection.matmul()` does not handle EOF from `socket.recv()` while receiving either the 16-byte response header or the FP16 result body. If the remote matmul peer closes cleanly before the expected bytes arrive, `recv()` returns `b''`; `bytearray.extend(b'')` makes no progress, so the receive loop remains true forever.

This is distinct from the router/server receive helpers in the same repository, which explicitly test for an empty chunk.

## Environment

Reproduced on:

- Linux `6.18.44` x86_64
- Python `3.13.5`
- Source reviewed at `Scottcjn/mlx-coffers@326053b15909396b842c5eb625221dadc0673a47`

## Affected code path

The direct client receives the response header with:

```python
buf = bytearray()
while len(buf) < 16:
    buf.extend(sock.recv(16 - len(buf)))
```

and receives the FP16 payload with:

```python
n_bytes = rM * rN * 2
result = bytearray()
while len(result) < n_bytes:
    result.extend(sock.recv(n_bytes - len(result)))
```

When a TCP peer performs an orderly close, Python `recv()` returns `b''`. Extending a `bytearray` with `b''` leaves its length unchanged, therefore both loops can make zero progress indefinitely.

`MatmulConnection._get_sock()` creates its socket without setting a timeout, so this direct-client path also has no timeout that eventually converts the condition into an exception.

By contrast, `mlx_matmul_server.recv_exact()` checks `if not chunk: return None`, and `coffer_router._recv_exact()` likewise checks for an empty chunk before extending its buffer.

## Minimal reproduction

From a checkout with the normal Python dependencies installed, save this as `repro_eof.py` in the repository root:

```python
import multiprocessing as mp

from distributed_matmul import MatmulConnection


class EOFSocket:
    def sendall(self, data):
        pass

    def recv(self, n):
        return b""  # normal socket EOF after peer closes


class EOFConnection(MatmulConnection):
    def _get_sock(self):
        return EOFSocket()


def run():
    EOFConnection("unused").matmul(b"", b"", M=1, N=1, K=1)


if __name__ == "__main__":
    p = mp.Process(target=run)
    p.start()
    p.join(0.5)
    print("still alive after EOF:", p.is_alive())
    if p.is_alive():
        p.terminate()
        p.join()
```

Observed:

```text
still alive after EOF: True
```

A second control using a real local `socket.socketpair()` and the exact receive-loop primitive produced the same result: after closing the peer, the child process was still alive after 250 ms and had to be terminated externally (`exitcode=-15`).

## Expected behavior

A truncated/closed remote response should fail promptly with a connection/protocol error so the caller can retry or fall back.

## Actual behavior

The caller thread can remain stuck forever after orderly peer EOF. In the distributed path this can stall a request instead of reaching the existing failover behavior.

## Suggested fix

Use one EOF-aware exact-read helper for both the direct-client header and payload, for example raising `ConnectionError` when `recv()` returns `b''`. On transport failure, reset/close `self._sock` so a later request reconnects. Add a regression test with either a fake socket returning `b''` or `socket.socketpair()` and assert the call raises rather than hangs.

## Duplicate / ownership checks

Before claiming this lane:

- fresh GitHub issue search in `Scottcjn/mlx-coffers` for `MatmulConnection`, `recv`, `EOF`, `hang`, and `timeout` returned no matching issues;
- fresh Slack search for `mlx-coffers` and for `mlx-coffers MatmulConnection` returned no owner/claim;
- the lane was announced in both coordination and delegations before this file was created.

## Submission status

A proper issue creation attempt in `Scottcjn/mlx-coffers` returned:

```text
403 Resource not accessible by integration
```

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents this GitHub-App failure and lists publication of a deliverable in a repository the contributor controls, then linking it, as an accepted fallback. It also lists a file PR and email to `sophia.eagent@gmail.com` as later fallback routes.

This file is the public, timestamped fallback artifact. Sponsor acceptance and RTC payout are **not** asserted here.