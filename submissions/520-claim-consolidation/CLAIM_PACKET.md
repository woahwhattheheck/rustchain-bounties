# RustChain #520 — blocked-claim conversion packet

Status: **internal conversion control only; no sponsor acceptance, payout, receivable, or RTC credit is asserted.**

Canonical machine manifest: [`manifest.json`](./manifest.json)

## What exists

`Scottcjn/rustchain-bounties#520` currently advertises **3 RTC per confirmed valid bug** and explicitly allows multi-claim. Literal `woahwhattheheck/rustchain-bounties@e01015ff53bb0f96e45984bc18ba6ec74df7631a` contains **19 distinct `520-*` public evidence carriers** covering 13 upstream repositories.

If — and only if — every carrier were independently accepted, the arithmetic ceiling would be **57 RTC**. That number is a gross scenario, **not earned RTC, not a receivable, and not a payout forecast**.

Every indexed carrier records a proper target-issue write blocked by GitHub App `403 Resource not accessible by integration`. Several also record the #520 claim/comment itself blocked by the same integration boundary. Their technical evidence is public; the sponsor-facing acceptance prerequisites are not complete.

## Sponsor contract that controls the next step

The current sponsor guide, `docs/HOW_TO_SUBMIT_A_BOUNTY.md`, says:

- #520 requires a real reproducible bug, a proper issue with reproduction steps/environment, no duplicate, and then a link on #520.
- A GitHub-App 403 is an expected harness limitation.
- Preferred recovery is a user/PAT-authenticated post or escalation to the human operator.
- Publishing the deliverable in a controlled repository is a public fallback, but it does not itself satisfy activity that must occur on sponsor repositories.
- Email to **`sophia.eagent@gmail.com`** with the bounty number is an accepted fallback; the sponsor says it can file complete work on the contributor's behalf while preserving credit/payout.
- An email submission must include the bounty number/URL, the deliverable, a public URL when applicable, the RTC wallet, and explicit AI disclosure.

Therefore these carriers should **not** be converted into 19 blind #520 comments. Each needs a proper upstream issue identity first, unless the sponsor itself files it via the documented email route.

## Single-writer conversion plan

1. **Fresh duplicate/obsolescence census.** Re-read each pinned target's current issues/PRs/main immediately before outbound. Drop or annotate anything already fixed, independently reported, or no longer reproducible.
2. **Select one writer.** Use the Commons Muse arbitration before any email, GitHub comment, or other human-facing sponsor contact. Do not let parallel seats contact the same sponsor seconds apart.
3. **Bind payout identity.** Supply the operator-approved RTC wallet value. This packet intentionally contains no guessed wallet.
4. **Disclose automation because the sponsor requires it.** The sponsor guide explicitly makes AI disclosure an email-submission requirement. Do not omit it in this sponsor route.
5. **Prefer one consolidated sponsor email over a comment spray.** Ask the sponsor to file the still-current reports on the contributor's behalf under the documented 403 fallback. Link the machine manifest and the individual public carriers. Make clear that every report is an independent bug and that no RTC is being counted before confirmation.
6. **Let the sponsor choose issue granularity.** If they require one email or one issue per finding, follow that instruction after the first reply rather than guessing and generating duplicate traffic.
7. **Reconcile receipts.** Record sponsor-created issue URLs, #520 claim-comment URLs, accept/reject/duplicate decisions, and only then any actual RTC award/settlement evidence back into the manifest/ledger.

## Evidence-first triage

The following ordering is for **review bandwidth**, not a claim that the sponsor will accept one report over another.

### A — direct contract/invariant failures with strong deterministic evidence

- `clawrtc-rs-tls-certificate-verification-disabled` — default client explicitly disables TLS certificate validation.
- `openclaw-x402-backend-failure-consumes-payment` — payment is consumed before paid backend success; transient failure can force a second payment.
- `qb-auto-delete-line-substring` — destructive line selector is prefix-ambiguous and `.first` can choose the wrong invoice line.
- `rustchain-monitor-balance-schema-mismatch` — canonical non-zero `amount_rtc` response is read from the wrong key and silently becomes zero.
- `rustchain-claim-portal-mcp-integer-overflow` — `1e309` decodes to infinity; `int()` raises uncaught `OverflowError` and reaches internal-error handling.
- `rustchain-mcp-wall-clock-nonce-collision` — wall-clock-millisecond nonce can collide/regress while the node correctly rejects duplicate/out-of-order nonces.
- `beacon-agent-card-malformed-pubkey` — boolean verifier raises on malformed public-key fields before its protected signature verification path.
- `beacon-contract-agent-type-validation` — wrong JSON types crash before the route's existing structured validation.
- `rustchain-mcp-read-timeout-unhandled` — transport errors escape three read tools despite structured handling existing elsewhere in the same module.

### B — deterministic boundary/ranking/identity failures

- `beacon-atlas-calibration-history-limit`
- `bottube-python-sdk-urlerror`
- `bottube-syndication-get-runs-boundary`
- `bounty-concierge-pool-url-false-verification`
- `bounty-concierge-skill-matcher-substring-false-positive`
- `grazer-mcp-malformed-video-shape`
- `grazer-negative-max-retries`
- `grazer-skill-nostr-truncated-event-url`
- `ram-coffers-probe-zero-iterations`
- `shaprai-lifecycle-state-gate-bypass`

All 19 still require a fresh current-target duplicate/fixed-state check before sponsor contact.

## Suggested one-email structure — **draft ingredients, not authorization to send**

Subject concept: `Bounty #520 — 403-blocked Bug Hunter reports for sponsor filing`

Body ingredients:

- State that the connected GitHub App cannot create the required upstream issues/comments and returns the documented 403.
- Ask the sponsor to file the attached/linked reports on the contributor's behalf under its own documented fallback.
- Give the #520 URL and approved RTC wallet.
- Include explicit AI/automation disclosure because the sponsor requires it.
- Link this packet/manifest plus each still-current carrier.
- State that the reports are independent findings, that duplicates/fixed findings should be rejected without ceremony, and that no payout is being asserted in advance.
- Ask for one reply listing the created issue URLs / accepted duplicates / rejected items so the public ledger can be reconciled without repeated follow-ups.

Do **not** send this until Muse arbitration names the single writer and the wallet/current-target census are complete.

## Inventory

| # | Target | Finding key | Current transport state |
|---:|---|---|---|
| 1 | `Scottcjn/beacon-skill` | `beacon-atlas-calibration-history-limit` | public carrier; upstream issue 403 |
| 2 | `Scottcjn/beacon-skill` | `beacon-agent-card-malformed-pubkey` | public carrier; upstream issue 403 |
| 3 | `Scottcjn/beacon-skill` | `beacon-contract-agent-type-validation` | public carrier; upstream issue 403 |
| 4 | `Scottcjn/bottube` | `bottube-python-sdk-urlerror` | public carrier; upstream issue 403 |
| 5 | `Scottcjn/bottube` | `bottube-syndication-get-runs-boundary` | public carrier; upstream issue 403 |
| 6 | `Scottcjn/bounty-concierge` | `bounty-concierge-pool-url-false-verification` | public carrier; upstream issue 403 |
| 7 | `Scottcjn/bounty-concierge` | `bounty-concierge-skill-matcher-substring-false-positive` | upstream issue + #520 route 403 |
| 8 | `Scottcjn/clawrtc-rs` | `clawrtc-rs-tls-certificate-verification-disabled` | upstream issue + #520 route 403 |
| 9 | `Scottcjn/grazer-mcp` | `grazer-mcp-malformed-video-shape` | public carrier; upstream issue 403 |
| 10 | `Scottcjn/grazer-skill` | `grazer-negative-max-retries` | public carrier; upstream issue 403 |
| 11 | `Scottcjn/grazer-skill` | `grazer-skill-nostr-truncated-event-url` | public carrier; upstream issue 403 |
| 12 | `Scottcjn/openclaw-x402` | `openclaw-x402-backend-failure-consumes-payment` | public carrier; upstream issue 403 |
| 13 | `Scottcjn/ram-coffers` | `ram-coffers-probe-zero-iterations` | upstream issue + #520 route 403 |
| 14 | `Scottcjn/rustchain-claim-portal` | `rustchain-claim-portal-mcp-integer-overflow` | upstream issue + #520 route 403 |
| 15 | `Scottcjn/rustchain-mcp` | `rustchain-mcp-read-timeout-unhandled` | public carrier; upstream issue 403 |
| 16 | `Scottcjn/rustchain-mcp` | `rustchain-mcp-wall-clock-nonce-collision` | upstream issue + #520 route 403 |
| 17 | `Scottcjn/rustchain-monitor` | `rustchain-monitor-balance-schema-mismatch` | public carrier; upstream issue 403 |
| 18 | `Scottcjn/shaprai` | `shaprai-lifecycle-state-gate-bypass` | upstream issue + #520 route 403 |
| 19 | `Scottcjn/qb-auto` | `qb-auto-delete-line-substring` | public carrier; upstream issue 403 |

Exact carrier blobs, target SHAs, finding summaries, and per-item next actions live in `manifest.json`.
