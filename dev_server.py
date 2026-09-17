"""
dev_server.py — Stable FastAPI development server for Windows
"""

from __future__ import annotations

import os
import sys
import uvicorn
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Add project root to Python path
# -------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from port_guard import assert_port_matches_web_config  # noqa: E402  (needs ROOT_DIR on sys.path)

# -------------------------------------------------------------------
# .env / port — read here, BEFORE uvicorn.run(), since the port has to be
# chosen before the app is even imported (that happens inside uvicorn's own
# reload subprocess). Same ENV_FILE convention as backend/main.py, so this
# script and the app it launches always agree on which .env is authoritative.
# -------------------------------------------------------------------

_env_file = os.environ.get("ENV_FILE", "").strip()
if _env_file:
    load_dotenv(_env_file, override=True)
else:
    load_dotenv()

BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8001"))

# Refuse to start if the IIS rewrite rule forwards somewhere else --
# see port_guard.py for why this cannot be caught any later.
assert_port_matches_web_config(BACKEND_PORT, ROOT_DIR)

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":

    print("\n[DEV SERVER] Starting FastAPI backend...")
    print(f"[DEV SERVER] Port: {BACKEND_PORT}")
    print("[DEV SERVER] Reload watching enabled")
    print("[DEV SERVER] Watching only: backend/")
    print("[DEV SERVER] Excluding logs, frontend, pycache, temp files\n")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=BACKEND_PORT,

        # Auto reload
        reload=True,

        # ONLY watch backend folder
        reload_dirs=[
            os.path.join(ROOT_DIR, "backend")
        ],

        # IMPORTANT:
        # Keep this SMALL on Windows
        reload_excludes=[
            "logs",
            "frontend",
            "__pycache__",
            ".git",
            ".venv",
            "temp",
            "tmp",
        ],

        reload_delay=1.0,

        log_level="info",
    )
