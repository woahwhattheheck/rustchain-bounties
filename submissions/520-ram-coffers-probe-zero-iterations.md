# Bug report: `gen9_cluster probe --iterations 0` crashes with `ZeroDivisionError`

Bounty: Scottcjn/rustchain-bounties#520 (Bug Hunter, 3 RTC)

Target repository: `Scottcjn/ram-coffers`

Source pin: `92b0488d414e5ea88a734c2349feb31d0a8c6c0c`

Affected path: `gen9-cluster/gen9_cluster/cli.py`

## Summary

The `gen9_cluster probe` command accepts `--iterations 0` because the argument is declared only as `type=int`. `cmd_probe()` then performs zero timed runner calls and divides by `args.iterations` while formatting the per-expert latency. The command therefore raises `ZeroDivisionError` instead of rejecting a non-positive benchmark count.

Negative iteration counts are also accepted. `range(negative)` executes no timed calls, while the derived FLOP/byte totals become negative and the reported latency divisor is negative, so invalid benchmark input can produce nonsensical metrics instead of a validation error.

## Fresh-source evidence

At the pinned source commit, the parser contains:

```python
p_probe.add_argument("--iterations", type=int, default=5)
```

and `cmd_probe()` contains:

```python
runner(x, weights, [1.0])                       # warm the caches
started = time.perf_counter()
for _ in range(args.iterations):
    runner(x, weights, [1.0])
elapsed = time.perf_counter() - started

flops = 2.0 * 3.0 * hidden * intermediate * args.iterations
gflops = flops / elapsed / 1e9
bytes_read = 3.0 * hidden * intermediate * 4.0 * args.iterations
...
print(f"{elapsed / args.iterations * 1e3:.2f} ms/expert")
```

There is no positive-integer validation on `--iterations`. A fresh code search of `gen9-cluster/tests` found no test referencing `iterations`.

## Reproduction

User-facing trigger:

```bash
python -m gen9_cluster probe --iterations 0
```

The exact post-loop arithmetic from the pinned function can be reproduced independently as follows:

```python
import time

iterations = 0
hidden = 4096
intermediate = 1024

started = time.perf_counter()
for _ in range(iterations):
    pass
elapsed = time.perf_counter() - started

flops = 2.0 * 3.0 * hidden * intermediate * iterations
gflops = flops / elapsed / 1e9
bytes_read = 3.0 * hidden * intermediate * 4.0 * iterations

print("gflops", gflops)
print("bytes_read", bytes_read)
print(elapsed / iterations * 1e3)
```

Observed in the verification environment:

```text
gflops 0.0
bytes_read 0.0
ZeroDivisionError: float division by zero
```

Environment:

- Linux 6.18.44 x86_64, glibc 2.41
- Python 3.13.5
- NumPy 2.3.5

The execution container could not resolve `github.com` for a full `git clone`, so I did not claim a complete package invocation receipt. The source pin, exact affected file, parser definition, and failing arithmetic were read directly from GitHub and the deterministic failing arithmetic above was executed locally unchanged.

## Expected behavior

`probe` should reject `0` and negative iteration counts before benchmark allocation/execution, preferably as an argparse validation error with exit code 2.

## Actual behavior

`0` passes argument parsing and reaches result formatting, where `elapsed / args.iterations` raises `ZeroDivisionError`. Negative values likewise pass parsing and can lead to invalid negative benchmark metrics.

## Suggested fix

Validate `--iterations` as a strictly positive integer. For example, use an argparse type helper that raises `argparse.ArgumentTypeError` when `value <= 0`, or add an explicit early guard in `cmd_probe()`. Add regression coverage for both `--iterations 0` and a negative value.

The same input-validation pass could also reject non-positive `--hidden` and `--intermediate`, but those are separate robustness cases and are not required to fix this report.

## Duplicate/collision checks

Before publication:

- GitHub issue search in `Scottcjn/ram-coffers` for `--iterations`, `probe` + `zero`, and `ZeroDivisionError`: no matching issue found.
- Slack coordination/delegation search for `ram-coffers` + `--iterations 0` / probe iterations: no matching owned lane found.

## Submission-path receipt

Direct `/claim` on `Scottcjn/rustchain-bounties#520` returned GitHub API `403 Resource not accessible by integration`.

Direct creation of the proper bug issue in `Scottcjn/ram-coffers` returned the same `403 Resource not accessible by integration`.

The sponsor's `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a controlled repository (and a file PR attempt) as fallback paths for this GitHub App limitation. This file is that public, timestamped fallback artifact. No RTC is counted unless/until the maintainer confirms acceptance.