# Get Production Ready

## Current State

- Flask + Gunicorn serving `POST /run` and `GET /health`
- ReAct loop with logging
- `web_search` is a **stub** — returns a fake string
- Agent runs **synchronously** inside the HTTP request
- No auth, no rate limiting, no input sanitization

---

## What Needs To Change

### 1. Wire up a real search provider
`web_search` calls nothing. Connect Tavily (simplest) or Brave Search. Needs `TAVILY_API_KEY` in `.env`.

### 2. Async job execution
Agent runs take 30–120 seconds. A synchronous endpoint will time out in production. Change to:
- `POST /run` → creates a job, returns `{ job_id }` immediately
- `GET /jobs/{job_id}` → returns status (`running` / `done` / `failed`) and result when ready
- Use a background thread pool (no new infrastructure needed for a single instance)

### 3. Input validation & security
- Enforce max goal length (prevent prompt injection via oversized input)
- Reject or sanitize `output_dir` to prevent path traversal
- Validate `max_iterations` is bounded (e.g. 1–20)

### 4. API key authentication
- Add a `Bearer` token check on `POST /run` via a middleware/decorator
- Token read from `API_SECRET_KEY` env var

### 5. Startup environment check
- Fail fast at startup if `ANTHROPIC_API_KEY` or `TAVILY_API_KEY` are missing, rather than crashing mid-request

### 6. Request correlation IDs
- Generate and attach a `request_id` to every log line and response for traceability

### 7. Token & cost tracking
- Capture `usage` from each Anthropic response and include it in the job result

### 8. Structured error responses
- All errors return `{ "error": "...", "request_id": "..." }` consistently

### 9. Gunicorn config file
- Add `gunicorn.conf.py` with worker count, timeout, access log format, and graceful shutdown settings

### 10. Improved health check
- `GET /health` verifies the Anthropic key is present and Tavily is configured

### 11. Stagnation detection
- Track `(tool_name, input_hash)` pairs across iterations
- If the same tool is called with identical inputs more than once, abort the run with `stopped: stagnation` and log the repeated call
- Addresses: *agent keeps looping without making progress*

### 12. Output validation
- After `write_file` is called, verify the written file is non-empty and contains the expected sections (executive summary, key findings, sources)
- Fail the job explicitly if the file is missing or malformed rather than returning a silent success
- Addresses: *agent produces an answer that looks plausible but is wrong*

### 13. Business intent guardrails
- Define an explicit allowlist of permitted tools per request type; reject any tool call not on the list before it executes
- Add a post-run content check that scans the output for rule violations (e.g. no PII, no external URLs in internal reports) and flags or blocks before the result is returned
- Addresses: *agent stays within permissions but violates business intent*

---

## Files That Will Change

| File | Change |
|---|---|
| `agent.py` | Real `web_search`, token usage tracking, request_id threading, stagnation detection, output validation |
| `app.py` | Async job queue, auth middleware, input validation, structured errors, correlation IDs, business intent guardrails |
| `requirements.txt` | Add `tavily-python` |
| `gunicorn.conf.py` | New — worker/timeout config |
| `.env.example` | Add `TAVILY_API_KEY`, `API_SECRET_KEY` |
| `test_agent.py` | Cover new validation, job endpoints, stagnation, output validation, guardrails |
