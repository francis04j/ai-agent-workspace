from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent / ".env")

_FALLBACK_MODEL = "claude-3-5-sonnet-20241022"
_resolved_model: str | None = None


def _select_model(client: anthropic.Anthropic) -> str:
    """Query the API for available models and return the most recent Sonnet-class one."""
    global _resolved_model
    if _resolved_model is not None:
        return _resolved_model
    try:
        available = [m.id for m in client.models.list()]
        sonnet_models = [m for m in available if "sonnet" in m.lower()]
        candidates = sonnet_models if sonnet_models else available
        _resolved_model = sorted(candidates)[-1]  # latest by lexicographic date suffix
    except Exception:
        _resolved_model = _FALLBACK_MODEL
    return _resolved_model


TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the public web for current information on a topic. "
            "Use when you need facts, news, or data that may have changed recently. "
            "Do NOT use for documents already present in the task context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Specific search query, 3-8 words.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "write_file",
        "description": "Write final output to a local file. Use when the task is complete and the report is ready.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["filename", "content"],
        },
    },
]

SYSTEM_PROMPT = """\
You are GoogleMini, a research agent. When given a goal:
1. Use web_search to find current, accurate information.
2. Search multiple times to cover different aspects of the topic.
3. When you have enough information, use write_file to save a structured report.
4. The report should include: an executive summary, key findings, and sources.
Think through each step before acting. When the file is written, you are done."""


def web_search(query: str) -> str:
    # Stub: replace with Tavily or Brave Search API for real searches.
    return f"[Search results for '{query}': connect a real search provider here]"


def _write_file_to_disk(filename: str, content: str, output_dir: Path) -> str:
    output_path = output_dir / Path(filename).name
    output_path.write_text(content, encoding="utf-8")
    return f"Wrote {output_path}"


def execute_tool(name: str, inputs: dict[str, Any], output_dir: Path) -> str:
    if name == "web_search":
        return web_search(inputs["query"])
    if name == "write_file":
        return _write_file_to_disk(inputs["filename"], inputs["content"], output_dir)
    return f"Unknown tool: {name}"


def run_agent(
    goal: str,
    output_dir: str | None = None,
    max_iterations: int = 10,
) -> dict[str, Any]:
    output_root = Path(output_dir or Path(__file__).resolve().parent / "output")
    output_root.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic()
    model = _select_model(client)
    messages: list[dict[str, Any]] = [{"role": "user", "content": goal}]
    logger.info("agent started | model=%s | goal=%r", model, goal)

    for iteration in range(1, max_iterations + 1):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")),
                "Task complete.",
            )
            logger.info(
                "agent finished | no tool calls | iterations=%d | model=%s",
                iteration,
                model,
            )
            return {
                "goal": goal,
                "model": model,
                "iterations": iteration,
                "output_dir": str(output_root),
                "result": final_text,
            }

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(
                        "tool call | iteration=%d | tool=%s | inputs=%r",
                        iteration,
                        block.name,
                        block.input,
                    )
                    result = execute_tool(block.name, block.input, output_root)
                    logger.info(
                        "tool result | iteration=%d | tool=%s | result=%r",
                        iteration,
                        block.name,
                        result[:120] if isinstance(result, str) else result,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})

    logger.warning(
        "agent stopped | max iterations reached | iterations=%d | model=%s",
        max_iterations,
        model,
    )
    return {
        "goal": goal,
        "model": model,
        "iterations": max_iterations,
        "output_dir": str(output_root),
        "result": "Max iterations reached.",
    }