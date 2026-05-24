from __future__ import annotations

import functools
import hmac
import logging
import os
import threading
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from agent import run_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)

_MAX_GOAL_LENGTH = 2000
_MIN_ITERATIONS = 1
_MAX_ITERATIONS = 20

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

_REQUIRED_ENV_VARS = ("ANTHROPIC_API_KEY", "TAVILY_API_KEY")


def _check_required_env_vars() -> None:
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise SystemExit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in your keys."
        )


_check_required_env_vars()


def _run_job(job_id: str, goal: str, max_iterations: int, request_id: str) -> None:
    try:
        result = run_agent(goal=goal, max_iterations=max_iterations, request_id=request_id)
        with _jobs_lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result
    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(exc)


def _require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        expected = os.environ.get("API_SECRET_KEY", "")
        if not expected:
            return jsonify({"error": "unauthorized"}), 401
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, expected):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.post("/run")
@_require_auth
def run() -> tuple[object, int]:
    request_id = str(uuid.uuid4())
    payload = request.get_json(silent=True) or {}
    goal = str(payload.get("goal", "")).strip()
    max_iterations = payload.get("max_iterations", 10)
    sync = payload.get("sync", False)

    if not goal:
        return jsonify({"error": "goal is required"}), 400

    if len(goal) > _MAX_GOAL_LENGTH:
        return jsonify({"error": f"goal exceeds maximum length of {_MAX_GOAL_LENGTH} characters"}), 400

    if not isinstance(max_iterations, int) or not (_MIN_ITERATIONS <= max_iterations <= _MAX_ITERATIONS):
        return jsonify({"error": f"max_iterations must be an integer between {_MIN_ITERATIONS} and {_MAX_ITERATIONS}"}), 400

    if not isinstance(sync, bool):
        return jsonify({"error": "sync must be a boolean"}), 400

    if sync:
        result = run_agent(goal=goal, max_iterations=max_iterations, request_id=request_id)
        return jsonify(result), 200

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "running",
            "goal": goal,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "result": None,
            "error": None,
        }

    thread = threading.Thread(target=_run_job, args=(job_id, goal, max_iterations, request_id), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id, "request_id": request_id}), 202


@app.get("/jobs/<job_id>")
def get_job(job_id: str) -> tuple[object, int]:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job), 200