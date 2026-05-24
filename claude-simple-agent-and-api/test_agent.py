"""Tests for GoogleMini agent.

Unit tests run without an API key.
The integration test (test_run_agent_calls_llm) requires ANTHROPIC_API_KEY and
makes a real network call — it is skipped automatically when the key is absent.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent import TOOLS, execute_tool, run_agent, web_search, _write_file_to_disk, _select_model
import agent


# ---------------------------------------------------------------------------
# Unit tests — no LLM calls
# ---------------------------------------------------------------------------


class TestWebSearch:
    def test_returns_string(self):
        result = web_search("python agent frameworks 2026")
        assert isinstance(result, str)

    def test_contains_query(self):
        result = web_search("LangGraph vs CrewAI")
        assert "LangGraph vs CrewAI" in result


class TestWriteFileToDisk:
    def test_writes_content(self, tmp_path):
        content = "# Test Report\nHello world"
        _write_file_to_disk("report.md", content, tmp_path)
        written = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert written == content

    def test_returns_path_string(self, tmp_path):
        result = _write_file_to_disk("out.md", "content", tmp_path)
        assert "out.md" in result


class TestExecuteTool:
    def test_web_search_dispatch(self, tmp_path):
        result = execute_tool("web_search", {"query": "test query"}, tmp_path)
        assert "test query" in result

    def test_write_file_dispatch(self, tmp_path):
        result = execute_tool(
            "write_file",
            {"filename": "test.md", "content": "hello"},
            tmp_path,
        )
        assert (tmp_path / "test.md").exists()
        assert "test.md" in result

    def test_unknown_tool(self, tmp_path):
        result = execute_tool("unknown_tool", {}, tmp_path)
        assert "Unknown tool" in result


class TestToolSchemas:
    def test_tools_list_has_two_entries(self):
        assert len(TOOLS) == 2

    def test_web_search_schema(self):
        tool = next(t for t in TOOLS if t["name"] == "web_search")
        assert "query" in tool["input_schema"]["properties"]
        assert "query" in tool["input_schema"]["required"]

    def test_write_file_schema(self):
        tool = next(t for t in TOOLS if t["name"] == "write_file")
        assert "filename" in tool["input_schema"]["properties"]
        assert "content" in tool["input_schema"]["properties"]


class TestRunAgentMocked:
    """run_agent with a mocked Anthropic client so no API key is needed."""

    @pytest.fixture(autouse=True)
    def reset_model_cache(self):
        """Clear the module-level model cache before each test for isolation."""
        agent._resolved_model = None
        yield
        agent._resolved_model = None

    def _configure_models_list(self, mock_client, model_id: str = "claude-3-5-sonnet-20241022"):
        """Set up mock_client.models.list() to return a single model."""
        fake_model = MagicMock()
        fake_model.id = model_id
        mock_client.models.list.return_value = [fake_model]

    def _make_tool_use_response(self, tool_name: str, tool_input: dict, tool_use_id: str = "tu_1"):
        block = MagicMock()
        block.type = "tool_use"
        block.name = tool_name
        block.input = tool_input
        block.id = tool_use_id
        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [block]
        return response

    def _make_end_turn_response(self, text: str = "Done."):
        block = MagicMock()
        block.text = text
        response = MagicMock()
        response.stop_reason = "end_turn"
        response.content = [block]
        return response

    def test_run_agent_completes_on_end_turn(self, tmp_path):
        with patch("agent.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            self._configure_models_list(mock_client)
            mock_client.messages.create.return_value = self._make_end_turn_response("All done.")

            result = run_agent("test goal", output_dir=str(tmp_path))

        assert result["goal"] == "test goal"
        assert result["model"] == "claude-3-5-sonnet-20241022"
        assert result["result"] == "All done."
        assert result["iterations"] == 1

    def test_run_agent_calls_tool_then_ends(self, tmp_path):
        with patch("agent.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            self._configure_models_list(mock_client)
            mock_client.messages.create.side_effect = [
                self._make_tool_use_response(
                    "web_search", {"query": "top LLM agents"}, "tu_1"
                ),
                self._make_tool_use_response(
                    "write_file",
                    {"filename": "report.md", "content": "# Report\nFindings here"},
                    "tu_2",
                ),
                self._make_end_turn_response("Report written."),
            ]

            result = run_agent("research LLM agents", output_dir=str(tmp_path))

        assert result["iterations"] == 3
        assert (tmp_path / "report.md").exists()
        assert "Report" in (tmp_path / "report.md").read_text()

    def test_run_agent_hits_max_iterations(self, tmp_path):
        with patch("agent.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            self._configure_models_list(mock_client)
            mock_client.messages.create.return_value = self._make_tool_use_response(
                "web_search", {"query": "loop"}, "tu_x"
            )

            result = run_agent("loop forever", output_dir=str(tmp_path), max_iterations=3)

        assert result["result"] == "Max iterations reached."
        assert result["iterations"] == 3

    def test_output_dir_is_created(self, tmp_path):
        new_dir = tmp_path / "agent_output"
        with patch("agent.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            self._configure_models_list(mock_client)
            mock_client.messages.create.return_value = self._make_end_turn_response()

            run_agent("any goal", output_dir=str(new_dir))

        assert new_dir.is_dir()


# ---------------------------------------------------------------------------
# Integration test — requires ANTHROPIC_API_KEY (skipped if absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live LLM test",
)
class TestRunAgentLive:
    def test_run_agent_calls_real_llm(self, tmp_path):
        """Verifies the full ReAct loop runs against the real Anthropic API."""
        result = run_agent(
            goal="What are the two most popular Python web frameworks? One sentence answer.",
            output_dir=str(tmp_path),
            max_iterations=5,
        )

        assert isinstance(result, dict)
        assert result["goal"] != ""
        assert result["iterations"] >= 1
        assert isinstance(result["result"], str)
        assert len(result["result"]) > 0
