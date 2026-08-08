# MORI Backend Handoff

This repository contains MORI's Telegram gateway. The partner backend supplies research, reasoning, browser automation, conversation state, and approval validation.

## What is safe to share

- All source code
- `requirements.txt`
- `.env.example`
- `docs/backend-contract.md`
- `docs/mori-persona.md`
- Tests and the MORI profile asset

## Never share or commit

- `.env`
- Telegram bot tokens
- Backend API keys
- Cookies, session data, OTPs, or browser profiles
- Runtime logs or PID files
- `.venv`

The existing `.gitignore` excludes all of these local runtime files.

## Partner setup

```powershell
git clone <repository-url>
cd mori-telegram
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The partner can implement and test the backend without possessing the Telegram token. They should expose an endpoint such as:

```text
POST http://127.0.0.1:8000/v1/mori/respond
```

The complete request and response schema is in [docs/backend-contract.md](docs/backend-contract.md).

## Connect the services

On the machine running the Telegram gateway, set:

```text
MORI_BACKEND_URL=http://127.0.0.1:8000/v1/mori/respond
MORI_BACKEND_API_KEY=<shared-secret-if-used>
```

Restart the gateway. Incoming Telegram events will then be forwarded to the partner endpoint instead of the local mock.

## Important polling rule

Run only one production instance of the Telegram polling gateway for `@MoriPathBot`. A partner who needs independent end-to-end testing should use a separate development bot token or coordinate stopping the live gateway first.

## Backend responsibilities

- Maintain conversation state keyed by `session_id`.
- Browse current sources and return sourced results.
- Keep form drafts and pending approvals server-side.
- Validate action ownership, exact payload, and expiry on every approval callback.
- Never trust Telegram button text as authorization.
- Return plain text plus optional callback or HTTPS URL actions.
- Avoid automatic retries for sensitive actions.

## Recommended deployment secret handling

- Local development: ignored `.env` files.
- GitHub Actions: GitHub repository or environment secrets.
- Hosting platforms: their encrypted environment-variable or secret manager UI.
- Never place real secret values in `.env.example`, README files, commits, issues, or screenshots.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe -m compileall -q mori_gateway tests
```

