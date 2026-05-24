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

import app as app_module
from app import app as flask_app

from agent import TOOLS, execute_tool, run_agent, web_search, _write_file_to_disk, _select_model
import agent


# ---------------------------------------------------------------------------
# Unit tests — no LLM calls
# ---------------------------------------------------------------------------


class TestWebSearch:
    @patch("agent.TavilyClient")
    def test_returns_string(self, MockTavily):
        MockTavily.return_value.search.return_value = {
            "results": [{"title": "Test", "url": "http://example.com", "content": "Test content"}]
        }
        result = web_search("python agent frameworks 2026")
        assert isinstance(result, str)

    @patch("agent.TavilyClient")
    def test_formats_results_with_title_and_url(self, MockTavily):
        MockTavily.return_value.search.return_value = {
            "results": [{"title": "LangGraph Guide", "url": "http://example.com/langgraph", "content": "LangGraph info"}]
        }
        result = web_search("LangGraph vs CrewAI")
        assert "LangGraph Guide" in result
        assert "http://example.com/langgraph" in result

    @patch("agent.TavilyClient")
    def test_empty_results_returns_no_results_message(self, MockTavily):
        MockTavily.return_value.search.return_value = {"results": []}
        result = web_search("no results query")
        assert "No results found" in result


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
    @patch("agent.TavilyClient")
    def test_web_search_dispatch(self, MockTavily, tmp_path):
        MockTavily.return_value.search.return_value = {
            "results": [{"title": "Result", "url": "http://example.com", "content": "info"}]
        }
        result = execute_tool("web_search", {"query": "test query"}, tmp_path)
        assert isinstance(result, str)
        MockTavily.return_value.search.assert_called_once_with(query="test query", max_results=5)

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
    def mock_tavily(self):
        """Prevent real Tavily network calls in all mocked agent tests."""
        with patch("agent.TavilyClient") as mock_cls:
            mock_cls.return_value.search.return_value = {
                "results": [{"title": "Mock result", "url": "https://example.com", "content": "mock content"}]
            }
            yield mock_cls

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
        response.usage.input_tokens = 10
        response.usage.output_tokens = 5
        return response

    def _make_end_turn_response(self, text: str = "Done."):
        block = MagicMock()
        block.text = text
        response = MagicMock()
        response.stop_reason = "end_turn"
        response.content = [block]
        response.usage.input_tokens = 10
        response.usage.output_tokens = 5
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
        assert "request_id" in result
        assert result["usage"]["input_tokens"] == 10
        assert result["usage"]["output_tokens"] == 5
        assert result["usage"]["total_tokens"] == 15

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
        assert "request_id" in result
        assert result["usage"]["input_tokens"] == 30  # 3 iterations x 10
        assert result["usage"]["output_tokens"] == 15  # 3 iterations x 5

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
        assert "request_id" in result
        assert "usage" in result

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
# App route tests — no LLM calls
# ---------------------------------------------------------------------------


class TestApp:
    _TEST_SECRET = "test-secret"

    def setup_method(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()
        with app_module._jobs_lock:
            app_module._jobs.clear()
        os.environ["API_SECRET_KEY"] = self._TEST_SECRET

    def teardown_method(self):
        os.environ.pop("API_SECRET_KEY", None)

    def test_health_returns_ok(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json["status"] == "ok"

    def test_run_missing_goal_returns_400(self):
        response = self.client.post("/run", json={}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 400
        assert "goal is required" in response.json["error"]

    def test_run_empty_goal_returns_400(self):
        response = self.client.post("/run", json={"goal": "   "}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 400
        assert "goal is required" in response.json["error"]

    def test_run_goal_too_long_returns_400(self):
        response = self.client.post("/run", json={"goal": "x" * 2001}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 400
        assert "exceeds maximum length" in response.json["error"]

    def test_run_max_iterations_too_high_returns_400(self):
        response = self.client.post("/run", json={"goal": "research topic", "max_iterations": 21}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 400
        assert "max_iterations" in response.json["error"]

    def test_run_max_iterations_too_low_returns_400(self):
        response = self.client.post("/run", json={"goal": "research topic", "max_iterations": 0}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 400
        assert "max_iterations" in response.json["error"]

    def test_run_max_iterations_non_integer_returns_400(self):
        response = self.client.post("/run", json={"goal": "research topic", "max_iterations": "ten"}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 400
        assert "max_iterations" in response.json["error"]

    @patch("app.run_agent")
    def test_run_valid_goal_returns_202_with_job_id(self, mock_run_agent):
        mock_run_agent.return_value = {"result": "done"}
        response = self.client.post("/run", json={"goal": "research topic"}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 202
        assert "job_id" in response.json
        assert "request_id" in response.json

    def test_get_job_not_found_returns_404(self):
        response = self.client.get("/jobs/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json["error"]

    def test_get_job_returns_stored_job_data(self):
        job_id = "test-job-123"
        with app_module._jobs_lock:
            app_module._jobs[job_id] = {
                "status": "done",
                "goal": "test goal",
                "created_at": "2026-05-24T00:00:00+00:00",
                "result": {"result": "test result"},
                "error": None,
            }
        response = self.client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json["status"] == "done"
        assert response.json["goal"] == "test goal"

    @patch("app.run_agent")
    def test_run_job_stores_result_on_success(self, mock_run_agent):
        import time
        mock_run_agent.return_value = {"result": "completed"}
        post_response = self.client.post("/run", json={"goal": "test goal"}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        job_id = post_response.json["job_id"]
        time.sleep(0.2)
        get_response = self.client.get(f"/jobs/{job_id}")
        assert get_response.json["status"] == "done"
        assert get_response.json["result"]["result"] == "completed"

    @patch("app.run_agent", side_effect=RuntimeError("LLM failed"))
    def test_run_job_stores_error_on_failure(self, mock_run_agent):
        import time
        post_response = self.client.post("/run", json={"goal": "failing goal"}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        job_id = post_response.json["job_id"]
        time.sleep(0.2)
        get_response = self.client.get(f"/jobs/{job_id}")
        assert get_response.json["status"] == "failed"
        assert "LLM failed" in get_response.json["error"]

    @patch("app.run_agent")
    def test_run_sync_true_returns_200_with_result(self, mock_run_agent):
        mock_run_agent.return_value = {"goal": "test", "result": "ReAct is a pattern.", "iterations": 1, "request_id": "rid-123", "usage": {}}
        response = self.client.post("/run", json={"goal": "test", "sync": True}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 200
        assert response.json["result"] == "ReAct is a pattern."

    @patch("app.run_agent")
    def test_run_sync_passes_request_id_to_agent(self, mock_run_agent):
        mock_run_agent.return_value = {"goal": "test", "result": "ok", "request_id": "any", "usage": {}}
        self.client.post("/run", json={"goal": "test", "sync": True}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        _, kwargs = mock_run_agent.call_args
        assert "request_id" in kwargs
        assert isinstance(kwargs["request_id"], str)

    @patch("app.run_agent")
    def test_run_sync_false_returns_202_with_job_id(self, mock_run_agent):
        mock_run_agent.return_value = {"result": "done"}
        response = self.client.post("/run", json={"goal": "test", "sync": False}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 202
        assert "job_id" in response.json

    def test_run_sync_non_boolean_returns_400(self):
        response = self.client.post("/run", json={"goal": "test", "sync": "yes"}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 400
        assert "sync" in response.json["error"]

    def test_run_no_auth_header_returns_401(self):
        response = self.client.post("/run", json={"goal": "test"})
        assert response.status_code == 401
        assert "unauthorized" in response.json["error"]

    def test_run_wrong_token_returns_401(self):
        response = self.client.post("/run", json={"goal": "test"}, headers={"Authorization": "Bearer wrong-token"})
        assert response.status_code == 401
        assert "unauthorized" in response.json["error"]

    def test_run_empty_token_returns_401(self):
        response = self.client.post("/run", json={"goal": "test"}, headers={"Authorization": "Bearer "})
        assert response.status_code == 401
        assert "unauthorized" in response.json["error"]

    def test_run_missing_api_secret_key_returns_401(self):
        os.environ.pop("API_SECRET_KEY", None)
        response = self.client.post("/run", json={"goal": "test"}, headers={"Authorization": f"Bearer {self._TEST_SECRET}"})
        assert response.status_code == 401
        assert "unauthorized" in response.json["error"]


# ---------------------------------------------------------------------------
# Startup environment check
# ---------------------------------------------------------------------------


class TestStartupEnvCheck:
    def test_raises_when_anthropic_key_missing(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-tav"}, clear=True):
            with pytest.raises(SystemExit):
                app_module._check_required_env_vars()

    def test_raises_when_tavily_key_missing(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-ant"}, clear=True):
            with pytest.raises(SystemExit):
                app_module._check_required_env_vars()

    def test_passes_when_all_keys_present(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-ant", "TAVILY_API_KEY": "test-tav"}, clear=True):
            app_module._check_required_env_vars()  # should not raise


# ---------------------------------------------------------------------------
# Integration test — requires ANTHROPIC_API_KEY (skipped if absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-"),
    reason="Real ANTHROPIC_API_KEY not set — skipping live LLM test",
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
