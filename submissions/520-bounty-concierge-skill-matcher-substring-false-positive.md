# Bounty #520 bug report: skill matcher accepts incidental substrings as full skill matches

Target: `Scottcjn/bounty-concierge`

Pinned target main: `8af8fdf80b3dc3816d3e13f4e99e2a1cab331cbc`

Pinned file: `concierge/skill_matcher.py`

Pinned blob: `2598f828962986131b74ab1834d255181edad032`

Bounty: `Scottcjn/rustchain-bounties#520` (Bug Hunter, multi-claim)

## Summary

`concierge.skill_matcher.match_skills()` uses raw substring membership for each skill keyword. As a result, unrelated words can count as exact skill matches and give an irrelevant bounty a perfect score. Because `recommend()` sorts on that score, incidental substrings can distort the opportunity ranking.

This report is pinned to the target source above. A fresh read immediately before publication confirmed the target main and blob were unchanged.

## Environment

- Linux
- Python 3.x
- Deterministic local reproduction; no network service required
- Source pinned to `Scottcjn/bounty-concierge@8af8fdf80b3dc3816d3e13f4e99e2a1cab331cbc`

## Steps to reproduce

Using the pinned module:

```python
from concierge import skill_matcher

print(skill_matcher.match_skills(
    {"title": "Trusted execution payout lane"}, ["rust"]
))
print(skill_matcher.match_skills(
    {"title": "Contest winner"}, ["testing"]
))
print(skill_matcher.match_skills(
    {"title": "Poster design"}, ["social-media"]
))
```

Observed output:

```text
1.0
1.0
1.0
```

The same predicate can be reduced directly from the current implementation:

```text
"rust" in "trusted"  -> True
"test" in "contest"  -> True
"post" in "poster"   -> True
```

## Expected result

All three examples should score `0.0`. None of the descriptions contains the corresponding skill keyword as a word or phrase:

- `trusted` is not the Rust language or Rust tooling;
- `contest` is not a testing task;
- `poster` is not a social-media post.

## Actual root cause

Current `match_skills()` logic:

```python
for skill in skills:
    keywords = SKILL_TAGS.get(skill.lower(), [skill.lower()])
    if any(kw in text for kw in keywords):
        matched += 1
```

Relevant default keywords include:

```python
"rust": ["rust", "cargo", "crate"]
"social-media": ["star", "share", "tweet", "post", "upvote", "review"]
"testing": ["test", "pytest", "coverage", "benchmark"]
```

The tests on target main exercise positive keyword matches, unknown-skill fallback, fractional scoring, sorting, and input immutability, but do not include negative boundary cases such as `trusted`, `contest`, or `poster`.

## Impact

A bounty that has no requested Rust, testing, or social-media skill can still receive a full `1.0` match for those categories. `recommend()` then sorts by `match_score`, so false positives can rank an irrelevant paid opportunity alongside or above a genuinely relevant one.

This is a functional ranking bug, not a security finding.

## Suggested repair

Match keywords as words/phrases rather than arbitrary substrings while preserving multi-word entries such as `github actions` and `red team`. Add regression tests that keep current positive cases green while asserting at minimum:

```python
assert match_skills({"title": "Trusted execution payout lane"}, ["rust"]) == 0.0
assert match_skills({"title": "Contest winner"}, ["testing"]) == 0.0
assert match_skills({"title": "Poster design"}, ["social-media"]) == 0.0
```

A boundary-aware regular expression or token/phrase matcher would both address the defect; the implementation choice should preserve punctuation-separated legitimate matches such as `Rust-based`, `post/review`, or `test-driven` according to the intended matching policy.

## Duplicate check

Immediately before taking this lane, repository issue and PR searches for `skill matcher substring false positive word boundary` returned no matching report or patch. Slack search for `skill_matcher` surfaced unrelated downstream opportunity-ranking work, not ownership of this defect.

## Submission routing

Direct `/claim` on `Scottcjn/rustchain-bounties#520` and direct issue creation on `Scottcjn/bounty-concierge` both returned GitHub `403 Resource not accessible by integration`. The sponsor's published `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a repository controlled by the contributor as a fallback for this connector-specific 403. This report is that public, timestamped fallback artifact. No bounty acceptance or payout is asserted here.
