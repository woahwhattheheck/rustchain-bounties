# Bounty #1618 — BoTTube Agents sort state is visual-only

Bounty: https://github.com/Scottcjn/rustchain-bounties/issues/1618  
Affected UI: https://bottube.ai/agents  
Source verified: `Scottcjn/bottube@6af6b63f7a5a87353a30cd4552dc5c0e183a96af`  
Source path: `bottube_templates/agents.html`

## Finding

The Agents directory exposes three sort links — **Most Videos**, **Newest**, and **A-Z** — but the selected sort is communicated only by the CSS class `active`:

```html
<a ... class="{% if sort == 'videos' %}active{% endif %}">Most Videos</a>
<a ... class="{% if sort == 'recent' %}active{% endif %}">Newest</a>
<a ... class="{% if sort == 'name' %}active{% endif %}">A-Z</a>
```

None of the links exposes `aria-current` or another programmatic current-state attribute, and the sort-link group has no accessible label.

## Impact

A screen-reader user can hear and activate all three sort links, but cannot determine which ordering is currently applied to the agent results. Sighted users receive that state from the active styling.

WCAG relevance: **1.3.1 Info and Relationships** and **4.1.2 Name, Role, Value**.

## Suggested fix

Set `aria-current="page"` on the active sort link (or another appropriate programmatic current-state token), and optionally expose the set as a labelled navigation region such as:

```html
<nav class="sort-tabs" aria-label="Agent sort order">
  ...
</nav>
```

## Verification and duplicate check

- Fresh BoTTube `main` was read at `6af6b63f7a5a87353a30cd4552dc5c0e183a96af`.
- The live `/agents` route renders the same three sort choices.
- Immediately before submission, the current #1618 comment history was checked for `/agents`, `Most Videos`, `sort-tabs`, and the Agents-directory sort state; no matching report was found.
- The existing `aria-current` report in #1618 concerns navigation on `rustchain.org`, not the BoTTube Agents sort selector.

## Submission status

A direct #1618 issue-comment submission was attempted first and returned GitHub `403 Resource not accessible by integration`. The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly permits publishing a document/report in a repository the contributor controls when that connector-specific 403 occurs, and also permits opening a pull request when the deliverable is a file.

Claimed amount: **1 RTC**, subject to maintainer validation.
