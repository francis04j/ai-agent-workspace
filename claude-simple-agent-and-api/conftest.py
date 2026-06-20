"""
Pytest configuration for the api test suite.

Sets placeholder environment variables before any test module is imported so
that the startup env check in app.py does not raise SystemExit during
collection. Real API calls are mocked in tests — these values are never used
for network requests.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-pytest")
os.environ.setdefault("TAVILY_API_KEY", "test-key-for-pytest")
