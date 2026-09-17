from __future__ import annotations

import os
import sys
import uvicorn
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from port_guard import assert_port_matches_web_config  # noqa: E402  (needs ROOT_DIR on sys.path)

# Same ENV_FILE convention as backend/main.py / dev_server.py -- read here,
# before uvicorn.run(), since the port must be chosen before the app itself
# is imported.
_env_file = os.environ.get("ENV_FILE", "").strip()
if _env_file:
    load_dotenv(_env_file, override=True)
else:
    load_dotenv()

BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8001"))

# Refuse to start if the IIS rewrite rule forwards somewhere else --
# see port_guard.py for why this cannot be caught any later.
assert_port_matches_web_config(BACKEND_PORT, ROOT_DIR)

if __name__ == "__main__":
    print("[SERVICE] Starting FastAPI backend...")
    print(f"[SERVICE] Port: {BACKEND_PORT}")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=BACKEND_PORT,
        reload=False,
        log_level="info",
    )