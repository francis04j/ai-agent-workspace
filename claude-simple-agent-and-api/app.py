from __future__ import annotations

import logging

from flask import Flask, jsonify, request

from agent import run_agent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.post("/run")
def run() -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    goal = str(payload.get("goal", "")).strip()
    output_dir = payload.get("output_dir")

    if not goal:
        return jsonify({"error": "goal is required"}), 400

    result = run_agent(goal=goal, output_dir=output_dir)
    return jsonify(result), 200