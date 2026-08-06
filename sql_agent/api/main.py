import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import src.config as config
from api.routes import health, query

# Attach a handler directly so logs always appear in the uvicorn terminal
# regardless of whether uvicorn already configured the root logger.
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(levelname)s  [%(name)s]  %(message)s"))
for _name in ("query", "startup"):
    _lg = logging.getLogger(_name)
    _lg.setLevel(logging.INFO)
    if not _lg.handlers:
        _lg.addHandler(_handler)
    _lg.propagate = False

# Loud, unmissable startup banner: which embedding folder is actually active.
# This exact mismatch (server silently running against the wrong
# EMBEDDING_DIR after a restart) caused multiple rounds of "why doesn't my
# fix show up" debugging — this print makes it visible in every server log
# instead of requiring a fresh diagnostic session each time.
_startup_log = logging.getLogger("startup")
_qa_index_path = f"{config.EMBEDDING_DIR}/qa_index.faiss"
_qa_index_exists = os.path.exists(_qa_index_path)
_startup_log.info("=" * 70)
_startup_log.info("EMBEDDING_DIR = %s", config.EMBEDDING_DIR)
_startup_log.info("qa_index.faiss present: %s (%s)", _qa_index_exists, _qa_index_path)
if not _qa_index_exists:
    _startup_log.warning(
        "No qa_index.faiss here — the direct-match / strong-grounding tiers "
        "are DISABLED for this run. Every query will go through full "
        "retrieval + LLM generation, even exact repeats of known questions."
    )
_startup_log.info("=" * 70)


app = FastAPI(
    title="SQL Query Generator API",
    description="Natural language → SQL pipeline with Oracle DB execution",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")

if __name__ == "__main__":
    import socket

    import uvicorn

    # Windows lets two processes bind the same TCP port, so a port already served
    # by something else does NOT fail here — uvicorn reports "running on :8000"
    # and another service quietly answers the requests (seen in practice: an
    # unrelated /v1/products API returning 404 for /api/query). Probe first and
    # say so, instead of leaving a confusing 404 to debug.
    # Default 8010. Both of the obvious ports are occupied by OTHER projects on
    # this machine, and each collision presented identically: the squatter has no
    # /api/query route, answers 404, and Vite forwards that 404 to the browser —
    # so it reads as "the frontend can't find the route" rather than "the backend
    # isn't running".
    #   8000 — Docker Desktop publishes ANCHOR-MT there
    #   8001 — Desktop\Chat-SystemWorking\dev_server.py, a FastAPI app titled
    #          "Report Assistant" serving /chat
    # MUST stay in sync with the proxy target in frontend/vite.config.js.
    # Override with API_PORT (and update the proxy) if 8010 is ever taken too.
    port = int(os.environ.get("API_PORT", "8010"))

    probe = socket.socket()
    probe.settimeout(1)
    already_serving = probe.connect_ex(("127.0.0.1", port)) == 0
    probe.close()

    if already_serving:
        print(f"\n  [WARNING] Something is already listening on port {port}.")
        print(f"  On Windows this server can still bind it, but requests may be")
        print(f"  answered by the OTHER process — which typically shows up as a")
        print(f"  404 from /api/query rather than a connection error.")
        print(f"  Check who owns it:")
        print(f"      curl http://localhost:{port}/openapi.json     # whose API is this?")
        print(f"  Then start on a free port AND update the proxy target in")
        print(f"  frontend/vite.config.js to match:")
        print(f"      $env:API_PORT = \"{port + 1}\"; python -m api.main\n")

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["api", "src"],   # only watch api/ and src/ — not embedding_building/
    )
