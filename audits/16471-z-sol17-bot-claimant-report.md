# #16471 supplementary finding — bot claimant can reach payout

**Auditor:** Z-Sol-17 / GPT-5.6 Sol  
**Source pinned:** `Scottcjn/rustchain-bounties@b404a4c75471fa738f759cc56fe3989d388be364`  
**Scope:** `scripts/bounty_payout.py`  
**Bounty:** upstream issue `Scottcjn/rustchain-bounties#16471` — 35 RTC audit + 10 RTC per confirmed additional defect beyond the first.  
**Payout routing if maintainer confirms this finding:** authenticated GitHub handle `woahwhattheheck`; no native RTC wallet is invented here.

## Finding

`bounty_payout.py` declares a safety invariant that bots are excluded so automation cannot farm rewards. `_is_bot_login()` exists and correctly recognizes bot metadata, known automation logins, and `[bot]` suffixes. However, the payout loop does not reject the **claim issue author** as a bot before wallet resolution.

`resolve_wallet()` applies a bot check only to its final claimant-handle fallback. Three higher-priority destinations return first:

1. `CANONICAL_WALLETS[claimant_login]`;
2. a native `RTC…` address in the issue body;
3. a parseable `Wallet: <handle>` in the issue body.

The production caller fetches `body,comments,author`, extracts only `author.login`, and calls `resolve_wallet(..., claimant_login=claimant)` without checking `_is_bot_login(claimant, author_obj)`.

## Concrete wrong-effect path

1. An issue authored by `github-actions[bot]` (or another bot identity) enters the payout candidate set and becomes legitimately `bounty-eligible` through an authorized gate/maintainer action.
2. The bot-authored issue body contains a valid native RTC address, or the bot login exists in the canonical claimant registry.
3. `resolve_wallet()` returns that destination before the only claimant-bot check.
4. `transfer()` can succeed; the script posts `RTC-AutoPay-Confirmed`, closes the issue, and exits green.

The code therefore pays an automation identity despite its explicit safety contract, with no error or review state.

## Deterministic helper proof

The current semantics satisfy both assertions simultaneously:

```python
bot = "github-actions[bot]"
wallet = "RTC" + "a" * 40
assert _is_bot_login(bot, None) is True
assert resolve_wallet(f"Wallet: {wallet}", [], claimant_login=bot) == (wallet, "native")
```

The existing test named `test_bot_claimant_rejected` covers only an empty-body claim that reaches the *last-resort* handle fallback, so it does not exercise the native/canonical/body-handle bypass.

## Distinction from prior #16471 bot findings

The upstream thread already contains bot-related fixes for **comment authors** and the GraphQL/REST comment shape. Those protect comment-sourced wallet data. This finding is the separate missing **top-level claimant identity gate** and is reachable before comment scanning.

## Proposed repair

Treat claimant identity as a top-level authorization boundary before any payout destination is resolved:

- preserve the full `author` object from `gh issue view`;
- pass it to `resolve_wallet()` (or reject in the caller);
- if `_is_bot_login(claimant_login, author_obj)` is true, return no destination / skip the claim before canonical, native, body-handle, comment, or fallback paths;
- add regressions for bot claimant + canonical registry, native body wallet, body handle, and metadata-only bot identity; keep a human native-wallet control.

A ready-to-apply unified patch is stored beside this report as `audits/16471-z-sol17-bot-claimant.patch`.

## Sponsor publication status

A direct upstream issue-comment write was attempted after duplicate checking and returned GitHub `403 Resource not accessible by integration`. This report and patch are therefore the durable handoff source; sponsor-facing publication still requires a seat/account with upstream write reach. No payment is asserted until maintainer confirmation and canonical RTC receipt.
