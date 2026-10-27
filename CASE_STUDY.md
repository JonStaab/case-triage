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
4. If evidence is missing, the AI can leave a rating unanswered and ask a question. The UI clearly identifies retained human choices.
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

Ten deterministic API tests cover input validation, missing credentials, structured responses, invalid or invented evidence, unanswered ratings, preview without mutation, reviewed-save persistence, failed-write rollback, concurrent review conflicts, and missing cases. The original backend regression checks cover all 60 priority combinations, existing routes, summary response/error paths, 20 concurrent creates, and JSON reload.

Browser testing verified suggestion → review → apply → create, then an existing-case human revision from Critical impact to High and a resulting priority change from P1 to P2.

The first live-model evaluation used eight synthetic support issues. Seven matched the expected impact and urgency labels. The dispatch case did not: the expected impact was High, while the AI selected Medium because manual assignment was still possible. Its reasoning was grounded but disagreed with the test label. This exposed an ambiguous policy boundary and is a reason to retain human review. The original result is preserved in evals/latest-results.json.

This is a small development evaluation, not a production accuracy estimate. No real customer records were used.

## Tradeoffs

Plain web technologies and JSON kept the first release small and deployable. JSON requires one service instance and one worker. AI reasons, questions, and next actions are currently transient rather than stored in an audit record. There is no retrieval system or agent framework because this version does not need either to accomplish its workflow.

## What would come next

- Expand the evaluation set and have support practitioners review ambiguous labels.
- Define how workarounds, affected customer counts, and commercial commitments should influence triage.
- Preserve human-reviewed decisions and explanations in an audit history.
- Add access and usage controls before using real customer information or broader public traffic.
- Measure whether suggestions reduce triage effort and whether agents accept or change them; these outcomes have not yet been measured.

## Development transparency

Jon Staab supplied the original case-management project and priority logic and directed the product's scope and deployment. AI-assisted tools supported frontend/backend implementation, debugging, test creation, and documentation. This case study describes implemented behavior and observed checks; it does not claim independent manual authorship of every line or production reliability.
