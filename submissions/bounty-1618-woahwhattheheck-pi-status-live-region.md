# Bounty #1618 submission — BoTTube Pi status live-region gap

Claimant / payout route: `woahwhattheheck`

Immutable evidence report:
https://github.com/woahwhattheheck/startup-credits/blob/2507ce36d442dc82d523b04cd38c94b800d2beee/bounty-evidence/bottube-1618-pi-status-live-region.md

Checked target source: `Scottcjn/bottube@00973f5b3d2098ad42404afb0cce3945d1eead85`.

Finding: `bottube_templates/pi_home.html` exposes `#pi-status` and `#pi-setup-status` as plain `<span>` elements. `piSignInUI()` and the `pi:authenticated` event asynchronously change `#pi-status`; `bottube_static/pi_pay.js::_payStatus()` asynchronously changes `#pi-setup-status` throughout Pi payment authorization, approval, completion, cancellation and error paths. Neither target has `role="status"`, `aria-live`, `aria-atomic`, or an equivalent status-message mechanism, and focus is not moved to the changed text.

Impact: screen-reader users can start the sign-in/payment flow but receive no automatic announcement of progress, failure, cancellation or completion even as visible text changes. WCAG 2.1/2.2 relevance: 4.1.3 Status Messages (AA).

Suggested repair: expose the concise status elements as polite atomic status/live regions; reserve assertive alerts only for errors that require interruption.

Duplicate check immediately before submission: current #1618 history contained no `pi-status`, `pi-setup-status`, `piSignInUI`, `_payStatus`, or Pi Browser workflow report; fresh `Scottcjn/bottube` issue search found no matching report; Slack coordination/delegation exact-lane searches were clean.

Submission transport: direct `/claim` and direct complete issue comment both returned `403 Resource not accessible by integration`. The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents claimant-controlled report publication and a file/PR carrier as fallbacks for this connector-specific 403. This file is the PR carrier for the same single paid lane; it makes no source fix or additional bounty claim.

Requested bounty: **1 RTC**, subject to maintainer validation. No native RTC address is invented; use the contributor/GitHub route for `woahwhattheheck` if accepted.
