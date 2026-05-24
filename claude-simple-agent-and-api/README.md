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

Then open `.env` and set your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

The `.env` file is listed in `.gitignore` and will not be committed.

**4. Start the server**

```bash
gunicorn --bind 127.0.0.1:8000 app:app
```

The server is ready when you see `Listening at: http://127.0.0.1:8000`.

## Endpoints

| Method | Path      | Description                        |
|--------|-----------|------------------------------------|
| GET    | `/health` | Returns `{"status": "ok"}`         |
| POST   | `/run`    | Runs the agent against a goal      |

## Example requests

**Health check**

```bash
curl http://127.0.0.1:8000/health
```

**Run the agent**

```bash
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"goal":"Compare the top three LLM coding agents"}'
```

Optional: pass `output_dir` to control where the agent writes files:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"goal":"Summarize recent AI news", "output_dir":"/tmp/agent-output"}'
```

**Example response**

```json
{
  "goal": "Compare the top three LLM coding agents",
  "iterations": 4,
  "output_dir": "/path/to/api/output",
  "result": "Report written to report.md"
}
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