---
description: "Use when writing, editing, or reviewing agent.py or app.py. Keep api/README.md in sync with every code change that affects endpoints, authentication, configuration, or request/response shapes."
applyTo: ["api/agent.py", "api/app.py"]
---

# README Update Requirements

Any code change to `agent.py` or `app.py` that affects observable behaviour **must** be reflected in `api/README.md` before the task is complete.

## When to update the README

| Change made | README section to update |
|---|---|
| New endpoint added | **Endpoints** table + **Example requests** |
| Endpoint removed or renamed | **Endpoints** table + all curl examples that reference it |
| New required env var | **Run locally → Create your `.env` file** block + **Authentication** (if auth-related) |
| Auth scheme changed | **Authentication** section + every `POST /run` curl example |
| New request field (`goal`, `sync`, `max_iterations`, …) | Relevant curl examples + response shapes |
| Response shape changed | Matching JSON sample in **Example requests** |
| New Python dependency | **Prerequisites** + `requirements.txt` note |
| Agent model or behaviour change | **Example requests** response samples if output format changes |

## Rules

1. **Do not remove existing curl examples** — update them in place.
2. **All `POST /run` curl examples must include `-H "Authorization: Bearer $API_SECRET_KEY"`.**
3. **Env var blocks must stay in sync** — if `.env.example` changes, update the README's `.env` snippet to match.
4. **Keep response JSON samples plausible** — update field names and shapes if the actual response structure changes.
5. **Health and job-polling endpoints are unauthenticated** — do not add auth headers to `GET /health` or `GET /jobs/{job_id}` examples.

## README structure reference

```
# Python Gunicorn API
## Files
## Prerequisites
## Run locally
  1. Create and activate a virtual environment
  2. Install dependencies
  3. Create your .env file        ← env vars live here
  4. Start the server
## Authentication                  ← token scheme, 401 behaviour
## Endpoints                       ← method/path/description table
## Example requests                ← curl + JSON samples per endpoint
## Run the tests
```

Do not restructure these sections; insert content within the appropriate existing section.
