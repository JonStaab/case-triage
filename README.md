# Case Triage

A support triage prototype for small B2B support and customer success teams. Agents record customer issues, assess business impact and urgency using concrete definitions, and review a queue sorted by calculated priority. An AI triage assistant suggests impact and urgency, cites exact evidence from the issue, asks missing questions, and recommends a next action. Agents review and edit suggestions before applying them. Optional AI summaries remain available.

Built with FastAPI, plain HTML/CSS/JavaScript, JSON persistence, and the OpenAI Responses API. This is a portfolio prototype, not a production support platform.

Read the [development case study](CASE_STUDY.md) for design decisions, reliability checks, evaluation results, and AI-assisted development disclosure. The app also links to a public case-study page.

## Triage decisions

The customer supplies the facts; a support agent selects impact and urgency. Customer tier follows company policy. This prototype preserves its original example revenue bands: Low under $5m, Medium $5m–$10m, High over $10m annual revenue.

Priority adds the tier score (1–3), impact score (1–4), and time sensitivity score (1–5): totals 3–4 are P4, 5–7 P3, 8–10 P2, and 11–12 P1. Critical business impact always yields P1, regardless of tier or urgency (policy v2). AI proposes impact and urgency using the rubric, while the human decides what to apply. The original issue remains visible and the final priority is calculated by the rules above.

## AI triage assistant

Use **Suggest triage** on the intake form or an existing case. The assistant returns suggested business impact and time sensitivity, concise reasons, supporting quotes, up to five clarification questions, and a suggested next action. It can leave either rating unanswered when the description lacks evidence. The model does not set customer tier or directly decide final priority. Unanswered ratings show Select a rating, not Low; the intake form also starts with unselected impact/urgency fields.

Review both dropdowns, check the confirmation, then **Save reviewed case**. This saves intake and answers in one step. Existing-case reviews save only the reviewed impact/urgency and recalculate priority. A stale review receives a conflict response rather than overwriting another update, including changes to saved clarification answers. Editing intake fields invalidates an old suggestion.

The integration uses OpenAI Structured Outputs (`responses.parse` with a Pydantic schema). Issue descriptions are treated as untrusted data, not instructions. The server rejects supporting quotes that do not occur verbatim in the issue. These checks validate structure and evidence presence, not the correctness of the reasoning. Requests are on demand, with no automatic retries for triage and `store=False`. Your existing OPENAI_API_KEY and OPENAI_MODEL settings work; no new production dependency is needed.

### Evaluation and tests

Install optional test dependencies: `pip install -r requirements-dev.txt`.
Run deterministic API tests: `python -m unittest discover -s tests -v`.
Run the paid, synthetic live-model evaluation: `python evals/evaluate_triage.py`.

The initial live run scored **7/8** on expected impact/urgency ratings. Outage, cosmetic issue, vague issue, missing deadline, instruction injection, deadline without impact, and partial restriction passed. In the dispatch case, the expected High impact was returned as Medium because manual assignment remained possible; the reasoning was grounded, but disagreed with the expected label. The original result is retained in `evals/latest-results.json`. This small smoke evaluation is not a production accuracy estimate or a guarantee against prompt injection. No real customer records are used.

The original ten API tests cover structured response handling, abstention, validation, missing key, invalid evidence/refusal, unchanged previews, reviewed save/persistence, disk failure rollback, concurrent review conflict, and missing cases. Browser checks cover intake suggestion/review/apply/create and an existing-case human revision from Critical to High, with priority recomputed from P1 to P2.

## Fictional demo

`demo-cases.json` contains three fictional examples: a P1 checkout outage, a P2 dispatch workflow issue, and a P4 cosmetic report issue. Existing private case data is not included.

To try the demo without changing your cases.json, run from this project's folder in PowerShell:

    $env:CASES_FILE = Join-Path (Get-Location) "demo-cases.json"
    python -m uvicorn Case_Management:app --host 127.0.0.1 --port 8767 --workers 1

Open http://127.0.0.1:8767. New cases in that session are saved to demo-cases.json. Stop the server and remove the override (`Remove-Item Env:CASES_FILE`) before running against your normal cases again.

## Validation

Verified create/list/detail flows in a browser, JSON persistence after a server restart, all 60 priority combinations, invalid-input handling, missing-case responses, summary response/error handling, failed-save rollback, and concurrent creates. Live summary generation was also confirmed locally after setting an API key.

## Known limits

No authentication, full audit history, or saved AI suggestions/summaries. Global request/creation caps now protect the shared demo; they are not access controls. Customer clarification questions and answers are saved separately from the original description. Humans can revise impact and urgency after AI review; there is no direct priority override. JSON requires one service instance and one worker. A public deployment lets visitors read/create cases and request AI suggestions and summaries using the server's API key. Use fictional data for a public demo.

## Windows quick start

Double-click Start-Case-Triage.cmd. It loads OPENAI_API_KEY from your saved Windows user environment and starts the server at http://127.0.0.1:8766. Keep the window open. If the app is already running, the launcher opens it in your browser. It never contains or prints the key. Install requirements first as described below.

## Local run (Python 3.13)

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    $env:OPENAI_API_KEY = "your-key"
    uvicorn Case_Management:app --reload

Open http://127.0.0.1:8000. API docs: /docs. The app works without an API key; summary requests then show a useful error. Environment variables must be set in the shell or hosting dashboard; .env files are not automatically loaded. Never commit a real key.

CLI remains available with `python Case_Management.py`. Stop the web server before using the CLI to edit the same JSON file.

## Storage

Existing cases.json and Case fields remain compatible. Cases with answers include an optional clarifications list (question/answer pairs); older records without it still load. The original issue_description is preserved. CASES_FILE optionally sets an absolute JSON path; the default is cases.json beside the Python module. New installations start empty. Writes use atomic replacement, and API creates are serialized in one process. Run exactly ONE worker and ONE service instance. Do not run separate CLI/web writers together. Invalid existing JSON intentionally stops startup rather than silently overwriting data. Back up the JSON regularly. Summaries are returned on request and are not saved.

## Deploy from GitHub to Render

Create a repository containing only these application files: Case_Management.py, static/, requirements.txt, render.yaml, README.md, .gitignore, .env.example, demo-cases.json. Do not include your learning exercises, .idea, environment, or private case data. cases.json is ignored; production starts empty. To migrate existing cases, privately back them up and copy them to the mounted disk before starting the app.

In Render, create a Blueprint from that repository using render.yaml. This provisions a paid Starter web service and 1 GB persistent disk (review current cost before provisioning). Enter OPENAI_API_KEY as a secret environment variable. OPENAI_MODEL defaults to the existing gpt-5.5; change it if your OpenAI project does not have access. Build: `pip install -r requirements.txt`. Start: `uvicorn Case_Management:app --host 0.0.0.0 --port $PORT --workers 1`. Health check: /health. JSON path: /var/data/cases.json. A free service's ephemeral filesystem cannot preserve cases across restarts/deploys.

After deployment, create a demo case, refresh, open it, generate a summary, and restart the service to verify persistence. This V1 has no authentication: everyone with the URL can read/create cases and request paid AI suggestions and summaries. Use synthetic demo data and set an OpenAI project spending limit before sharing the URL.

## API

- GET /cases
- GET /cases/{case_id}
- POST /cases (customer_name, issue_description, customer_tier, business_impact, time_sensitivity)
- POST /cases/{case_id}/summary
- POST /triage (issue_description, customer_tier, optional clarifications; returns suggestions without saving)
- PATCH /cases/{case_id}/triage (reviewed ratings plus expected original values for conflict detection)
- PATCH /cases/{case_id}/clarifications (save answers without changing ratings; optimistic conflict detection)
- GET /health

Tier: Low/Medium/High. Impact: Low/Medium/High/Critical. Sensitivity: Low/Medium/High/Urgent/Critical. Policy v2 assigns P1 to every Critical-impact shutdown. Other score thresholds are retained.



## Answering clarification questions

Each AI follow-up question has an optional answer textarea. Leave unknown answers blank. **Reassess with answers** sends the original issue plus reported answers for a fresh assessment; questions themselves are never treated as facts or accepted as supporting evidence. Edited answers disable applying the old assessment until reassessment or an explicit context save.

For intake, reassess answered questions, review both ratings, confirm, and choose **Save reviewed case**. This creates the case and saves assessed answers directly. Unsaved answer edits require reassessment before saving the AI review.

For existing cases, **Save answers to case** persists the context without changing the original issue, impact, urgency, or priority. Alternatively, **Save reviewed assessment** saves the reviewed ratings together with assessed answers. Reopening the case shows the saved Q&A, and subsequent AI triage and summary requests include it. Suggestions and next actions remain transient.

Bounds: at most 20 Q&A entries, 500 characters per question, 1,500 per answer. Customer answers are reported facts, not independently verified data. Conflicting facts should trigger a clarification question.

Eight additional API tests cover legacy loading, Q&A round trips, answer-only save, reviewed save, stale-context conflicts, bounds validation, failed-save rollback, evidence from answers (but not questions), and summaries using saved context. Together with the original ten tests, all **18 tests** pass.

## Workbench update (October 28)

The active queue now supports Open, In progress, and Resolved. Resolve removes a case from the active view; use the Resolved filter to reopen it. Move to Trash asks for confirmation and is recoverable through the Trash filter (restores as Resolved).

AI-supported ratings show Ready for review. Review both ratings, check the confirmation, and choose Save reviewed case to save intake and answers in one action. Required clarification questions stop when both ratings are supported; optional investigation questions do not block saving. Changed answers must be reassessed before saving an AI review. Manual assessment remains available.

See [priority policy v2](PRIORITY_POLICY.md) for the shutdown override, examples, legacy-record behavior and shared-demo limits. demo_controls.py is a required runtime file. No dependency changes are needed. Keep the existing single-worker Render start command and persistent disk.

Validation: `python -m unittest discover -s tests -v` exercises 28 tests, including the complete 60-combination priority matrix, lifecycle, optimistic conflicts, disk failures, AI grounding and demo limits. These deterministic tests do not establish model accuracy. The earlier live evaluation report remains historical and is not a validation of the revised prompt.

Live synthetic workbench evaluation: **4/6** passed. Shutdown/today, recovery versus response deadline, conflicting impact and vague costs passed. Two cosmetic scenarios abstained on “next month” urgency rather than returning expected Low. The report preserves these failures; model accuracy is not established. See evals/workbench-results.json.

## Optional private Gmail pilot

The public demo remains unchanged unless email intake is explicitly enabled. See [GMAIL_SETUP.md](GMAIL_SETUP.md) for the separate private service, test Gmail account, Google authorization and labeled-message polling. Original email text is stored as private drafts; the manager creates a reviewed case. Replies group by Gmail thread and repeated deliveries cannot create duplicate cases. No automatic AI calls, outgoing replies, scheduled digests or phone alerts are enabled in this release.

Forty API tests pass, including private-access boundaries, email parsing, duplicate delivery, stale source checks, source linkage/persistence and existing triage/lifecycle checks. Connector logic is also checked offline with mocked Gmail/HTTP services. A real Google authorization and timed delivery test remain pending; no real inbox has been connected by this implementation. No new Python dependency is required.

## Case ownership and activity timeline — October 30

The case detail view now includes an owner, assigned actions (responsible person, waiting-on party and due date), completion outcomes and a chronological activity history. Record first human acknowledgment, information requests, follow-ups, information received, client updates and resolution notes independently. This supports future responsiveness KPIs without equating vendor recovery time with PM performance.

API additions: PATCH /cases/{id}/owner, POST /cases/{id}/actions, POST /cases/{id}/actions/{action_id}/complete, POST /cases/{id}/activities. Requests require expected_revision and a reported actor name. Existing source links and metadata survive changes. Legacy cases acquire an empty workflow with no invented historical events. The existing single-process atomic JSON persistence remains in use.

Validation: 47 API tests pass locally; seven new workflow tests cover ownership, actions, timestamps, stale revisions, legacy history and failure rollback. No new AI accuracy claim is made. KPIs and live Gmail authorization remain pending. The updated frontend needs deployment and browser acceptance before sharing the new feature as live.

See [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) for dated milestones, measured test execution time, limitations, acceptance steps and the planned KPI definitions. Reported names and manual activity times are not verified identities or proof of external communication. Do not use public-demo data to evaluate employees.

## ASAP and checkpoints

Immediate actions no longer require a made-up deadline. Choose ASAP for prompt work, Follow-up checkpoint for deliberate pursuit, or an explicit promised client update/vendor response/other commitment. Dated types require a date; ASAP does not. Existing saved dates are preserved.

Use Show active cases needing attention for recorded-workflow gaps and overdue checkpoints/commitments. Acknowledgment elapsed time is measured from known case creation; unknown legacy history is shown as unknown. It is not a company SLA or evidence of inaction. An assigned action is a plan, not proof it was performed. Complete it with an outcome and separately record any client communication.

Actor name is remembered in memory on the current page only. This convenience is not authentication. Responsibility defaults to case owner or reported actor. API ActionCreate accepts optional due_at and kind = immediate (default), follow_up, client_update, vendor_response, or commitment. Non-immediate types require due_at. 53 distinct API tests pass and a local browser ASAP-save/reload check passed. See DEVELOPMENT_LOG.md for measured execution time and remaining limitations.
