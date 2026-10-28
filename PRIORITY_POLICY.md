# Priority policy v2

This prototype supports a small B2B support team. An agent reviews reported facts; AI suggests ratings; fixed rules calculate priority. It is not an emergency-response service or a production ticketing system.

## Ratings and priority

A complete operational shutdown (Critical business impact) is P1 for every customer tier. A workable alternative means the agent should reconsider whether impact is truly Critical. Customer size cannot demote a complete shutdown.

For other cases add tier (Low=1, Medium=2, High=3), impact (Low=1, Medium=2, High=3), and urgency (Low=1, Medium=2, High=3, Urgent=4, Critical=5). Totals 3–4 yield P4; 5–7 P3; 8–10 P2; 11–12 P1. Revenue bands are example policy, not verified customer data or a universal support standard.

Urgency describes when the support response/action is needed. An estimated six-month rebuild does not establish when support is needed. Ask for that deadline rather than infer Low urgency. Missing evidence remains unknown. Conflicting answers require clarification. An extinguished fire does not establish an active emergency.

| Reported facts and reviewed choices | Result |
| --- | --- |
| All production stopped; Low tier; help today (Urgent) | P1: shutdown override |
| High impact; Low tier; help today (Urgent) | P2: total 8 |
| Medium impact; Low tier; within one week (High) | P3: total 6 |
| Minor inconvenience; Low tier; more than two weeks | P4: total 3 |
| Six-month restoration estimate; no response deadline | AI must clarify urgency; no complete AI priority preview |

Legacy records retain their saved priority. Their explanation flags a difference from v2; reviewing and saving recalculates it. Status changes alone do not silently reclassify cases. The queue groups by priority, with equal-priority records in their existing order; it does not promise SLA or deadline ordering.

## Finish a case

Active includes Open and In progress. Resolve moves a case into Resolved. Reopen returns it to Open. Move to Trash requires confirmation and preserves the record. Restore brings it back as Resolved; reopen separately if work is needed. There is no permanent-delete endpoint.

## Public demo limits

DEMO_MODE defaults to true. Limits are global for all visitors: 40 AI attempts/day, 5/minute, two concurrent requests, 20 creations/day, 5 creations/minute, 40 active records, and 100 stored records including Trash. AI failures consume attempts. UTC daily counters persist in a sidecar beside CASES_FILE; the persistent disk must hold both files. Override the DEMO_* variables in demo_controls.py if needed. These caps bound request volume, not a dollar spend guarantee; model costs and tokens still matter.

Use one worker and one service instance with the JSON store. This anonymous shared demo lets any visitor resolve or trash fictional entries. It is not suitable for confidential customer data. Trash does not free the stored-record allowance; owner maintenance is needed when the demo reaches capacity. Do not erase live records without a backup and an explicit decision.
