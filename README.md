# Case Triage

A support triage prototype for small B2B support and customer success teams. Agents record customer issues, assess business impact and urgency using concrete definitions, and review a queue sorted by calculated priority. Optional AI summaries condense the issue without deciding its priority.

Built with FastAPI, plain HTML/CSS/JavaScript, JSON persistence, and the OpenAI Responses API. This is a portfolio prototype, not a production support platform.

## Triage decisions

The customer supplies the facts; a support agent selects impact and urgency. Customer tier follows company policy. This prototype preserves its original example revenue bands: Low under $5m, Medium $5m–$10m, High over $10m annual revenue.

Priority adds the tier score (1–3), impact score (1–4), and time sensitivity score (1–5): totals 3–4 are P4, 5–7 P3, 8–10 P2, and 11–12 P1. Critical impact with Critical sensitivity always yields P1. AI only summarizes; the original issue remains visible.

## Fictional demo

`demo-cases.json` contains three fictional examples: a P1 checkout outage, a P2 dispatch workflow issue, and a P4 cosmetic report issue. Existing private case data is not included.

To try the demo without changing your cases.json, run from this project's folder in PowerShell:

    $env:CASES_FILE = Join-Path (Get-Location) "demo-cases.json"
    python -m uvicorn Case_Management:app --host 127.0.0.1 --port 8767 --workers 1

Open http://127.0.0.1:8767. New cases in that session are saved to demo-cases.json. Stop the server and remove the override (`Remove-Item Env:CASES_FILE`) before running against your normal cases again.

## Validation

Verified create/list/detail flows in a browser, JSON persistence after a server restart, all 60 priority combinations, invalid-input handling, missing-case responses, summary response/error handling, failed-save rollback, and concurrent creates. Live summary generation was also confirmed locally after setting an API key.

## Known limits

No authentication, priority overrides, audit history, or saved summaries. JSON requires one service instance and one worker. A public deployment lets visitors read/create cases and request summaries using the server's API key. Use fictional data for a public demo.

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

Existing cases.json and Case fields remain compatible. CASES_FILE optionally sets an absolute JSON path; the default is cases.json beside the Python module. New installations start empty. Writes use atomic replacement, and API creates are serialized in one process. Run exactly ONE worker and ONE service instance. Do not run separate CLI/web writers together. Invalid existing JSON intentionally stops startup rather than silently overwriting data. Back up the JSON regularly. Summaries are returned on request and are not saved.

## Deploy from GitHub to Render

Create a repository containing only these application files: Case_Management.py, static/, requirements.txt, render.yaml, README.md, .gitignore, .env.example, demo-cases.json. Do not include your learning exercises, .idea, environment, or private case data. cases.json is ignored; production starts empty. To migrate existing cases, privately back them up and copy them to the mounted disk before starting the app.

In Render, create a Blueprint from that repository using render.yaml. This provisions a paid Starter web service and 1 GB persistent disk (review current cost before provisioning). Enter OPENAI_API_KEY as a secret environment variable. OPENAI_MODEL defaults to the existing gpt-5.5; change it if your OpenAI project does not have access. Build: `pip install -r requirements.txt`. Start: `uvicorn Case_Management:app --host 0.0.0.0 --port $PORT --workers 1`. Health check: /health. JSON path: /var/data/cases.json. A free service's ephemeral filesystem cannot preserve cases across restarts/deploys.

After deployment, create a demo case, refresh, open it, generate a summary, and restart the service to verify persistence. This V1 has no authentication: everyone with the URL can read/create cases and request paid summaries. Use synthetic demo data and set an OpenAI project spending limit before sharing the URL.

## API

- GET /cases
- GET /cases/{case_id}
- POST /cases (customer_name, issue_description, customer_tier, business_impact, time_sensitivity)
- POST /cases/{case_id}/summary
- GET /health

Tier: Low/Medium/High. Impact: Low/Medium/High/Critical. Sensitivity: Low/Medium/High/Urgent/Critical. Priority rules are preserved, including the Critical impact + Critical sensitivity P1 override.

