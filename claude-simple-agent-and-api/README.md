# Python Gunicorn API

This folder contains a minimal Python API that wraps the `GoogleMini` agent described in the article.

## Files

- `agent.py` — agent tools, ReAct loop, and `run_agent` function
- `app.py` — Flask routes (`GET /health`, `POST /run`) served by Gunicorn
- `requirements.txt` — dependencies (`anthropic`, `flask`, `gunicorn`)
- `test_agent.py` — unit and integration tests

## Prerequisites

- Python 3.11+
- An Anthropic API key
- A Tavily API key (for live web search)

## Run locally

**1. Create and activate a virtual environment**

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Create your `.env` file**

```bash
cp .env.example .env
```

Then open `.env` and set your keys:

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
API_SECRET_KEY=your-secret-here
```

Generate a strong `API_SECRET_KEY` — any random string works:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

The `.env` file is listed in `.gitignore` and will not be committed.

**4. Start the server**

```bash
gunicorn --bind 127.0.0.1:8000 app:app
```

The server is ready when you see `Listening at: http://127.0.0.1:8000`.

## Authentication

`POST /run` requires a Bearer token. Set `API_SECRET_KEY` in your `.env` (see setup above), then pass it in every request:

```
Authorization: Bearer <your-secret>
```

`GET /health` and `GET /jobs/{job_id}` are unauthenticated.

Missing or incorrect tokens return:

```json
{"error": "unauthorized"}
```

(HTTP 401)

## Endpoints

| Method | Path             | Description                                      |
|--------|------------------|--------------------------------------------------|
| GET    | `/health`        | Returns `{"status": "ok"}`                       |
| POST   | `/run`           | Submit a goal — async by default, sync optional  |
| GET    | `/jobs/{job_id}` | Poll an async job for status and result          |

## Example requests

**Health check**

```bash
curl http://127.0.0.1:8000/health
```

**Run the agent — sync mode (waits for result)**

Use `"sync": true` when you want the response immediately. Best for short goals.

```bash
curl -s -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-here" \
  -d '{"goal":"In one sentence, what is the ReAct agent pattern?", "sync": true}'
```

Response (200):

```json
{
  "goal": "In one sentence, what is the ReAct agent pattern?",
  "model": "claude-sonnet-4-6",
  "iterations": 1,
  "output_dir": "/path/to/api/output",
  "result": "The ReAct pattern interleaves reasoning and acting..."
}
```

**Run the agent — async mode (default)**

Use the default (or `"sync": false`) for longer research tasks. The server returns immediately with a `job_id`.

```bash
curl -s -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_SECRET_KEY" \
  -d '{"goal":"Search for the top 3 AI agent frameworks released in 2026 and write a report."}'
```

Response (202):

```json
{"job_id": "897650c6-406e-411c-bfcc-180cf92c5a61"}
```

**Poll for the result**

```bash
curl -s http://127.0.0.1:8000/jobs/897650c6-406e-411c-bfcc-180cf92c5a61
```

Response when done:

```json
{
  "status": "done",
  "goal": "Search for the top 3 AI agent frameworks...",
  "created_at": "2026-05-24T10:00:00+00:00",
  "result": { "iterations": 4, "output_dir": "...", "result": "Report written." },
  "error": null
}
```

**Optional: control iteration limit**

```bash
curl -s -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_SECRET_KEY" \
  -d '{"goal":"Summarize recent AI news", "sync": true, "max_iterations": 5}'
```

## Run the tests

Unit tests run without an API key. The live integration test requires `ANTHROPIC_API_KEY` to be set in `api/.env`.

```bash
# Unit tests only
python -m pytest test_agent.py -v

# Include the live LLM test (reads key from .env)
python -m pytest test_agent.py -v
```

Example curl 
(1) curl -s -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"goal":"In one sentence, what is the ReAct agent pattern?"}'

(2) curl -s -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"goal":"Search for the top 3 latest AI agent frameworks released in 2026 and write a 1 paragraph report to a file."}'


No tool calls:
```
[INFO] agent: agent started | model=claude-sonnet-4-6 | goal='In one sentence...'
[INFO] agent: agent finished | no tool calls | iterations=1 | model=claude-sonnet-4-6
```

Tool calls
```
[INFO] agent: agent started | model=claude-sonnet-4-6 | goal='Search for...'
[INFO] agent: tool call | iteration=1 | tool=web_search | inputs={'query': 'AI agent frameworks 2026'}
[INFO] agent: tool result | iteration=1 | tool=web_search | result='[Search results for ...'
[INFO] agent: tool call | iteration=2 | tool=write_file | inputs={'filename': 'report.md', ...}
[INFO] agent: tool result | iteration=2 | tool=write_file | result='Wrote /path/to/report.md'
[INFO] agent: agent finished | no tool calls | iterations=3 | model=claude-sonnet-4-6
````