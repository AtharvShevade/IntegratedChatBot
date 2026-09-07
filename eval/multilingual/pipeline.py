"""Thin wrapper around the real ``decide()`` -- the harness observes the
pipeline, it never modifies it.

Deliberately bypasses the HTTP layer. Under APP_VERSION=5.5, ``/chat`` adds
only a no-op repo scope (backend/main.py:229, short-circuits when not IS_V6)
and a pass-through when ``request_id`` is None (backend/main.py:172), so
calling ``decide()`` directly exercises the identical code path with less
machinery. This follows the established pattern in backend/tests
(test_compare_disambiguation.py:20-45): asyncio.run, no server.

Two things this module exists to get right:

  * Import order. backend.services.auth_service freezes AUTHORIZATION_ENABLED
    at import time (auth_service.py:55), so config.apply_eval_env() has to run
    before backend is imported anywhere in the process. bootstrap() enforces
    that and refuses to proceed if backend is already loaded.

  * Session hygiene. ``_session_context`` (backend/agent/__init__.py:259) is a
    process-global dict that is never garbage collected or expired. State
    leaking between cases is the single largest correctness hazard in a
    multi-turn evaluation, so every case clears its own key before and after.

The intent extractor is left LIVE. backend/tests mock it with an AsyncMock to
avoid a network call; we must not, because routing fidelity is precisely what
is being measured.
"""
from __future__ import annotations

import asyncio
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from eval.multilingual import config

_BOOTSTRAPPED = False


def bootstrap() -> dict[str, str]:
    """Prepare the process for driving the pipeline. Idempotent.

    Returns the environment overrides applied, for stamping into results.
    """
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return config.run_config()  # type: ignore[return-value]

    if any(m.startswith("backend.") or m == "backend" for m in sys.modules):
        raise RuntimeError(
            "backend was imported before pipeline.bootstrap(); "
            "AUTHORIZATION_ENABLED is frozen at import time in "
            "backend/services/auth_service.py:55, so the auth bypass would not "
            "take effect and every case would return the canned "
            "'Authentication required.' response."
        )

    root = str(config.PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)

    # Same ordering as backend/main.py:22-23 -- .env first, then logging set up
    # before any backend module binds a logger.
    from dotenv import load_dotenv

    load_dotenv()
    overrides = config.apply_eval_env()

    from backend.utils.logger import setup_logging  # noqa: E402
    import logging  # noqa: E402

    setup_logging(console_level=logging.WARNING)

    _BOOTSTRAPPED = True
    return overrides


def _agent():
    """Import lazily so bootstrap() always precedes the first backend import."""
    if not _BOOTSTRAPPED:
        raise RuntimeError("call pipeline.bootstrap() before running any query")
    import backend.agent as agent

    return agent


def clear_session(session_id: str | None) -> None:
    if not session_id:
        return
    agent = _agent()
    agent._session_context.pop(session_id, None)
    try:
        import backend.guided as guided

        getattr(guided, "_guided_sessions", {}).pop(session_id, None)
    except Exception:  # noqa: BLE001 - guided store is optional
        pass


@dataclass
class TurnResult:
    """One ``decide()`` call, timed by wall clock.

    Latency is measured here rather than read from the logs because
    ``[PERF] operation=decide`` is emitted on exactly one of decide()'s many
    return paths (backend/agent/__init__.py:2307-2311) -- every fast path,
    staged branch, db_qa route and SQL route returns without it.
    """

    query: str
    response: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def field(self, name: str, default=None):
        return self.response.get(name, default)

    def to_dict(self) -> dict:
        # Keep the archived record shape ({**ChatResponse, _question,
        # _duration_ms}) used by coverage_results.jsonl et al. so results stay
        # diffable against the historical baselines.
        record = dict(self.response)
        record["_question"] = self.query
        record["_duration_ms"] = round(self.duration_ms, 1)
        if self.error:
            record["_error"] = self.error
        return record


def run_turn(
    query: str,
    session_id: str | None = None,
    login_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> TurnResult:
    """Run one message through the unmodified pipeline."""
    agent = _agent()
    started = time.perf_counter()
    try:
        response = asyncio.run(
            agent.decide(
                query,
                session_id=session_id,
                asp_session=None,
                login_id=login_id,
                user_id=None,
                role_id=None,
                conversation_history=conversation_history or [],
            )
        )
        elapsed = (time.perf_counter() - started) * 1000.0
        if not isinstance(response, dict):
            response = dict(response)
        return TurnResult(query=query, response=response, duration_ms=elapsed)
    except BaseException as exc:  # noqa: BLE001 - a bad case must not kill the run
        # BaseException, not Exception, on purpose. The SQL-agent path can
        # raise SystemExit-family errors out of native extensions, and a bare
        # `except Exception` lets those through -- which silently terminated a
        # 60-case baseline run at case 42 with exit code 0, looking like a
        # clean finish. Re-raise only genuine user interrupts.
        if isinstance(exc, KeyboardInterrupt):
            raise
        elapsed = (time.perf_counter() - started) * 1000.0
        return TurnResult(
            query=query,
            response={},
            duration_ms=elapsed,
            error=f"{type(exc).__name__}: {exc}",
        )


def new_session_id(prefix: str = "mleval") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# Response fields carrying user-visible prose. These are what a production
# translation layer would send outbound, so these are what the harness
# translates and scores. Everything omitted here is protocol, enum, key or
# ground-truth data -- see the plan's "core constraint" section.
TRANSLATABLE_FIELDS = (
    "response_text",
    "llm_summary",
    "db_summary",
    "db_beautified",
    "status_note",
    "accuracy_hint",
    "more_info_hint",
    "download_label",
)


def translatable_payload(response: dict) -> dict[str, str]:
    """The subset of a response a translation layer would actually touch."""
    return {
        name: value
        for name in TRANSLATABLE_FIELDS
        if isinstance((value := response.get(name)), str) and value.strip()
    }
