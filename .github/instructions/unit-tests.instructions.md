---
description: "Use when writing, editing, or reviewing agent.py or app.py. Always write unit tests for every code change that affects the agent loop or API endpoints. Covers mocking patterns for TavilyClient and Anthropic, Flask test client usage, and test structure requirements."
applyTo: ["api/agent.py", "api/app.py"]
---

# Unit Test Requirements

Every code change to `agent.py` or `app.py` **must** be accompanied by unit tests in `test_agent.py`.

## Rules

1. **New function → at least one new test.** Cover the happy path, one edge case, and one error/failure path.
2. **Changed behaviour → updated test.** If existing behaviour changes, update the corresponding test. Do not leave tests asserting the old behaviour.
3. **No real credentials in unit tests.** Mock `anthropic.Anthropic` and `agent.TavilyClient` so tests run without `ANTHROPIC_API_KEY` or `TAVILY_API_KEY`.
4. **Use `tmp_path` for all file I/O.** Never write to the real `output/` directory in tests.
5. **Flask routes use `app.test_client()`.** Test HTTP endpoints through the test client, not by calling route functions directly.
6. **Isolate shared state.** Clear module-level state (e.g. `_jobs`, `_resolved_model`) in `setup_method` / `teardown_method` so tests do not affect each other.

## Test Class Structure

| Class | What it covers |
|---|---|
| `TestWebSearch` | `web_search()` in `agent.py` — mock `agent.TavilyClient` |
| `TestWriteFileToDisk` | `_write_file_to_disk()` |
| `TestExecuteTool` | `execute_tool()` dispatch — mock `agent.TavilyClient` for web_search cases |
| `TestToolSchemas` | Validates the `TOOLS` list contracts |
| `TestRunAgentMocked` | `run_agent()` with mocked Anthropic client |
| `TestApp` | Flask routes in `app.py` using test client |

## Mocking Patterns

### TavilyClient
```python
from unittest.mock import patch

@patch("agent.TavilyClient")
def test_web_search_returns_results(self, MockTavily):
    MockTavily.return_value.search.return_value = {
        "results": [{"title": "Result", "url": "http://example.com", "content": "Info"}]
    }
    result = web_search("test query")
    assert isinstance(result, str)
    assert "Result" in result
```

### Anthropic client
```python
@patch("agent.anthropic.Anthropic")
def test_run_agent(self, mock_cls, tmp_path):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.models.list.return_value = [MagicMock(id="claude-3-5-sonnet-20241022")]
    mock_client.messages.create.return_value = ...  # build with helpers
```

### Flask test client
```python
import app as app_module
from app import app as flask_app

class TestApp:
    def setup_method(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()
        with app_module._jobs_lock:
            app_module._jobs.clear()

    def test_health(self):
        response = self.client.get("/health")
        assert response.status_code == 200
```
