"""
Shared test setup.

- Tests never call the real API (no key, no cost), whatever is set in your shell.
- The original tests were written against the fixed 152-message queue, so each
  test starts in "benchmark" mode. Tests that exercise generated shifts ask for
  one explicitly with server._activate("shift", seed).
"""

import os
import sys

os.environ["TRIAGE_NO_DOTENV"] = "1"  # never read the real .env (and its key) during tests
for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
    os.environ.pop(var, None)
os.environ["SHIFT_SEED"] = "1"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "data"), ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _benchmark_mode_and_isolated_cache(tmp_path, monkeypatch):
    import server

    monkeypatch.setattr(server, "LLM_CACHE_PATH", str(tmp_path / "llm_cache.json"))
    server._activate("benchmark")
    yield
    server._reset_actions()
