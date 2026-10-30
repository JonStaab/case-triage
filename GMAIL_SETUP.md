# Gmail intake pilot setup

Status: implementation tested with synthetic emails. A real Gmail account has NOT been connected or authorized. No messages have been fetched or sent from your accounts. Alerts, digests, attachments and automatic AI classification are not included in this first intake release.

## Start here

Create a separate Gmail test account and enable two-step verification. Do not send its password to anyone or place it in code. Use fictional issues only during the pilot. In Gmail create a label named `CaseTriage`. Only messages carrying this label, received in the last 30 days, are selected by the connector. You can apply it manually at first; later add an appropriate Gmail filter. Replies may need labeling too. The label is a connector filter, not a Google permission boundary: the authorized gmail.readonly scope can read the mailbox.

## Deployment boundary

Keep https://case-triage.onrender.com as the public portfolio demo. Upload this update with email intake DISABLED there (the default). Then create a SEPARATE private service from the same repository using the optional `render-email-pilot.yaml` blueprint path. Do not apply this blueprint to the existing public service. A separate service/disk can incur additional hosting costs; review the displayed cost before creating it. No extra service has been created for you.

The private blueprint uses exactly one worker and one persistent disk. Set PRIVATE_MODE=true, EMAIL_INTAKE_ENABLED=true and DEMO_MODE=false. CASES_FILE=/var/data/cases.json and EMAIL_DRAFTS_FILE=/var/data/email-drafts.json. Use PRIVATE_USERNAME=manager and a unique PRIVATE_PASSWORD of at least 16 characters. Generate a DIFFERENT random EMAIL_WEBHOOK_SECRET (at least 32 characters), kept in Render environment settings and Google Script Properties only. GMAIL_INTAKE_MAILBOX is the exact test Gmail address. OPENAI_API_KEY stays a server environment variable. Do not reuse your Gmail password for the pilot password.

Browser HTTP Basic authentication protects the entire private service, including static assets, cases, drafts, API docs and AI endpoints; /health reveals only health. Use HTTPS. The connector uses its own Bearer secret on its one POST endpoint and cannot access the manager UI. There are no per-user accounts, roles or audit records. This is a single-manager pilot, not a multi-company production service.

The app fails closed if intake is enabled on a public demo or required settings are absent. PRIVATE_MODE remains on when the connector is disabled. An existing draft store also keeps the access gate on to avoid accidentally exposing previously imported data. Do not change the pilot into a public demo; use a separate empty service instead.

## Google Apps Script connector

1. Sign into the TEST Gmail account, then open https://script.google.com and create a new project named Case Triage intake.
2. Paste `gmail-connector/Code.gs` into its code editor.
3. In Project Settings enable the appsscript.json manifest, then replace it with `gmail-connector/appsscript.json`. It declares Advanced Gmail v1 and gmail.readonly plus script.external_request. If Gmail is not visible under Services, add Gmail API v1. A standard Cloud project may also require enabling Gmail API in Cloud Console.
4. In Project Settings -> Script Properties add INTAKE_URL = https://YOUR-PRIVATE-SERVICE.onrender.com/integrations/gmail and EMAIL_WEBHOOK_SECRET = the separate secret saved in Render. Never use the public demo URL. Only trusted project editors should access these properties.
5. Run syncCaseTriage manually and complete Google's authorization under the test account. Permissions allow reading Gmail and sending selected message content to your private Render service. No Gmail password goes to Render. Do not bypass a browser security warning; stop if authorization is blocked and inspect the project/scopes first.
6. Send one fictional problem from your ordinary address to the test inbox and apply CaseTriage. Run syncCaseTriage again. Open your private app, sign in as manager and select Refresh email drafts. Confirm sender, subject and original text.
7. Select Review draft, set customer tier yourself, then request AI triage or use manual assessment. Saving records the email draft ID/revision with the case. Retry cannot create another case for that thread. A new message arriving before save triggers a stale-review conflict. New messages after creation appear on the draft and are NOT silently applied to the saved assessment.
8. Once the manual test works, use Apps Script's Triggers (clock icon), Add trigger -> syncCaseTriage -> Time-driven -> Minutes timer -> Every 5 minutes. This is polling, not instant delivery or a guaranteed alert SLA. Google asks permission to create the trigger. Your computer need not stay on. No trigger has been installed by this update.

## Limits and failures

Each run handles up to 20 labeled messages and paginates across runs. Successful acknowledgments are remembered locally; server message-ID deduplication survives retries/restarts. The connector never marks mail read, edits labels, sends replies or deletes messages. Transport/authorization errors retain retry eligibility. Connector logs contain counts, not email bodies or credentials. Check Apps Script execution failures: there are no PM notification digests yet.

Messages larger than 250 KB decoded or bodies above 8000 characters are rejected; attachments are ignored. HTML is converted to plain text and rendered using textContent, not executed. A draft can hold 20 messages; the private store holds 200 threads. A combined thread above 10000 characters requires manual review rather than truncation. Original email text may include quoted history; deduplication is by Gmail message ID, not sentence meaning. Spam and misleading email remain untrusted reports.

AI is only called after a manager clicks Suggest triage or Generate summary. Those actions send the displayed issue/answers to the configured OpenAI API; imported drafts alone do not invoke AI. Sender address is a starting customer-name suggestion, not verified company identity or tier.

Disable the time trigger to stop polling; set EMAIL_INTAKE_ENABLED=false to stop acceptance while retaining PRIVATE_MODE=true. Revoke the script's Google access if retiring it, and rotate the webhook secret if exposed. Back up both JSON files and keep the private disk access restricted. A wider company rollout needs provider OAuth verification, company approval, stronger identity/access controls and an appropriate data-retention policy.

Official references: https://developers.google.com/apps-script/advanced/gmail ; https://developers.google.com/apps-script/guides/services/authorization ; https://developers.google.com/workspace/gmail/api/auth/scopes
