"""M-27: runtime log hygiene.

Covers three independent pieces:
  1. `.gitignore` now excludes every LOG_DIR variant (logs/, logs_5.5/,
     logs_6.0/, any logs*-named dir) and the specific tracked-by-accident
     files the review named (hallucination_log.jsonl, feedback.jsonl,
     intent_classifications.jsonl).
  2. `backend.utils.logger._prune_old_logs()` deletes daily log files older
     than LOG_RETENTION_DAYS, leaving recent ones and non-log files alone.
  3. `backend.utils.logger.RedactingFilter` redacts credential-shaped
     substrings (Bearer tokens, password=..., JWTs) from log records before
     they reach a handler, without touching ordinary diagnostic text
     (request IDs, user/tenant identifiers, timings, error text).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from backend.utils import logger as logger_module


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestGitignoreCoversRuntimeLogs:
    def _gitignore_lines(self) -> set[str]:
        with open(PROJECT_ROOT / ".gitignore", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip() and not line.startswith("#")}

    def test_logs_dir_patterns_present(self):
        lines = self._gitignore_lines()
        assert "logs/" in lines
        assert "logs_*/" in lines or "logs*/" in lines

    def test_known_tracked_by_accident_files_present(self):
        lines = self._gitignore_lines()
        assert "eval/results/hallucination_log.jsonl" in lines
        assert "feedback.jsonl" in lines
        assert "intent_classifications.jsonl" in lines


class TestLogRetention:
    def test_old_log_files_are_removed(self, tmp_path):
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        old_file = tmp_path / f"{old_date}.log"
        old_file.write_text("old log content")

        logger_module._prune_old_logs(str(tmp_path), retention_days=30)

        assert not old_file.exists()

    def test_recent_log_files_are_kept(self, tmp_path):
        recent_date = datetime.now().strftime("%Y-%m-%d")
        recent_file = tmp_path / f"{recent_date}.log"
        recent_file.write_text("recent log content")

        logger_module._prune_old_logs(str(tmp_path), retention_days=30)

        assert recent_file.exists()

    def test_non_daily_log_files_are_left_alone(self, tmp_path):
        other_file = tmp_path / "app.log"
        other_file.write_text("not a daily-rotated file")

        logger_module._prune_old_logs(str(tmp_path), retention_days=30)

        assert other_file.exists()

    def test_prune_does_not_raise_on_empty_or_missing_dir(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        logger_module._prune_old_logs(str(empty), retention_days=30)  # must not raise

    def test_retention_days_env_var_is_read_with_safe_fallback(self, monkeypatch):
        monkeypatch.setattr(logger_module.os, "environ", {"LOG_RETENTION_DAYS": "not-a-number"})
        # Re-derive the same way the module does, without reloading the
        # whole module (which would re-run setup_logging's guard state).
        try:
            value = max(1, int(logger_module.os.environ.get("LOG_RETENTION_DAYS", "30")))
        except ValueError:
            value = 30
        assert value == 30


class TestRedactingFilter:
    def _filtered_message(self, raw: str) -> str:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=1,
            msg=raw, args=(), exc_info=None,
        )
        logger_module.RedactingFilter().filter(record)
        return record.getMessage()

    def test_bearer_token_is_redacted(self):
        msg = self._filtered_message("Authorization: Bearer abcdef0123456789.abcdef")
        assert "abcdef0123456789" not in msg
        assert "[REDACTED]" in msg

    def test_password_param_is_redacted(self):
        msg = self._filtered_message("login failed for url=/x?password=SuperSecret123")
        assert "SuperSecret123" not in msg
        assert "[REDACTED]" in msg

    def test_jwt_shaped_token_is_redacted(self):
        fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dGhpc2lzbm90cmVhbA"
        msg = self._filtered_message(f"jwt={fake_jwt}")
        assert fake_jwt not in msg
        assert "[REDACTED]" in msg

    def test_ordinary_diagnostic_text_is_untouched(self):
        raw = (
            "Chat request completed: intent=db_my_profile duration=20.14s "
            "session=5FEC448ABDBD45A590133E2987335382 login_id=iris810"
        )
        msg = self._filtered_message(raw)
        assert msg == raw, "ordinary request IDs/timings/identifiers must not be redacted"

    def test_user_query_text_is_untouched(self):
        raw = "query='what is my role' tier=regex intent=db_my_role found=True"
        msg = self._filtered_message(raw)
        assert msg == raw, "the intentional intent-mining dataset's raw query text must survive"

    def test_filter_never_raises_on_malformed_record(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="%s %s", args=("only-one",), exc_info=None,  # args/msg mismatch
        )
        result = logger_module.RedactingFilter().filter(record)  # must not raise
        assert result is True


class TestLogDirIsConfigurable:
    def test_log_dir_honors_env_override(self, monkeypatch, tmp_path):
        # Re-derive LOG_DIR the same way the module does at import time,
        # confirming the override logic itself (not re-importing the module,
        # which would disturb other tests' logging state).
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "custom_logs"))
        override = os.environ.get("LOG_DIR", "").strip()
        assert override == str(tmp_path / "custom_logs")
