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
#   2026-05-19 10:30:11 | INFO     | backend.agent:decide | request received
#
# Files:
#   logs/2026-07-02.log — one file per day, created automatically
#   stdout             — configurable level (INFO in production, DEBUG in dev)

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Any

# ── Path constants ─────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(                    # Chat-System/
    os.path.dirname(                                # backend/
        os.path.dirname(os.path.abspath(__file__))  # backend/utils/
    )
)
LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
APP_LOG_PATH = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error.log")

# ── Format ─────────────────────────────────────────────────────────────────────
_FMT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ── Guard against double-setup (uvicorn --reload calls startup twice) ─────────
_configured = False


class DailyFileHandler(logging.FileHandler):
    """Write logs to a new file each day using the YYYY-MM-DD.log naming scheme."""

    def __init__(self, log_dir: str, level: int = logging.INFO, encoding: str = "utf-8") -> None:
        self.log_dir = log_dir
        self.current_path = ""
        os.makedirs(log_dir, exist_ok=True)
        self._set_log_path()
        super().__init__(self.current_path, mode="a", encoding=encoding)
        self.setLevel(level)

    def _set_log_path(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        self.current_path = os.path.join(self.log_dir, f"{today}.log")

    def _rotate_if_needed(self) -> None:
        new_path = os.path.join(self.log_dir, datetime.now().strftime("%Y-%m-%d") + ".log")
        if new_path == self.current_path:
            return
        if self.stream:
            self.flush()
            self.close()
        self._set_log_path()
        self.baseFilename = os.path.abspath(self.current_path)
        self.stream = self._open()

    def emit(self, record: logging.LogRecord) -> None:
        self._rotate_if_needed()
        super().emit(record)


def log_exception(
    logger_instance: logging.Logger,
    message: str,
    exc: BaseException,
    **context: Any,
) -> None:
    """Log an exception with traceback and any available request/session context."""
    context_parts = [f"{key}={value}" for key, value in context.items() if value not in (None, "", [], {})]
    suffix = f" | {' | '.join(context_parts)}" if context_parts else ""
    logger_instance.exception("%s%s", message, suffix)


def setup_logging(console_level: int | None = None) -> None:
    """Configure the root logger with daily file + console handlers."""
    global _configured
    if _configured:
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    if console_level is None:
        console_level = logging.INFO

    formatter = logging.Formatter(fmt=_FMT, datefmt=_DATEFMT)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    app_handler = DailyFileHandler(LOG_DIR, level=logging.INFO)
    app_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    root.addHandler(app_handler)
    root.addHandler(console_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("arelle").setLevel(logging.WARNING)

    _configured = True

    logging.getLogger(__name__).info(
        "Logging initialized — log_dir=%s console_level=%s",
        LOG_DIR,
        logging.getLevelName(console_level),
    )
