# Development and validation log

This log separates implementation milestones, observed tests, live deployment and future work. Dates are session milestones, not a timesheet. Total active engineering hours and a continuous development duration were not tracked; no claim about them is made.

| Date | Change and reason | Evidence and status |
| --- | --- | --- |
| 2026-10-27 | Plain HTML/CSS/JS frontend added around existing FastAPI/JSON/CLI foundation; AI review evolved beyond a summary button. | Initial 10 API tests; historical live evaluation retained in evals/latest-results.json (7/8). Small synthetic sample, not production accuracy. |
| 2026-10-28 | Answer clarification questions and reassess without losing source text. | 18 tests passed at that milestone; user tested the deployed workflow. |
| 2026-10-28 | Case lifecycle, recoverable Trash, single-step reviewed intake, shutdown priority override and shared-demo limits. | 28 tests passed; matrix covers all 60 tier/impact/urgency combinations. Six newer synthetic AI scenarios passed 4/6; two abstained on next-month urgency instead of expected Low. User confirmed live queue views worked. |
| 2026-10-28 | Optional private Gmail draft intake and read-only Apps Script connector. | 40 API tests passed; connector checked offline with mocked Gmail/HTTP. Real Gmail authorization, timed delivery and private deployment remain pending. No inbox is connected by these tests. |
| 2026-10-30 | Added case ownership, action responsibility/deadlines, completion outcomes and recorded activity timeline before live email integration. | 47 API tests pass locally. The most recent verbose run reported 6.801 seconds for the test suite; that is execution time, not development time or API response latency. This release is not yet deployed. |

## Ownership/timeline design

PM responsiveness is different from total resolution speed. A vendor may delay recovery while the PM promptly acknowledges, requests information, follows up and informs the client. The new record therefore separates first human acknowledgment, information requested, follow-up, information received, client update, resolution note and general note/correction.

Each case has an owner. Each action has a description, responsible person, optional waiting-on party, due time and completion outcome. The PM can own follow-through while a vendor owes an answer. Due dates are human-entered commitments; AI does not invent them.

Activity events contain actor, source, reported occurrence time and server recording time. Manual backdated events retain their later recording timestamp. Future occurrence times beyond five minutes of clock tolerance and timezone-free API dates are rejected. Browser inputs use the user's local timezone and serialize UTC. Historical actions on legacy cases remain unknown; loading an old case does not invent an acknowledgment or creation event.

Status changes and assessment/context saves add system events. Manual communication entries are reported by the user; the app does not send an email or verify that an external communication actually occurred. An AI suggestion is not counted as a human response. Timeline entries cannot be edited/deleted through the API; corrections can be appended as notes. JSON files are editable by the server owner, and public-demo names are unverified. This is an application activity history, not a tamper-proof compliance audit or verified employee performance record.

## Current test coverage

Run from the project folder: `python -m unittest discover -s tests -v`.

The 47 API tests include the earlier triage, grounding, clarification, lifecycle, private access, Gmail delivery/retry and demo-budget cases. Seven new workflow tests cover creation versus legacy history, owner persistence and stale conflicts, action assignment/completion, separate occurrence/recording times, invalid dates and empty names, failed-write rollback, and retention of ownership/history across existing assessment and status changes. JavaScript syntax checks pass for the new workflow script. No new live AI evaluation was run for this deterministic feature change.

Pending: browser acceptance on the deployed release; verify owner assignment, requesting a vendor commitment, recording a client update, completing an action, resolving/reopening and persistence after reload/restart. Use fictional records in the public demo. Review existing privacy boundaries before real-user trials.

## Next: KPI calculations, not yet implemented

Candidate intervals: issue received to first human acknowledgment; receipt to first information request; follow-up due to actual follow-up; information received to client update; and proportion of due actions completed on time. A completed task alone does not prove the client received an update; log that activity separately.

Define business hours, timezone, ownership changes, waiting periods, reopened cases and corrections before aggregating. Missing starting events must show insufficient data, never zero minutes. Show whether times are source-derived or manually reported. Avoid an employee ranking from a small or unverified sample. No PM performance improvement, customer satisfaction uplift or hours saved has yet been measured.

## Reference approach

Vantaca Scout's guide describes source citations and user feedback: https://support.vantaca.com/hc/en-us/articles/32820943372571-Scout-User-Guide . The exact chatbot development/rollout article recalled by the user was not located in this search.

Vanta (a different company) describes evaluation datasets and feedback loops: https://www.vanta.com/resources/vanta-ai-quality-evaluation-maturity-model . These are references for transparent explanation, not proof that this prototype meets either company's standards. No affiliation or endorsement is claimed.
