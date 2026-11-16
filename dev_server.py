"""
dev_server.py — Stable FastAPI development server for Windows
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import threading
import time

import uvicorn

# -------------------------------------------------------------------
# Add project root to Python path
# -------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# -------------------------------------------------------------------
# .env / port — read here, BEFORE uvicorn.run(), since the port has to be
# chosen before the app is even imported (that happens inside uvicorn's own
# reload subprocess). Same ENV_FILE convention as backend/main.py, so this
# script and the app it launches always agree on which .env is authoritative.
# -------------------------------------------------------------------

# The loading itself (ENV_FILE, .env and the per-version overlay) lives in
# backend/env_loader.py.
from backend.env_loader import load_env  # noqa: E402
load_env()

from backend.config import BACKEND_PORT

# -------------------------------------------------------------------
# Daily self-restart
# -------------------------------------------------------------------

def _start_daily_restart() -> None:
    """Exit the process once a day so the service manager (WinSW <onfailure action="restart"/>)
    starts it again. DAILY_RESTART_AT is HH:MM local time; default 02:00; set but empty disables it;
    an invalid value prints a warning and disables it (it never stops the server from starting)."""
    raw = os.environ.get("DAILY_RESTART_AT", "02:00").strip()
    if not raw:
        print("[DEV SERVER] Daily restart disabled (DAILY_RESTART_AT is empty)")
        return
    try:
        hh, mm = raw.split(":")
        at = dt.time(int(hh), int(mm))
    except ValueError:
        print(f"[DEV SERVER] Daily restart disabled: DAILY_RESTART_AT={raw!r} is not HH:MM")
        return

    def _next_run(after: dt.datetime) -> dt.datetime:
        target = dt.datetime.combine(after.date(), at)
        return target if target > after else target + dt.timedelta(days=1)

    target = _next_run(dt.datetime.now())

    def _watch() -> None:
        # Short sleeps, clock re-read each time: a long sleep could drift if the machine clock is adjusted.
        while True:
            remaining = (target - dt.datetime.now()).total_seconds()
            if remaining <= 0:
                print(f"[DEV SERVER] Daily restart at {raw}: exiting so the service manager restarts the backend", flush=True)
                os._exit(1)
            time.sleep(min(30.0, remaining))

    threading.Thread(target=_watch, name="daily-restart", daemon=True).start()
    print(f"[DEV SERVER] Daily restart scheduled for {target:%Y-%m-%d %H:%M}")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":

    print("\n[DEV SERVER] Starting FastAPI backend...")
    print(f"[DEV SERVER] Port: {BACKEND_PORT}")
    print("[DEV SERVER] Reload disabled (single process); restart the service to pick up code changes\n")

    # H-07 hardening: default to loopback-only so this process is reachable
    # only through the local IIS reverse proxy (confirmed same-machine
    # deployment), not directly from the network. BACKEND_HOST stays
    # env-overridable for a dev setup that genuinely needs LAN access.
    _host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    print(f"[DEV SERVER] Host: {_host}")

    _start_daily_restart()

    uvicorn.run(
        "backend.main:app",
        host=_host,
        port=BACKEND_PORT,

        # One process only: reload spawned a watcher plus workers that left
        # orphans holding the port when run as a Windows service.
        reload=False,

        log_level="info",
    )
