# How Case Triage was built

## The problem

Support agents receive issue descriptions that vary in detail and urgency. A queue needs a consistent way to separate a cosmetic issue from a workflow failure or a complete outage. An AI-generated label alone does not explain what to do or whether the input supports that decision.

## The starting point

The project began as a Python case-management application with a CLI, a Case model, JSON persistence, a priority calculator, four FastAPI routes, and an OpenAI summary function. The first web release preserved that foundation and added plain HTML, CSS, and JavaScript served by FastAPI. It was deployed from GitHub to Render with a persistent disk.

## The next design decision

A summary button demonstrated API integration but did little to help an agent triage. The assistant was expanded to propose business impact and time sensitivity, explain its reasoning with quotes from the issue, identify missing information, and suggest one next action. Customer tier remains a company policy input. Final priority is calculated by deterministic rules so that the resulting decision can be reproduced.

The old rules are a starting rubric, not evidence that this is the best policy for every support team. A future version could compare alternative policies or an AI priority recommendation against representative cases before changing production behavior.

## What makes the workflow reviewable

1. The agent enters an issue or opens an existing case.
2. The AI returns a structured proposal, not a saved decision.
3. The UI displays reasons and exact evidence quotes alongside editable ratings.
4. If evidence is missing, the AI can leave a rating unanswered and ask a question. The UI leaves unanswered ratings unselected. Agents can answer follow-up questions in place and reassess with the added context.
5. The agent reviews both ratings and explicitly applies the result. On an intake form, case creation is still a separate step.
6. Saving an existing-case review recalculates priority. A conflicting update is rejected so an old review cannot silently overwrite a newer one.

## Reliability measures and their limits

- Structured Outputs and Pydantic constrain response fields and allowed labels.
- Instructions separate the task policy from the issue text and tell the model to treat embedded commands as untrusted data.
- The server checks that supporting evidence quotes occur verbatim in the description.
- Missing information can produce an abstention instead of a forced rating.
- AI suggestions do not automatically change cases or customer tier.
- Atomic JSON writes and a single worker support the small V1 deployment.

These measures do not prove the model's reasoning is correct. A valid quote can still support a debatable conclusion, and a small prompt-injection smoke test does not establish comprehensive resistance. The application has no authentication, audit history, or production-grade abuse controls. Public demos should use fictional data.

## What was tested

The initial ten deterministic API tests cover input validation, missing credentials, structured responses, invalid or invented evidence, unanswered ratings, preview without mutation, reviewed-save persistence, failed-write rollback, concurrent review conflicts, and missing cases. The original backend regression checks cover all 60 priority combinations, existing routes, summary response/error paths, 20 concurrent creates, and JSON reload.

Browser testing verified suggestion → review → apply → create, then an existing-case human revision from Critical impact to High and a resulting priority change from P1 to P2.

The first live-model evaluation used eight synthetic support issues. Seven matched the expected impact and urgency labels. The dispatch case did not: the expected impact was High, while the AI selected Medium because manual assignment was still possible. Its reasoning was grounded but disagreed with the test label. This exposed an ambiguous policy boundary and is a reason to retain human review. The original result is preserved in evals/latest-results.json.

This is a small development evaluation, not a production accuracy estimate. No real customer records were used.

## Closing the clarification loop

A demo user identified a real gap: the AI asked useful questions, but there was nowhere to answer them. This led to answer fields below each question and a **Reassess with answers** action. Intake answers stay with the form until a case is created; an existing case can save answers without changing its ratings. Applying a reviewed assessment can save both ratings and context.

The original description remains intact. Saved Q&A is visible on reopening and included in later assessments and summaries. The server checks quotes against actual description/answer text, not against the wording of a question. Unknown ratings no longer default to Low. An explicit selection and human confirmation are required before applying ratings.

Eight additional API tests exercise persistence, compatibility, optimistic conflicts, validation, rollback, answer evidence, and summary context. All 18 deterministic API tests pass. A live synthetic browser check starts with an underspecified raw-material-cost issue, answers the follow-up questions, and verifies reassessment using those answers.

## Tradeoffs

Plain web technologies and JSON kept the first release small and deployable. JSON requires one service instance and one worker. AI reasoning and next actions remain transient rather than stored in an audit record. Customer clarification questions and answers are saved separately from the original issue and included in subsequent assessments and summaries. There is no retrieval system or agent framework because this version does not need either to accomplish its workflow.

## What would come next

- Expand the evaluation set and have support practitioners review ambiguous labels.
- Define how workarounds, affected customer counts, and commercial commitments should influence triage.
- Preserve human-reviewed decisions and explanations in an audit history.
- Add access and usage controls before using real customer information or broader public traffic.
- Measure whether suggestions reduce triage effort and whether agents accept or change them; these outcomes have not yet been measured.

## Development transparency

Jon Staab supplied the original case-management project and priority logic and directed the product's scope and deployment. AI-assisted tools supported frontend/backend implementation, debugging, test creation, and documentation. This case study describes implemented behavior and observed checks; it does not claim independent manual authorship of every line or production reliability.

## Workbench iteration

Testing exposed a missing lifecycle and a confusing multi-step save flow. The update adds active/resolved/Trash views, reversible removal, one-step reviewed intake saving, and an explanation when a saved legacy priority differs from the revised policy. Complete operational shutdowns now receive P1 regardless of tier. See PRIORITY_POLICY.md for policy and limits.

The AI review separates essential clarification from optional investigation: once both ratings have support, the interface is ready for review. Unknowns remain unknown. Public demo counters limit requests globally and persist beside the case file, using the existing single-worker architecture. This bounds usage without adding authentication or a database. Anonymous access remains a deliberate demo limitation.

## October 30: measure follow-through before measuring outcomes

A user walkthrough exposed a product distinction: fast resolution and good project management are not the same outcome. A PM can promptly acknowledge an issue, pursue missing vendor information and update a client even while a repair or replacement remains outside the PM's control.

The next iteration records those steps explicitly. Cases now have an owner; actions have a responsible party, waiting-on contact, due time and completion outcome. The timeline separately records human acknowledgment, information requests, follow-up, information received and client updates. System transitions and manually reported actions carry distinct sources. Each event retains reported occurrence time and server recording time; old cases are not given invented past activity.

This foundation was built before connecting a live inbox so emails can later supply source events to a consistent record. The local API suite now passes 47 tests. Seven workflow tests cover persistence, timestamps, legacy records, conflicts and failed-write rollback. Full details and a dated release history are in DEVELOPMENT_LOG.md. Active development hours were not tracked, and test-suite execution time must not be presented as development duration.

There is no employee KPI dashboard yet. The next measurement design will focus on time to acknowledgment, pursuit of missing information and updates to the client, with explicit handling for unknown timestamps and external waiting time. Public demo activity and reported actor names are not verified evidence of employee performance. This remains a prototype, not a tamper-proof audit system.
