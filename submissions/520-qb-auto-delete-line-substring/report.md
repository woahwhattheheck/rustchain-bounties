# Bug Hunter report: `qb-auto` can delete the wrong invoice line

Upstream: `Scottcjn/qb-auto`

Pinned upstream commit: `d509e7564f8c5622cb10be0e8761eba6cc240201`

Sponsor bounty: `Scottcjn/rustchain-bounties#520` (Bug Hunter, multi-claim)

## Summary

`qb_delete_line_item(invoice_num, line_number)` uses an unanchored accessible-name regex for the destructive line-delete control and then resolves all matches with `.first`:

```python
delete_btn = page.get_by_role("button", name=re.compile(rf"Delete line {line_number}"))
await delete_btn.first.click()
```

The repo's `actions.js` path has the same class of selector:

```javascript
const deleteBtn = page.getByRole('button', {
  name: new RegExp(`Delete line ${DELETE_LINE}`)
});
```

For `line_number = 1`, the pattern also matches `Delete line 10`, `Delete line 11`, and so on. If a longer-numbered control is earlier in locator order, or if the exact line-1 control is absent while line 10 exists, `.first` can select the wrong destructive control and the Python workflow proceeds to save the invoice.

This is closely analogous to the substring transaction-number bug already fixed in the same upstream commit by `txn_name_pattern()` / `resolve_txn_button()`: invoice `685` must not match invoice `6850`, but the line-delete selector still lacks the equivalent exact-boundary and uniqueness fence.

## Reproduction

No live QuickBooks mutation is required. The exact regex used in `server.py` demonstrates the collision:

```python
import re

pat = re.compile(r"Delete line 1")
names = ["Delete line 10", "Delete line 11", "Delete line 1"]
print([name for name in names if pat.search(name)])
# ['Delete line 10', 'Delete line 11', 'Delete line 1']

names = ["Delete line 10", "Delete line 1"]
print(next(name for name in names if pat.search(name)))
# Delete line 10
```

Observed locally:

- OS: Linux 6.18.44 x86_64, glibc 2.41
- Python: 3.13.5
- Output 1: `['Delete line 10', 'Delete line 11', 'Delete line 1']`
- Output 2: `Delete line 10`

## Expected

A request to delete line `1` should target exactly one control named `Delete line 1`. Missing or ambiguous exact matches should fail closed before a click or save.

## Actual

The unbounded regex matches longer line numbers sharing the prefix and the Python implementation explicitly chooses `.first`, turning an ambiguous selector into a potentially wrong invoice mutation.

## Suggested fix

Use an exact/bounded name pattern (for example `^Delete line <escaped-number>$`) and require exactly one match before clicking. Apply the same rule in `actions.js`. Add a regression where `Delete line 10` appears before `Delete line 1`, plus a case where only `Delete line 10` exists and requesting line 1 must refuse to act.

## Duplicate / collision checks

Before publication:

- Slack search for `qb-auto`: zero current claims/results in the connected workspace.
- Upstream issue searches for `Delete line`, `line item`, `line_number`, `wrong line`, and `substring`: no matching issues.
- The connected GitHub integration does not have write permission on `Scottcjn/qb-auto`; direct proper issue creation was attempted and returned HTTP 403 `Resource not accessible by integration`.

This file is therefore a public fallback artifact preserving a complete issue-quality report until an upstream-writable credential or human can file it in `Scottcjn/qb-auto` and link that issue on bounty #520.

## Bounty status

**Not claimed as paid / 0 RTC counted.** The bounty acceptance text requires a proper upstream issue plus a link on `Scottcjn/rustchain-bounties#520`; the available GitHub App cannot perform those sponsor-repo writes. This fallback does not pretend otherwise.
