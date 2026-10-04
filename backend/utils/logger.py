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

import glob
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any

from backend.utils.request_context import RequestIdFilter

# ── Path constants ─────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(                    # Chat-System/
    os.path.dirname(                                # backend/
        os.path.dirname(os.path.abspath(__file__))  # backend/utils/
    )
)
# Overridable so two simultaneous backend processes (e.g. 5.5 on one port,
# 6.0 on another, same codebase checkout, each with its own .env via
# ENV_FILE -- see backend/main.py) don't interleave writes into the same log
# files. Default is unchanged, so any deployment that never sets LOG_DIR
# behaves exactly as before. A relative override is resolved against the
# project root (not the process's working directory), same convention as
# sql_agent's EMBEDDING_DIR override.
_log_dir_override = os.environ.get("LOG_DIR", "").strip()
if _log_dir_override:
    LOG_DIR = (_log_dir_override if os.path.isabs(_log_dir_override)
               else os.path.join(_PROJECT_ROOT, _log_dir_override))
else:
    LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
APP_LOG_PATH = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error.log")

# M-27: DailyFileHandler rotates to a new file every day but never deleted
# an old one, so LOG_DIR grew without bound indefinitely. Overridable (same
# convention as LOG_DIR) for a deployment that needs a longer/shorter
# retention window; 30 days is a reasonable default for operational logs
# that were never meant to be a permanent archive.
try:
    LOG_RETENTION_DAYS = max(1, int(os.environ.get("LOG_RETENTION_DAYS", "30")))
except ValueError:
    LOG_RETENTION_DAYS = 30

# ── Format ─────────────────────────────────────────────────────────────────────
# M-28: %(request_id)s is populated by RequestIdFilter (attached below) for
# every record, in or out of a request (reads "-" outside one) -- no change
# needed at any of this app's ~1000 existing logger.info/warning/... call
# sites. Appended to the existing format rather than inserted mid-string, so
# every log line before this change remains a PREFIX of every line after it.
_FMT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s | request_id=%(request_id)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# M-28: structured (JSON) logging is opt-in via LOG_FORMAT=json -- unset (the
# default) keeps the exact plain-text format/handlers/rotation this
# deployment's runbooks (doc/runbooks/log-maintenance.md) and IIS setup
# already rely on. JSON output is for a deployment that feeds logs to an
# aggregator (e.g. the optional Docker path, H-15) where structured fields
# matter more than human-readability at the terminal.
_LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").strip().lower()


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Carries the same fields the text formatter
    exposes (timestamp, level, logger name, function, request_id, message)
    plus exc_info when present -- never raw secrets: RedactingFilter runs
    BEFORE formatting (attached to the handler, same as for the text
    formatter) since it rewrites record.msg/record.args, not formatted
    output, so redaction applies identically to both formats."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, _DATEFMT),
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)

# M-27: redact secret-shaped substrings that might accidentally end up in a
# log message (a pasted bearer token, an auth header, a password=... query
# param, a JWT). This is deliberately narrow -- it targets credential-shaped
# patterns only, never ordinary free text, so it does not touch the
# intentional raw-query logging in backend/utils/intent_log.py (a documented
# dataset mined to improve intent classification) or any other diagnostic
# field (request IDs, user/tenant identifiers, timings, AI output) this
# application's logging already relies on.
_REDACT_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\bBearer\s+[A-Za-z0-9\-_\.]{10,}", re.IGNORECASE),
    re.compile(r"\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)\s*=\s*[^&\s]+", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b"),  # JWT shape
)


def _redact(text: str) -> str:
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class RedactingFilter(logging.Filter):
    """Redacts credential-shaped substrings from a record's rendered message
    before it reaches any handler. Attached to each HANDLER individually
    (not the root logger) so both console and file output are covered,
    including records that propagate up from child loggers -- a logger's
    own .filter() is only consulted for records it originates itself, not
    for records reaching its handlers via callHandlers() from a child
    logger, so a root-level filter would silently never run for the vast
    majority of this application's log calls."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def _prune_old_logs(log_dir: str, retention_days: int) -> None:
    """Delete daily log files older than *retention_days*. Best-effort: a
    permission error or an unexpected filename is logged and skipped, never
    allowed to block startup."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    pattern = os.path.join(log_dir, "????-??-??.log")
    for path in glob.glob(pattern):
        name = os.path.basename(path)
        date_part = name[: -len(".log")]
        try:
            file_date = datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            continue  # not one of our daily log files -- leave it alone
        if file_date < cutoff:
            try:
                os.remove(path)
            except OSError as exc:
                logging.getLogger(__name__).warning(
                    "[log retention] could not remove old log %s: %s", path, exc,
                )

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

    _prune_old_logs(LOG_DIR, LOG_RETENTION_DAYS)

    formatter: logging.Formatter
    if _LOG_FORMAT == "json":
        formatter = JsonFormatter()
    else:
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

    # Attached to each HANDLER (not the root logger) -- a logger's own
    # .filter() is only consulted for records it originates itself; records
    # from every child logger (backend.main, backend.agent.router, ...)
    # reach these handlers via callHandlers(), which checks each HANDLER's
    # filters, not the root logger's. A root-level filter would have silently
    # never run for the vast majority of this application's log calls.
    redactor = RedactingFilter()
    request_id_filter = RequestIdFilter()
    for handler in (app_handler, console_handler):
        handler.addFilter(request_id_filter)  # must run before redactor sees getMessage()
        handler.addFilter(redactor)

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
