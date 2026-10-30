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

## October 30 — ASAP actions and meaningful checkpoints

User testing showed that forcing a due date on an immediate PM action encouraged invented deadlines. Immediate actions now default to ASAP and can be saved without a date. Follow-up checkpoints, promised client updates, promised vendor responses and other dated commitments require an intentional date/time. Existing action dates remain intact and are labeled legacy dated actions rather than retroactively treated as promises.

The queue can filter active cases needing attention. Signals distinguish acknowledgment not recorded, earlier history unknown, waiting without a follow-up checkpoint, follow-up due, overdue client updates, overdue vendor responses and other overdue dated actions. Resolved/trashed cases stop generating active signals. Completing a task removes its overdue signal; it does not fabricate an acknowledgment, email sent, or client update.

The elapsed-time display starts at known case creation, not Gmail receipt. It is not an SLA score or a verified reaction time. An explicit manually reported initial_response event is needed to stop the acknowledgment-not-recorded signal. Legacy missing timestamps remain unknown. No company business-hours or response-window policy has been set.

Validation: 53 distinct API tests pass; the final suite execution took 10.322 seconds. Six added tests cover undated ASAP actions, required dates for commitments, signal removal after completion, explicit response event/clock handling, legacy unknown history/closed-case behavior and preservation of old dated actions. A local browser test saved an ASAP action without a date, defaulted responsibility from the reported actor name, displayed the waiting/checkpoint flag, and verified the saved action after reload. No new live AI evaluation was needed or run. Deployment remains pending.

Small usability changes: actor name is remembered only in page memory (not authenticated identity); action responsibility defaults to the case owner or reported actor. Timeline entries use readable descriptions rather than raw JSON. This avoids repeated typing without pretending that public-demo names are verified.

Timeline display polish: readable event names and descriptions replace raw JSON. Each entry shows the activity time and actor once; a separate 'Logged later' timestamp appears when recording differs by at least one minute. Both original timestamps remain stored. JavaScript syntax check passed.


## October 30, 2026 — Director overview and PM workspace

Added three views over the same case records: Team queue, PM workspace, and Director overview. The PM name filter matches case ownership or open action responsibility (case-insensitive); entering a name also pre-fills the reported actor for subsequent activities. This is a demo filter, not authentication or role-based authorization.

The director overview shows active case count, unassigned cases, cases without an open next action, overdue commitments, waiting without a follow-up checkpoint, and unrecorded/unknown acknowledgment history. Exception links open the existing case detail. Current workload is grouped by current owner; past response performance is not attributed to that owner.

Follow-through metrics cover retained cases excluding Trash, including resolved cases for historical commitments. Only follow-up/client-update commitments due by the viewing time enter their respective denominators. A completion is on time only when its server timestamp is on or before the due date. Future and undated ASAP actions are excluded. Median first acknowledgment uses the existing explicit human-acknowledgment interval from case creation; unknown/invalid intervals are excluded and sample counts are displayed. No SLA, arbitrary passing score, or employee ranking is invented. No date-range reporting or owner-at-event attribution is implemented yet.

Validation: Node fixture assertions cover empty data, active/resolved/Trash scopes, due-only denominators, completion cutoff, unknown history, PM matching, and priority order. JavaScript syntax checks passed. Browser checks verified director cards and PM filtering against isolated fictional records. No new AI requests, hosting resources, production dependency, or backend schema changes were introduced. Development hours were not tracked.
