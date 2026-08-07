"""Root pytest conftest.

Loads the project's .env before any test module imports backend code, so
pytest runs see the same OLLAMA_BASE_URL/OLLAMA_EXTRACT_MODEL/etc config as
the real app (backend/main.py calls load_dotenv() at import time — pytest
has no equivalent, so without this every LLM-touching test silently fell
back to load_dotenv()'s built-in defaults: 127.0.0.1:11434 / phi3:mini,
neither of which is what this deployment actually runs against).
"""
from dotenv import load_dotenv

load_dotenv()
