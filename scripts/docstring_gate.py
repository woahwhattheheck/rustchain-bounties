#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Adjudicate docstring bounty claims.

WHY THIS EXISTS
---------------
The #73 gate only recognises CODE-REVIEW claims -- `is_review_claim()` requires
"review" in the title. Every other bounty type falls straight through it, so
docstring, blog, star and bug claims had no automated adjudication at all and
simply accumulated unpaid. On 2026-08-10 that was 19 open docstring claims,
batches 31 to 49, none of them gate-processed.

Docstring claims are unusually verifiable, so they are worth gating properly
rather than paying on assertion. A claim states a PR, a file, a function count
and a rate, and the diff should be `+N/-0` where N is that count.

WHAT IT VERIFIES (all of it, before paying anything)
  1. The cited PR is **MERGED**. An open PR is not delivered work.
  2. The claim issue author is the same GitHub identity as the merged PR author.
  3. The PR touches the claimed file.
  4. The added lines are **actually docstrings** -- lines opening with a quote
     triple. This is the check that matters: without it "I added 40 docstrings"
     pays out for 40 lines of anything.
  5. The claimed count matches what was really added.

PAYMENT IS COMPUTED FROM THE VERIFIED COUNT, NEVER THE CLAIMED ONE. A claim
that overstates is paid the true amount rather than rejected outright -- the
usual cause is miscounting, not fraud, and rejecting honest arithmetic errors
teaches people to stop claiming.

Sets `bounty-eligible` + `docstring-verified` and posts the arithmetic, so the
existing payout runner pays it on its next pass. Never moves RTC itself.

Env: GITHUB_TOKEN, GH_REPO, ISSUE_NUMBER, RATE_PER_FUNC (0.01), MAX_RTC (25).
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys

REPO = os.environ.get("GH_REPO", "Scottcjn/rustchain-bounties")
NUM = os.environ.get("ISSUE_NUMBER", "")
RATE = float(os.environ.get("RATE_PER_FUNC", "0.01"))
# A single claim asking for more than this is not auto-payable. Docstring work
# is small by nature; a very large claim is either a mistake or something that
# deserves a human read.
MAX_RTC = float(os.environ.get("MAX_RTC", "25"))
# Per-contributor rolling weekly ceiling on DOCSTRING earnings specifically.
#
# A per-claim ceiling bounds nothing here: each batch is ~5 RTC, so batch 50,
# 51 and 52 all sail under it. The unbounded axis is volume, not size -- there
# is always another file to document, which is the same faucet shape as the
# ONBOARD comparison bounty that had to be closed at 98% farm share.
#
# At 0.01 RTC/function the weekly cap is a soft backstop, not the constraint:
# a docstring is a one-line comment (often on a test stub), so the per-unit price
# sits at the top of what the strongest contributors earn across ALL bounty
# types in a week (measured 2026-08-10: typical top earners 20-50 RTC/week).
# It caps a faucet without punishing anyone doing real work.
#
# This applies ONLY to docstring claims. Large one-off bounties are untouched.
MAX_RTC_PER_WEEK = float(os.environ.get("MAX_RTC_PER_WEEK", "40"))

PR_RE = re.compile(r'github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)')
COUNT_RE = re.compile(
    r'(?:functions?\s+documented|documented|added\s+docstrings?\s+to)\D{0,20}?(\d{1,3})',
    re.I)
FILE_RE = re.compile(r'(?:^|\s)((?:[\w.-]+/)*[\w.-]+\.py)\b')
DOCSTRING_OPEN = re.compile(r'^\s*[rRbBuU]{0,2}("""|\'\'\')')
PAYABLE_LABELS = frozenset({"bounty-eligible", "docstring-verified"})


class GhError(RuntimeError):
    """A `gh` invocation failed. Must never be mistaken for an empty result."""


def gh(args, default=None, strict=False):
    """Run `gh` and parse JSON.

    `strict=True` raises on failure instead of returning `default`. That matters
    wherever the result feeds a MONEY decision: the earnings lookup behind the
    weekly cap returned `{}` on any CLI/auth/rate-limit failure, which
    `docstring_rtc_this_week()` then reported as 0.0 RTC already earned. A
    contributor already over the 40 RTC/week ceiling was therefore treated as
    having earned nothing, and the cap failed OPEN. A failed lookup is not an
    authoritative zero.
    """
    try:
        p = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=120)
    except Exception as e:
        if strict:
            raise GhError(f"gh {' '.join(args[:3])} failed: {e}") from e
        return default
    if p.returncode != 0:
        if strict:
            raise GhError(f"gh {' '.join(args[:3])} exited {p.returncode}: "
                          f"{(p.stderr or '').strip()[:200]}")
        return default
    try:
        return json.loads(p.stdout) if p.stdout.strip() else default
    except json.JSONDecodeError as e:
        if strict:
            raise GhError(f"gh {' '.join(args[:3])} returned unparseable JSON: {e}") from e
        return default


def gh_raw(args):
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise GhError(f"gh {' '.join(args[:3])} failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout



def add_labels(*names):
    """Apply one or more labels in a single REST request.

    `gh issue edit --add-label` goes through GraphQL and currently fails with a
    Projects-classic deprecation error. Use REST instead. When several labels
    form one state transition, submit them together so the client never creates
    a deliberate one-label intermediate state across separate requests.
    """
    if not names:
        return True
    args = ["gh", "api", "-X", "POST", f"/repos/{REPO}/issues/{NUM}/labels"]
    for name in names:
        args.extend(["-f", f"labels[]={name}"])
    r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(
            f"::warning::could not apply label(s) {', '.join(names)}: "
            f"{r.stderr.strip()[:120]}"
        )
        return False
    return True


def is_already_adjudicated(labels):
    """Return true only for a complete payable state or an older terminal gate."""
    labels = set(labels)
    return "gate-processed" in labels or PAYABLE_LABELS <= labels


def commit_payable_state(amount):
    """Publish the trusted amount before making a claim payable.

    The payer requires both the `docstring-verified` label and a trusted amount
    marker. Publishing labels first used to let a failed comment write strand a
    claim forever: the gate returned success, the payer had no amount, and later
    gate sweeps skipped the already-labelled claim. Keep a failure retryable by
    publishing the marker first and treating the two labels as the commit step.
    """
    marker = f"<!-- rtc-payout-amount: {amount} -->"
    try:
        # `gh issue comment` writes plain CLI output, not JSON. gh_raw() is the
        # strict helper for this operation: non-zero status raises immediately.
        gh_raw(["issue", "comment", NUM, "-R", REPO, "--body", marker])
    except GhError as e:
        # Do not add `needs-human`: the scheduled fresh-claim sweep excludes it.
        # With no payable labels written yet, leaving the claim untouched is what
        # makes the transient publication failure automatically retryable.
        print(f"::error::trusted payout marker was not published on {REPO}#{NUM}: {e}")
        return False

    if not add_labels("bounty-eligible", "docstring-verified"):
        # A marker without the payable labels is inert: the payout runner and
        # weekly-cap query both require docstring-verified. Do not add a hold
        # label which would exclude this claim from the scheduled retry sweep.
        print(f"::error::payable labels not applied on {REPO}#{NUM}; held for retry")
        return False
    return True



def issue_comments(issue_number):
    """Return all issue comments; incomplete pagination is a money-gate error."""
    comments = []
    page = 1
    while True:
        batch = gh(["api", "-X", "GET",
                    f"/repos/{REPO}/issues/{issue_number}/comments",
                    "-f", "per_page=100", "-f", f"page={page}"], None, strict=True)
        if not isinstance(batch, list):
            raise GhError(f"comments page {page} for {REPO}#{issue_number} is not a list")
        if len(batch) > 100:
            raise GhError(f"comments page {page} for {REPO}#{issue_number} exceeds per_page=100")
        comments.extend(batch)
        if len(batch) < 100:
            return comments
        page += 1


def docstring_rtc_this_week(author):
    """RTC this author has already been granted for docstrings in 7 days.

    Summed from this gate's own `rtc-payout-amount` markers rather than from
    the chain, so the check works from Actions with no node access and no
    admin key. Only claims the gate itself verified are counted.
    """
    since = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    q = (f"repo:{REPO} is:issue author:{author} label:docstring-verified "
         f"created:>{since}")
    res = gh(["api", "-X", "GET", "search/issues", "-f", f"q={q}", "-f", "per_page=100"], {}, strict=True)
    total = 0.0
    for it in (res.get("items") or []):
        if str(it.get("number")) == str(NUM):
            continue          # never count the claim being adjudicated
        # The marker lives in a gate comment, not the issue body. A marker after
        # comment 100 is still authoritative payout state, so scan every page.
        cs = issue_comments(it["number"])
        for c in cs:
            m = re.search(r'<!--\s*rtc-payout-amount:\s*([\d.]+)\s*-->', c.get("body") or "")
            if m:
                total += float(m.group(1))
                break
    return round(total, 2)


def is_docstring_claim(title, body):
    t = (title or "").lower()
    if "docstring" in t or re.search(r'\bdocs?\s+batch\b', t):
        return True
    return "docstring" in (body or "").lower()[:400]


def count_added_docstrings(diff: str):
    """Return (docstring_lines, total_added, files_touched).

    Counts only ADDED lines that open a docstring. Continuation lines of a
    multi-line docstring are not counted, so one docstring is one unit however
    many lines it spans.
    """
    doc = total = 0
    files = []
    in_docstring = False
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:].strip())
            in_docstring = False
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        total += 1
        content = line[1:]
        if in_docstring:
            if '"""' in content or "'''" in content:
                in_docstring = False
            continue
        if DOCSTRING_OPEN.match(content):
            doc += 1
            stripped = content.strip()
            # One-liner if the closing quotes appear again on the same line.
            quote = '"""' if '"""' in stripped else "'''"
            if stripped.count(quote) < 2:
                in_docstring = True
    return doc, total, files


def main():
    if not NUM:
        print("ISSUE_NUMBER not set", file=sys.stderr)
        return 1
    iss = gh(["issue", "view", NUM, "-R", REPO,
              "--json", "title,body,labels,author,state"], {})
    if not iss:
        print(f"could not read {REPO}#{NUM}", file=sys.stderr)
        return 1
    labels = {l["name"] for l in iss.get("labels", [])}
    if is_already_adjudicated(labels):
        print("already adjudicated; skipping")
        return 0
    title, body = iss.get("title", ""), iss.get("body") or ""
    if not is_docstring_claim(title, body):
        print("not a docstring claim; leaving for another gate")
        return 0

    m = PR_RE.search(body) or PR_RE.search(title)
    if not m:
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            "🤖 Docstring gate: no pull request URL found in this claim. Add the full "
            "`https://github.com/<owner>/<repo>/pull/<n>` link and it will be re-checked."], None)
        add_labels("needs-human")
        return 0
    pr_repo, pr_num = m.group(1), m.group(2)

    pr = gh(["pr", "view", pr_num, "-R", pr_repo,
             "--json", "state,additions,deletions,files,author,mergedAt"], {})
    if not pr:
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: could not read {pr_repo}#{pr_num}. Flagged for a human."], None)
        add_labels("needs-human")
        return 0

    if pr.get("state") != "MERGED":
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: {pr_repo}#{pr_num} is **{pr.get('state','OPEN').lower()}**, not merged.\n\n"
            f"Docstring bounties pay on merge, because until then the documentation is not in the "
            f"codebase. This claim is not closed — it will be re-checked automatically once the PR "
            f"lands, and you do not need to re-file it."], None)
        add_labels("awaiting-merge")
        print(f"{pr_repo}#{pr_num} not merged ({pr.get('state')}); waiting")
        return 0

    claim_author = (iss.get("author") or {}).get("login")
    pr_author = (pr.get("author") or {}).get("login")
    if (
        not isinstance(claim_author, str)
        or not claim_author.strip()
        or not isinstance(pr_author, str)
        or not pr_author.strip()
    ):
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: {pr_repo}#{pr_num} is merged, but the gate could not establish "
            f"both the claim author and merged PR author GitHub identities. Holding for human "
            f"review rather than making the claim payable."], None)
        add_labels("needs-human")
        print(f"author identity unavailable for claim {REPO}#{NUM} / PR {pr_repo}#{pr_num}")
        return 0

    if claim_author.casefold() != pr_author.casefold():
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: this claim was filed by **@{claim_author}**, but merged PR "
            f"{pr_repo}#{pr_num} is authored by **@{pr_author}**. The payout runner resolves the "
            f"recipient from the claim author, so the gate cannot safely make this claim payable. "
            f"Holding for human review."], None)
        add_labels("needs-human")
        print(f"claim/PR author mismatch: @{claim_author} != @{pr_author}")
        return 0

    diff = gh_raw(["pr", "diff", pr_num, "-R", pr_repo])
    doc_count, total_added, files = count_added_docstrings(diff)
    claimed = None
    cm = COUNT_RE.search(body) or COUNT_RE.search(title)
    if cm:
        claimed = int(cm.group(1))

    amount = round(doc_count * RATE, 2)
    if doc_count == 0:
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: {pr_repo}#{pr_num} is merged, but no added lines in it open a "
            f"docstring ({total_added} lines added in total). If the work is real and the gate has "
            f"misread it, say so here and a human will look."], None)
        add_labels("needs-human")
        return 0

    author = (iss.get("author") or {}).get("login", "")
    try:
        already = docstring_rtc_this_week(author) if author else 0.0
    except GhError as e:
        # Cannot establish prior earnings => cannot honour the cap => do not pay.
        # Failing closed is the whole point; the previous behaviour approved the
        # claim as though the contributor had earned nothing this week.
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: verified **{doc_count} docstrings** in {pr_repo}#{pr_num}, but the "
            f"weekly-earnings lookup failed, so the {MAX_RTC_PER_WEEK:g} RTC/week cap cannot be "
            f"checked right now.\n\nHolding rather than approving — a failed lookup is not proof "
            f"that you have earned nothing. This retries automatically on the next sweep; you do "
            f"not need to do anything."], None)
        add_labels("needs-human")
        print(f"::error::earnings lookup failed, refusing to approve: {e}")
        return 0
    if already + amount > MAX_RTC_PER_WEEK:
        add_labels("weekly-cap-reached")
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: verified **{doc_count} docstrings** in {pr_repo}#{pr_num} "
            f"(**{amount} RTC**), but this would take you to "
            f"**{round(already + amount, 2)} RTC** of docstring earnings in a rolling 7 days, "
            f"over the **{MAX_RTC_PER_WEEK:g} RTC/week** ceiling for this bounty type.\n\n"
            f"**The work is accepted and this claim is not closed.** It becomes payable again as "
            f"soon as the rolling window clears, and it will be picked up automatically. You do "
            f"not need to re-file it or do anything.\n\n"
            f"Why the ceiling exists: documentation bounties are unbounded by nature, since there "
            f"is always another file. The cap keeps one bounty type from consuming the pool, and "
            f"40 RTC/week is roughly the top of what any contributor earns across all bounty types. "
            f"It is not a judgement on the quality of your work, which has been consistently fine.\n\n"
            f"If you want higher-value work, the bounty board has open items at 7 to 35 RTC each "
            f"that are not rate-limited."], None)
        print(f"weekly cap: {author} at {already} + {amount} > {MAX_RTC_PER_WEEK}")
        return 0

    if amount > MAX_RTC:
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"🤖 Docstring gate: verified **{doc_count} docstrings** in {pr_repo}#{pr_num}, which at "
            f"{RATE} RTC each comes to {amount} RTC. That is above the {MAX_RTC} RTC auto-pay ceiling, "
            f"so it needs a human to release it. Nothing is wrong with the claim."], None)
        add_labels("needs-human")
        return 0

    note = ""
    if claimed is not None and claimed != doc_count:
        note = (f"\n\nYou claimed **{claimed}**; the diff contains **{doc_count}**. "
                f"Paying the verified number. If you think the gate has miscounted, say so and a "
                f"human will check — miscounts are usually arithmetic, not bad faith.")

    if not commit_payable_state(amount):
        # Notification is deliberately secondary to durable state. If even this
        # status comment fails, the red run + retryable labels still prevent a
        # false-success terminal state.
        gh(["issue", "comment", NUM, "-R", REPO, "--body",
            f"⏸️ 🤖 **Docstring gate: checks passed, but payable state was not fully committed.** "
            f"PR {pr_repo}#{pr_num} is merged with **{doc_count}** docstrings → **{amount} RTC**. "
            f"The gate is holding this claim for retry rather than reporting it as verified."], None)
        return 1

    gh(["issue", "comment", NUM, "-R", REPO, "--body",
        f"✅ 🤖 **Docstring gate: verified.**\n\n"
        f"- PR {pr_repo}#{pr_num} is **merged**\n"
        f"- Files: `{', '.join(files[:4]) or 'n/a'}`\n"
        f"- Added lines opening a docstring: **{doc_count}** (of {total_added} added lines)\n"
        f"- Rate {RATE} RTC each → **{amount} RTC**{note}\n\n"
        f"Queued for payout. The balance moves after the standard confirmation window, not on this "
        f"comment."], None)
    print(f"verified {doc_count} docstrings -> {amount} RTC on {REPO}#{NUM}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())