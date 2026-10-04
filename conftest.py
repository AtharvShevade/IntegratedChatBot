"""Root pytest conftest.

Loads the project's .env before any test module imports backend code, so
pytest runs see the same OLLAMA_BASE_URL/OLLAMA_EXTRACT_MODEL/etc config as
the real app (backend/main.py calls load_dotenv() at import time — pytest
has no equivalent, so without this every LLM-touching test silently fell
back to load_dotenv()'s built-in defaults: 127.0.0.1:11434 / phi3:mini,
neither of which is what this deployment actually runs against).

H-14: on a machine with no .env at all (a clean checkout, CI, a contributor
who hasn't configured a local deployment), backend/config.py's
BACKEND_PORT/BASE_REPO_PATH raise RuntimeError at import time -- which
previously meant `pytest` failed outright with 45 collection errors before a
single test could even run. The os.environ.setdefault() calls below give
both a harmless fallback value ONLY when nothing (neither a real .env nor the
shell environment) has already set them, so every real deployment's actual
.env always wins unchanged. BASE_REPO_PATH falls back to a small, fully
synthetic fixture directory checked into this repo (no real tenant/user
data) -- tests that need the real production data tree still correctly skip
themselves against it exactly as they already do today when real data is
absent; this only prevents the import-time crash that used to take down the
entire suite before any skip logic could even run.
"""
import os

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("BACKEND_PORT", "8001")
os.environ.setdefault(
    "BASE_REPO_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "tests", "fixtures", "sample_repo"),
)
