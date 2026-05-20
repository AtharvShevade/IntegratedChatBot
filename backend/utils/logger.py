# logger.py — Centralised logging setup for the Chat-System backend.
#
# Call setup_logging() once at application startup (in main.py).
# Every other module should continue to declare its own logger as:
#
#     logger = logging.getLogger(__name__)
#
# That way log records carry the exact module path as their "name" field,
# giving clean per-module filtering in log viewers.
#
# Output format:
#   2026-05-19 10:30:11 | INFO     | backend.agent | [INTENT] intent=get_status
#
# Files:
#   logs/app.log   — INFO and above, rotating (10 MB × 5 backups)
#   logs/error.log — ERROR and above, rotating (10 MB × 5 backups)
#   stdout         — configurable level (DEBUG in dev, INFO in prod)

from __future__ import annotations

import logging
import logging.handlers
import os
import sys

# ── Path constants ─────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(                    # Chat-System/
    os.path.dirname(                                # backend/
        os.path.dirname(os.path.abspath(__file__))  # backend/utils/
    )
)
LOG_DIR        = os.path.join(_PROJECT_ROOT, "logs")
APP_LOG_PATH   = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error.log")

# ── Format ─────────────────────────────────────────────────────────────────────
_FMT  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ── Rotating file settings ─────────────────────────────────────────────────────
_MAX_BYTES    = 10 * 1024 * 1024   # 10 MB per file before rotation
_BACKUP_COUNT = 5                  # keep 5 rotated copies

# ── Guard against double-setup (uvicorn --reload calls startup twice) ─────────
_configured = False


def setup_logging(console_level: int = logging.DEBUG) -> None:
    """Configure the root logger with rotating file + console handlers.

    Parameters
    ----------
    console_level:
        Minimum level printed to stdout.  Pass ``logging.INFO`` for quieter
        production output.  Defaults to DEBUG so all messages appear during
        development.

    The function is idempotent — subsequent calls are silently ignored so it
    is safe to call it from application factories or test fixtures.
    """
    global _configured
    if _configured:
        return

    # Ensure the logs/ directory exists (it typically already does because it
    # stores XML data files, but create it defensively).
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(fmt=_FMT, datefmt=_DATEFMT)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # root captures everything; handlers filter

    # ── app.log: INFO and above ────────────────────────────────────────────────
    app_handler = logging.handlers.RotatingFileHandler(
        APP_LOG_PATH,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)

    # ── error.log: ERROR and above ─────────────────────────────────────────────
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_PATH,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # ── Console: configurable level ────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    root.addHandler(app_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)

    # ── Suppress chatty third-party loggers ────────────────────────────────────
    # httpx/httpcore log every TCP connection at DEBUG; suppress to WARNING.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # Uvicorn access log is redundant — FastAPI already logs requests.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # Arelle emits very verbose DEBUG output; keep at WARNING.
    logging.getLogger("arelle").setLevel(logging.WARNING)

    _configured = True

    logging.getLogger(__name__).info(
        "[STARTUP] Logging initialised — app=%s  errors=%s  console_level=%s",
        APP_LOG_PATH,
        ERROR_LOG_PATH,
        logging.getLevelName(console_level),
    )
