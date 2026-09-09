# main.py — FastAPI entry point: /chat, /speech-to-text, /health.
# Start with: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

# Initialise centralised logging before any other backend import so that
# module-level loggers in agent, guided, tools, etc. are already wired up.
from backend.utils.logger import log_exception, setup_logging  # noqa: E402
setup_logging(console_level=logging.INFO)

from backend import version_config  # noqa: E402
from backend.agent import decide, explain_category_for_report  # noqa: E402
from backend.guided import guided_step, GUIDED_ACTIONS  # noqa: E402
from backend import i18n  # noqa: E402
from backend.i18n.translator import PlaceholderSafeTranslator  # noqa: E402
from backend import stt  # noqa: E402
from backend.stt import config as stt_config, vocabulary as stt_vocabulary  # noqa: E402
from backend.models import (  # noqa: E402
    ChatRequest, ChatResponse, CompareRequest, CompareSummaryRequest,
    ExplainCategoryRequest, FeedbackRequest,
)
from backend.utils.intent_log import log_feedback  # noqa: E402

logger = logging.getLogger(__name__)

# ── Warmup guard ──────────────────────────────────────────────────────────────
# In development (--reload / dev_server.py), Uvicorn re-imports this module
# in the reloader child process after every code change.  The lifespan context
# manager therefore runs again, which would repeat SentenceTransformer, FAISS,
# and Ollama warm-up — the exact slow operations we want to avoid.
#
# This flag is set to True the first time _warmup_embedding() completes so
# subsequent reloads skip the heavy work.  Because Python module state is
# process-local, the flag resets naturally on a genuine fresh start.
_warmup_done: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm Ollama models, SentenceTransformer, and FAISS indexes on startup."""
    global _warmup_done
    logger.info("Application startup started")
    import asyncio

    try:
        # ── Pre-load SentenceTransformer + FAISS indexes in a thread so the async
        # event loop is not blocked.  This moves the cold-start penalty from the
        # first user query to server startup (invisible to users).
        def _warmup_embedding():
            global _warmup_done
            if _warmup_done:
                logger.info("Warm-up skipped; already completed in this process")
                return
            try:
                import backend.sql_agent.vectorizer as _vec  # noqa: F401  triggers module-level load
                logger.info("SentenceTransformer model loaded")
            except Exception as exc:
                logger.warning("SentenceTransformer warm-up failed: %s", exc)

            try:
                from backend.sql_agent.retriever import search
                from backend.sql_agent.vectorizer import embed_query
                from backend.sql_agent.config import (
                    TABLE_INDEX_PATH, TABLE_META_PATH,
                    COLUMN_INDEX_PATH, COLUMN_META_PATH,
                )
                import os as _os
                # search() takes a pre-computed query embedding, not a query
                # string — embedding once here also warms the encoder itself.
                _warm_vec = embed_query("warmup")
                if _os.path.exists(TABLE_INDEX_PATH):
                    search(TABLE_INDEX_PATH, TABLE_META_PATH, _warm_vec, k=1)
                    logger.info("Table FAISS index loaded")
                if _os.path.exists(COLUMN_INDEX_PATH):
                    search(COLUMN_INDEX_PATH, COLUMN_META_PATH, _warm_vec, k=1)
                    logger.info("Column FAISS index loaded")
            except Exception as exc:
                logger.warning("FAISS warm-up failed: %s", exc)

            try:
                from backend.db_qa.intents.embedding_index import search_intent, INDEX_PATH
                import os as _os
                if _os.path.exists(INDEX_PATH):
                    search_intent("warmup", k=1)
                    logger.info("Intent exemplar FAISS index loaded")
                else:
                    logger.warning(
                        "Intent exemplar index not found at %s — "
                        "run `python -m backend.db_qa.intents.embedding_index` to build it",
                        INDEX_PATH,
                    )
            except Exception as exc:
                logger.warning("Intent exemplar index warm-up failed: %s", exc)

            try:
                from backend.config import app_db_base_path
                if app_db_base_path():
                    from backend.db_qa.xml_store import XMLStore
                    store = XMLStore(app_db_base_path())
                    _ = store.users()
                    _ = store.departments()
                    _ = store.roles()
                    _ = store.periods()
                    logger.info("Application DB XML store loaded")
            except Exception as exc:
                logger.warning("Application DB XML warm-up skipped: %s", exc)

            _warmup_done = True

        await asyncio.get_event_loop().run_in_executor(None, _warmup_embedding)

        from backend.services.llm_service import (
            OLLAMA_BASE_URL, OLLAMA_EXTRACT_MODEL, OLLAMA_MODEL, _KEEP_ALIVE,
        )
        async with httpx.AsyncClient(timeout=120) as client:
            for model in {OLLAMA_EXTRACT_MODEL, OLLAMA_MODEL}:
                try:
                    await client.post(
                        f"{OLLAMA_BASE_URL}/api/chat",
                        json={"model": model, "messages": [], "stream": False, "keep_alive": _KEEP_ALIVE},
                    )
                    logger.info("LLM model ready: %s", model)
                except Exception as exc:
                    logger.warning("LLM warm-up failed for model=%s: %s", model, exc)

        # State the multilingual configuration THIS process actually has.
        # os.environ is fixed at process start, so a backend started before
        # MULTILINGUAL_ENABLED was set returns English to every fr/ar/hi
        # request while looking perfectly healthy. One log line makes that
        # visible instead of leaving it to be guessed at from the UI.
        _i18n_cfg = i18n.runtime_config()
        logger.info(
            "Multilingual: enabled=%s model=%s endpoint=%s languages=%s",
            _i18n_cfg["enabled"], _i18n_cfg["model"],
            _i18n_cfg["base_url"], _i18n_cfg["supported"],
        )
        if not _i18n_cfg["enabled"]:
            logger.warning(
                "Multilingual is DISABLED in this process — /chat and /guided "
                "will return English even when lang=fr|ar|hi is sent. "
                "Set MULTILINGUAL_ENABLED=true in .env and restart."
            )

        # Same reasoning as the multilingual line above: os.environ is fixed at
        # process start, so a backend started before STT_BASE_URL was set would
        # fail every transcription while looking healthy.
        _stt_cfg = stt.runtime_config()
        logger.info(
            "STT: enabled=%s endpoint=%s language_mode=%s concurrency=%d timeout=%.0fs",
            _stt_cfg["enabled"], _stt_cfg["base_url"], _stt_cfg["language_mode"],
            _stt_cfg["concurrency"], _stt_cfg["timeout"],
        )
        if not _stt_cfg["enabled"]:
            logger.warning(
                "STT is DISABLED in this process — the mic button will report "
                "that voice input is unavailable. Set STT_ENABLED=true and restart."
            )

        logger.info("Application startup completed")
        yield
    except Exception as exc:
        log_exception(logger, "Application startup failed", exc)
        raise
    finally:
        logger.info("Application shutdown completed")


app = FastAPI(title="Report Assistant", version="3.0.0", lifespan=lifespan)

# ── In-flight request tracking (for Stop Generation) ──────────────────────────
# Keyed by request_id (minted client-side per request). Lets /stop cancel the
# asyncio.Task backing a /chat, /guided, /compare-execute, or /explain-category
# call. Cancellation is cooperative: it takes effect at the next `await` inside
# the task (e.g. the next Ollama/httpx call), which covers the dominant
# long-pole in every request path.
_inflight_tasks: dict[str, asyncio.Task] = {}

# request_ids that /stop has deliberately cancelled. Needed to tell a
# user-initiated Stop apart from a CancelledError that means something else
# entirely (server shutdown, client disconnect) — the two arrive at the
# endpoint as the identical exception, but only the first should be turned
# into a normal HTTP response. Swallowing the second would break shutdown.
_stopped_request_ids: set[str] = set()

# ── STT admission control ─────────────────────────────────────────────────────
# MEASURED: the Whisper service transcribes one clip at a time. Two concurrent
# 1s clips returned in 13.6s and 27.2s -- the second caller simply waited for
# the first. Bounding admission here means a third caller is told to retry
# instead of queueing invisibly behind two requests that each take ~14s.
# Same reasoning, and the same shape, as the semaphore in i18n/boundary.py.
_stt_slots = asyncio.Semaphore(stt_config.concurrency())


class RequestStopped(Exception):
    """The user pressed Stop and /stop cancelled this request's task.

    Deliberately NOT a subclass of asyncio.CancelledError: the whole point is
    that endpoints can catch this and return a clean response without also
    catching (and thereby suppressing) genuine cancellation.
    """


async def _run_cancellable(request_id: str | None, coro):
    if not request_id:
        return await coro
    task = asyncio.ensure_future(coro)
    _inflight_tasks[request_id] = task
    try:
        return await task
    except asyncio.CancelledError:
        # Only the task WE created was cancelled, by /stop — this coroutine
        # itself is not being cancelled, so converting the exception here
        # suppresses nothing that should propagate. Any other CancelledError
        # (shutdown, disconnect) leaves request_id absent from the set and is
        # re-raised untouched.
        if request_id in _stopped_request_ids:
            raise RequestStopped from None
        raise
    finally:
        _inflight_tasks.pop(request_id, None)
        _stopped_request_ids.discard(request_id)


def _stopped_response(intent: str = "stopped") -> ChatResponse:
    """The response a stopped request returns instead of dropping the
    connection. Plain and terminal — the frontend already rendered whatever
    partial state it had; this just closes the request cleanly."""
    return ChatResponse(
        intent=intent,
        result_type="stopped",
        response_text="Request stopped.",
    )

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_exception(
        logger,
        "Unhandled exception",
        exc,
        method=request.method,
        path=request.url.path,
        request_id=request.headers.get("x-request-id"),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again."},
    )


def _make_repo_scope(tenant_id: str | None, domain: str | None, jwt: str | None):
    """Build the version_config.repo_scope for one request.

    APP_VERSION=5.5 (default): always a no-op — root=None so
    config.get_active_root() keeps returning BASE_REPO_PATH exactly as
    before this existed.

    APP_VERSION=6.0: resolves TenantId (trusting an explicit tenant_id, or
    falling back to a domain -> TenantId lookup in XML_Tenant.xml) and sets
    the active root to D:\\Repo6\\Repo6\\{TenantId} for the request. If no
    tenant can be resolved, the scope is still a no-op — downstream reads
    fail closed (file-not-found -> empty results) rather than silently
    reading data under the bare, non-tenant-scoped repo root.
    """
    if not version_config.IS_V6:
        return version_config.repo_scope(None)

    resolved_tenant_id = version_config.resolve_tenant_id(tenant_id, domain)
    if not resolved_tenant_id:
        logger.warning(
            "[APP_VERSION=6.0] Could not resolve tenant_id (tenant_id=%r, domain=%r) — "
            "request will run with no tenant repo root set.",
            tenant_id, domain,
        )
        return version_config.repo_scope(None, tenant_id=tenant_id, jwt=jwt)

    root = version_config.repo_root_for_tenant(resolved_tenant_id)
    return version_config.repo_scope(root, tenant_id=resolved_tenant_id, jwt=jwt)


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    logger.info(
        "API request received: /chat session=%s",
        request.session_id or "anonymous",
    )
    start = time.monotonic()
    # ── Debug trace: log every /chat request so missing identity is immediately visible ──
    from backend.utils.debug import debug_log
    debug_log(
        "/chat API HIT",
        question=request.message,
        login_id=request.login_id or "NOT PROVIDED",
        user_id=request.user_id   or "NOT PROVIDED",
        role_id_from_net="NOT SENT — resolved inside decide() via auth_service",
        asp_session="provided" if request.asp_session else "NOT PROVIDED",
        session_id=request.session_id or "none",
    )

    # ── APP_VERSION=6.0: resolve tenant repo root for this request only.
    # No-op under 5.5 (root stays None -> BASE_REPO_PATH, unchanged behavior).
    _repo_scope = _make_repo_scope(request.tenant_id, request.domain, request.jwt)
    _repo_scope.__enter__()
    try:
        # ── Multilingual boundary, INBOUND: user language → English ───────────
        # No-op (returns request.message itself, no model call) when
        # MULTILINGUAL_ENABLED=false or lang is absent/"en". decide() below
        # receives an English string either way and is completely unaware of
        # this layer.  Wrapped in _run_cancellable so Stop Generation
        # interrupts a translation exactly as it interrupts any Ollama call.
        _inbound = await _run_cancellable(
            request.request_id, i18n.translate_inbound(request.message, request.lang)
        )
        if not _inbound.ok:
            # FAIL SAFE. A timed-out or truncated translation is
            # indistinguishable from a valid short question once it reaches
            # decide(), which would then route it confidently and wrongly.
            # Refuse the turn instead — the pipeline is never called.
            logger.warning(
                "Chat request refused: inbound translation failed lang=%s session=%s error=%s",
                request.lang, request.session_id or "anonymous", _inbound.error,
            )
            return ChatResponse(**i18n.inbound_failure_response(request.lang, _inbound.error))

        result = await _run_cancellable(request.request_id, decide(
            _inbound.text,
            session_id=request.session_id,
            asp_session=request.asp_session,
            login_id=request.login_id,
            user_id=request.user_id,
            role_id=request.role_id,
            # Already English: the frontend replays data.i18n.english from the
            # previous turn, so the classifier and LLM extractor keep seeing
            # English context without seven extra translation calls.
            conversation_history=request.conversation_history[-7:] if request.conversation_history else None,
        ))
        elapsed = time.monotonic() - start
        intent_for_log = result.intent if isinstance(result, ChatResponse) else result.get("intent", "?")
        logger.info(
            "Chat request completed: intent=%s duration=%.2fs session=%s",
            intent_for_log, elapsed, request.session_id or "anonymous",
        )
        # ── Debug trace: log the response summary ──────────────────────────────
        debug_log(
    "/chat RESPONSE",
    intent=intent_for_log,
    db_found=result.db_found if isinstance(result, ChatResponse) else result.get("db_found", "N/A"),
    result_type=result.result_type if isinstance(result, ChatResponse) else result.get("result_type", "?"),
    job_id=result.job_id if isinstance(result, ChatResponse) else result.get("job_id"),  # ← ADD THIS
    response_preview=(
        result.response_text if isinstance(result, ChatResponse)
        else result.get("response_text", "")
    )[:120],
    elapsed_s=f"{elapsed:.3f}s",
)
        # ── Multilingual boundary, OUTBOUND: English → user language ─────────
        # Returns `result` itself, unchanged and uncopied, when the feature is
        # off or lang is English. Never raises; on translation failure the
        # correct ENGLISH answer is returned rather than a blank one. Option
        # lists are masked out before the call and re-rendered locally from
        # options[], so identifiers cannot be altered by the model.
        if isinstance(result, ChatResponse):
            if not i18n.should_translate(request.lang):
                return result
            result = result.model_dump()
        result = await _run_cancellable(request.request_id, i18n.translate_outbound(
            result, request.lang,
            english_message=_inbound.text,
            inbound=_inbound,
        ))
        return ChatResponse(**result)
    except RequestStopped:
        logger.info("Chat request stopped by user: session=%s", request.session_id or "anonymous")
        return _stopped_response()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        log_exception(
            logger,
            "Chat request failed because the LLM service was unavailable",
            exc,
            endpoint="/chat",
            session_id=request.session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to process your request at the moment. Please try again.",
        ) from exc
    finally:
        _repo_scope.__exit__(None, None, None)


@app.post("/compare-execute", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def compare_execute(request: CompareRequest) -> ChatResponse:
    """Execute a pre-staged instance comparison directly — no intent detection.

    The frontend calls this after the user picks two instances from the dropdown
    UI. It resolves the full file paths from the server-side session state and
    runs the XBRL variance pipeline immediately.
    """
    from backend.agent import execute_comparison
    logger.info(
        "API request received: /compare-execute session=%s",
        request.session_id or "anonymous",
    )
    start = time.monotonic()
    try:
        result = await _run_cancellable(request.request_id, execute_comparison(
            session_id=request.session_id,
            idx_a=request.instance_a,
            idx_b=request.instance_b,
        ))
        elapsed = time.monotonic() - start
        logger.info(
            "Comparison completed: duration=%.2fs session=%s",
            elapsed, request.session_id or "anonymous",
        )
        # The comparison's own prose is deterministic and resolves from the
        # catalogue. variance_data / variance_all / labels are DATA and are not
        # translatable fields, so the table and chart are untouched. llm_summary
        # here is Python's deterministic draft; the model-authored narrative
        # arrives separately via /compare-summary.
        result = await _run_cancellable(request.request_id, i18n.translate_outbound(
            result, request.lang,
        ))
        return ChatResponse(**result)
    except RequestStopped:
        logger.info("Comparison request stopped by user: session=%s", request.session_id or "anonymous")
        return _stopped_response()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        log_exception(
            logger,
            "Comparison request failed because the LLM service was unavailable",
            exc,
            endpoint="/compare-execute",
            session_id=request.session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to process your request at the moment. Please try again.",
        ) from exc


@app.post("/compare-summary", status_code=status.HTTP_200_OK)
async def compare_summary(request: CompareSummaryRequest) -> dict:
    """The AI narrative for a variance table the user is already looking at.

    /compare-execute returns the table and chart immediately with whatever
    summary its 8-second inline budget managed to produce — which on a CPU
    Ollama is none. The frontend then calls this endpoint, which runs the
    same generator with a realistic budget, and drops the bullets into the
    panel when they arrive.

    Returns {"llm_summary": str} — empty string on any failure, exactly as
    the inline path does, so a missing summary is never an error state:
    the table and chart above it are complete either way.
    """
    from backend.tools.variance_explain import generate_explanations

    logger.info(
        "API request received: /compare-summary report=%s rows=%d",
        request.report_name or "?", len(request.rows),
    )
    if not request.rows:
        return {"llm_summary": ""}

    # generate_explanations reads each row's two values by the LABEL keys
    # (r.get(label_a)), while the frontend holds them as val_a/val_b — the
    # shape /compare-execute serialised them into. Map back rather than
    # changing either side's contract.
    label_a = request.label_a or "A"
    label_b = request.label_b or "B"
    rows = [
        {
            "concept":     row.concept,
            label_a:       row.val_a,
            label_b:       row.val_b,
            "diff":        row.diff,
            "pct_change":  row.pct_change,
            "significant": row.significant,
            # Carried through so the async narrative can name the supervisory
            # section, exactly as the inline path already does.
            "section":         row.section,
            "importance_tier": row.importance_tier,
            "mandated_by":     row.mandated_by,
            # Selection + business context. concept_base drives the
            # max-3-per-concept cap, context_key finds the parent row for
            # share-of-total, and unit gates ₹ Cr formatting.
            "concept_base":       row.concept_base or row.concept,
            "context_key":        row.context_key or "BASE",
            "unit":               row.unit,
            "section_code":       row.section_code,
            "importance":         row.importance,
            "priority":           row.priority,
            "importance_matched": row.importance_matched,
        }
        for row in request.rows
    ]

    try:
        timeout = float(os.getenv("OLLAMA_SUMMARY_ASYNC_TIMEOUT", "300"))
    except ValueError:
        timeout = 300.0

    start = time.monotonic()
    try:
        summary = await _run_cancellable(
            request.request_id,
            generate_explanations(
                rows, label_a, label_b, request.report_name,
                timeout=timeout, all_rows=rows,
            ),
        )
    except RequestStopped:
        logger.info("Compare-summary request stopped by user: report=%s", request.report_name or "?")
        return {"llm_summary": ""}
    except Exception as exc:  # noqa: BLE001 — the summary is optional by design
        log_exception(
            logger, "Compare summary failed", exc,
            endpoint="/compare-summary", report_name=request.report_name,
        )
        return {"llm_summary": ""}

    logger.info(
        "[PERF] endpoint=/compare-summary duration=%.2fs chars=%d",
        time.monotonic() - start, len(summary or ""),
    )

    # GENUINELY DYNAMIC. This narrative is written by the model per comparison
    # -- it is not a template and cannot be catalogued, so it is the one place
    # on this endpoint that legitimately spends a runtime translation call.
    # translate_outbound masks the concept names, figures and percentages out
    # of it first, so the numbers a regulator reads are the pipeline's own.
    #
    # This narrative is several sentences long -- longer than a normal chat
    # reply -- and the shared qwen3:14b Ollama proxy was measured reliably
    # exceeding even a 180s budget on it. Benchmarked against aya-expanse:8b
    # on realistic comparison-analysis text (short + long, en->hi/fr/ar):
    # 81-157s, every [[E#]] placeholder preserved. So THIS endpoint only uses
    # its own model (config.compare_summary_translation_model(), NOT
    # TRANSLATION_MODEL/qwen3:14b -- every other translation path is
    # unaffected) and keeps the existing 180s budget, which already covers
    # the worst case measured (157s) with margin -- no need to raise it.
    #
    # PlaceholderSafeTranslator adds one more check on top of the existing
    # restore_entities() safety net: the benchmark also found aya-expanse:8b
    # can (rarely) reuse a placeholder for a second value or invent a bare
    # number in prose next to an intact one, neither of which
    # restore_entities() catches on its own (see translator.py). A rejected
    # translation falls back to English via the SAME existing mechanism any
    # other translation failure already uses -- no new fallback path.
    if summary and i18n.should_translate(request.lang):
        try:
            translation_timeout = float(os.getenv("COMPARE_SUMMARY_TRANSLATION_TIMEOUT", "180"))
        except ValueError:
            translation_timeout = 180.0
        # i18n.boundary.get_translator (attribute access, not a bound import) so
        # tests that monkeypatch "backend.i18n.boundary.get_translator" still
        # intercept this call exactly as they do the default /chat path.
        base_translator = i18n.boundary.get_translator(
            timeout=translation_timeout,
            model=i18n.config.compare_summary_translation_model(),
            base_url=i18n.config.compare_summary_translation_base_url(),
        )
        translator = PlaceholderSafeTranslator(base_translator)
        localized = await _run_cancellable(request.request_id, i18n.translate_outbound(
            {"llm_summary": summary, "options": []}, request.lang, translator,
        ))
        return {"llm_summary": localized.get("llm_summary") or summary}

    return {"llm_summary": summary or ""}


@app.post("/explain-category", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def explain_category(request: ExplainCategoryRequest) -> ChatResponse:
    """On-demand error explanation for a single category (formula_error,
    xbrl_schema, dimensional). Triggered when the user clicks an
    "Explain ... Errors" button in the ErrorSummaryPanel.
    """
    logger.info(
        "API request received: /explain-category category=%s form_id=%s",
        request.category, request.form_id,
    )
    start = time.monotonic()
    try:
        result = await _run_cancellable(request.request_id, explain_category_for_report(
            error_file_path=request.error_file_path,
            category=request.category,
            form_id=request.form_id,
            report_name=request.report_name,
            offset=request.offset,
        ))
        elapsed = time.monotonic() - start
        logger.info(
            "Error explanation completed: category=%s duration=%.2fs",
            request.category, elapsed,
        )
        # Deterministic prose here resolves from the catalogue; the LLM-authored
        # error explanations in error_details[] are NOT translated (Phase 2).
        result = await _run_cancellable(request.request_id, i18n.translate_outbound(
            result, request.lang, english_message=request.category,
        ))
        return ChatResponse(**result)
    except RequestStopped:
        logger.info("Explain-category request stopped by user: category=%s", request.category)
        return _stopped_response()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        log_exception(
            logger,
            "Error explanation request failed because the LLM service was unavailable",
            exc,
            endpoint="/explain-category",
            category=request.category,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to process your request at the moment. Please try again.",
        ) from exc


@app.post("/speech-to-text", status_code=status.HTTP_200_OK)
async def speech_to_text(
    file: UploadFile = File(...),
    lang: str = Form("en"),
    request_id: str | None = Form(None),
) -> dict:
    """Transcribe recorded audio to text in the SPOKEN language.

    This does not translate and does not touch the chat pipeline. The
    transcript is returned to the frontend, which puts it in the input box
    (App.jsx handleTranscript) so the user can correct a misheard report name
    before pressing Send. Keeping it out of /chat is also what keeps STT
    latency outside the chat latency budget.

    Backed by the remote Whisper service (backend/stt), reached exactly the way
    Ollama is: a base URL in configuration, a thin typed client, no model and
    no audio decoding on this host.
    """
    if not stt.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice input is turned off.",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file received.",
        )

    limit = stt_config.max_bytes()
    if len(audio_bytes) > limit:
        # Bounds a runaway recorder before it costs a minute of serialized CPU
        # on the STT host.
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="That recording is too long. Please record a shorter message.",
        )

    # The service validates by FILENAME EXTENSION -- measured: a .txt upload is
    # rejected with the allowed list. api.js already names the blob
    # "recording.webm"; fall back rather than send something unnamed.
    filename = (file.filename or "recording.webm").strip() or "recording.webm"

    # The selected UI language is the STT language hint. Whisper's own
    # detection is unreliable on short or noisy clips (measured
    # language_probability 0.35-0.63 on non-speech), while a user who picked
    # French is overwhelmingly likely to be speaking French. STT_LANGUAGE_MODE
    # =auto hands the decision back to the model.
    requested = (lang or "").strip().lower()
    hint: str | None = None
    if stt_config.language_mode() == "ui" and requested in stt_config.supported_languages():
        hint = requested

    logger.info(
        "API request received: /speech-to-text bytes=%d lang=%r hint=%r file=%r",
        len(audio_bytes), requested, hint, filename,
    )
    start = time.monotonic()

    client = stt.get_client()
    try:
        async with _stt_slots:
            result = await _run_cancellable(request_id, client.transcribe(
                audio_bytes, filename, lang=hint,
                initial_prompt=stt_vocabulary.initial_prompt(),
            ))
    except RequestStopped:
        logger.info("Speech-to-text stopped by user: request_id=%s", request_id)
        return {"transcript": "", "stopped": True}

    elapsed = time.monotonic() - start
    logger.info(
        "[PERF] endpoint=/speech-to-text duration=%.2fs ok=%s chars=%d meta=%s",
        elapsed, result.ok, len(result.text), result.to_dict(),
    )

    if not result.ok:
        # Nothing sensible to degrade to: a failed transcription has no English
        # fallback the way a failed translation does.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to transcribe audio right now. Please try again.",
        )

    return {
        "transcript": result.text,
        "detected_language": result.language,
        "language_probability": result.language_probability,
    }


@app.post("/stop", status_code=status.HTTP_200_OK)
async def stop_request(request: Request) -> dict:
    """Cancel an in-flight /chat, /guided, /compare-execute, or /explain-category
    request identified by request_id (see Stop Generation feature).

    Cancellation is cooperative: the backing asyncio.Task is cancelled, which
    raises CancelledError at its next `await` (typically the next LLM/httpx
    call). If the task has already finished, this is a harmless no-op.
    """
    body = await request.json()
    request_id = body.get("request_id")
    task = _inflight_tasks.get(request_id) if request_id else None
    stopped = False
    if task and not task.done():
        # Record BEFORE cancelling: _run_cancellable reads this set to decide
        # whether the CancelledError it is about to see is a user Stop (return
        # a clean response) or something it must not swallow.
        _stopped_request_ids.add(request_id)
        task.cancel()
        stopped = True
    logger.info("Stop requested: request_id=%s stopped=%s", request_id, stopped)
    return {"stopped": stopped}


@app.post("/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(request: FeedbackRequest) -> dict:
    """Record a thumbs up/down on a completed assistant response.

    Persisted to logs/feedback.jsonl for later analysis — see
    backend.utils.intent_log.log_feedback. Never raises: a logging
    failure here should not surface as a chat-breaking error.
    """
    log_feedback(
        rating=request.rating,
        query=request.query,
        intent=request.intent,
        result_type=request.result_type,
        session_id=request.session_id,
    )
    return {"ok": True}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict:
    return {"status": "ok"}


@app.get("/download-file", status_code=status.HTTP_200_OK)
async def download_file(
    form_id: str, type: str, filename: str,
    tenant_id: str | None = None, domain: str | None = None,
):
    """Serve a render or error file for download.

    Query params:
        form_id   — numeric report ID (non-numeric chars stripped server-side)
        type      — "render" | "error"
        filename  — bare filename, no directory component allowed
        tenant_id / domain — APP_VERSION=6.0 only; resolves the tenant repo root

    Security: form_id is sanitised to digits only; filename is reduced to its
    basename so path-traversal attempts ('../../../etc/passwd') are rejected.
    The resolved absolute path is verified to lie within the designated base
    directory before the file is opened.
    """
    import re as _re
    from pathlib import Path
    from fastapi.responses import FileResponse
    from backend.tools.report_lookup import build_render_file_path, build_error_file_path
    from backend.config import render_base_dir, instance_base_dir

    with _make_repo_scope(tenant_id, domain, None):
        # ── Input validation ──────────────────────────────────────────────────
        safe_fid  = _re.sub(r"[^0-9]", "", form_id)
        safe_name = os.path.basename(filename)  # strips any directory component

        if not safe_fid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request.")
        if not safe_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request.")
        if type not in ("render", "error"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request.")

        # ── Path construction ───────────────────────────────────────────────────
        if type == "render":
            file_path = build_render_file_path(safe_fid, safe_name)
            base_dir  = render_base_dir()
            media     = "text/html"
        else:
            file_path = build_error_file_path(safe_fid, safe_name)
            base_dir  = instance_base_dir()
            media     = "application/xml"

        # ── Containment check — prevent directory traversal ─────────────────────
        resolved  = Path(file_path).resolve()
        base_real = Path(base_dir).resolve()
        try:
            resolved.relative_to(base_real)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        if not resolved.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

        logger.info("[DOWNLOAD] type=%s form_id=%s filename=%s", type, safe_fid, safe_name)
        return FileResponse(
            path=str(resolved),
            media_type=media,
            filename=safe_name,
        )


@app.get("/reports", status_code=status.HTTP_200_OK)
async def list_reports(tenant_id: str | None = None, domain: str | None = None) -> dict:
    """Return all known report names from returns.xml — used for guided-mode autocomplete."""
    from backend.tools.report_lookup import _parse_returns
    with _make_repo_scope(tenant_id, domain, None):
        names = sorted({r.get("Name", "") for r in _parse_returns() if r.get("Name")})
    return {"reports": names}


@app.get("/allowed-actions", status_code=status.HTTP_200_OK)
async def allowed_actions(
    login_id: str | None = None,
    tenant_id: str | None = None, domain: str | None = None,
) -> dict:
    """Return the subset of guided-menu actions this user may see/perform.

    Side-effect-free (unlike POSTing a sentinel message through /guided, which
    shares the live conversation's session_id and can corrupt an in-progress
    guided flow). Used by the frontend to filter the action menu on load and
    whenever identity changes, independent of any conversation session.
    """
    from backend.guided import _allowed_actions
    with _make_repo_scope(tenant_id, domain, None):
        return {"actions": _allowed_actions(login_id)}


@app.get("/status-errors/{job_id}", status_code=status.HTTP_200_OK)
async def get_status_errors(job_id: str, lang: str = "en") -> dict:
    """Poll for the result of a background LLM error-enrichment job.

    Returns:
        {"status": "not_found"}  — unknown job_id
        {"status": "pending"}    — job still running
        {"status": "done", "error_messages": [...], "error_details": [...]}  — complete
    """
    from backend.agent import _error_jobs
    job = _error_jobs.get(job_id)
    if job is None:
        return {"status": "not_found"}
    if job["status"] == "pending":
        return {"status": "pending"}
    # Done — return payload and clean up
    payload = job["payload"]
    logger.warning(
    "[POLL] job_id=%s keys=%s",
    job_id,
    list(payload.keys()) if payload else []
)
    _error_jobs.pop(job_id, None)
    # ── Multilingual boundary: OUTBOUND ────────────────────────────────────
    # This is the report-status path, and it carries the SAME error_details[]
    # cards /explain-category returns -- the enrichment simply finished after
    # the first response was already sent. Without this the cards came back
    # English no matter which language was selected, because the poll is the
    # only place they are delivered.
    localized = await i18n.translate_outbound(dict(payload or {}), lang)
    return {"status": "done", **localized}


@app.post("/guided", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def guided(request: ChatRequest) -> ChatResponse:
    """Guided workflow endpoint — deterministic step-by-step input collection.

    Intent is known from the button pressed; no LLM extraction is used.
    Send message="__GUIDED_START__" to open the action menu.
    """
    logger.info(
        "[REQUEST] mode=guided session=%s message=%r",
        request.session_id, request.message,
    )
    start = time.monotonic()
    _repo_scope = _make_repo_scope(request.tenant_id, request.domain, request.jwt)
    _repo_scope.__enter__()
    try:
        result = await _run_cancellable(request.request_id, guided_step(
            request.message,
            session_id=request.session_id,
            asp_session=request.asp_session,
            login_id=request.login_id,
        ))
        elapsed = time.monotonic() - start
        logger.info(
            "[PERF] endpoint=/guided result_type=%s duration=%.2fs session=%s",
            result.get("result_type", "?"), elapsed, request.session_id,
        )
        # ── Multilingual boundary: OUTBOUND ONLY for /guided ─────────────────
        # There is deliberately NO inbound translation here. Every message this
        # endpoint receives is a token the pipeline matches verbatim, never
        # free prose:
        #   * "__GUIDED_START__"        — the menu sentinel (main.py:726)
        #   * an exact GUIDED_ACTIONS label — matched with `msg in
        #     GUIDED_ACTIONS` at guided.py:179-180, an English literal test
        #   * a report name / ReturnId / Request ID — taken verbatim at
        #     guided.py:198-230 (_looks_like_request_id_attempt, _INSTANCE_ID_RE)
        # Translating any of them would break the flow outright. The user still
        # gets a localized RESPONSE; the button labels stay English, which is
        # also what keeps them matchable on the next turn.
        result = await _run_cancellable(request.request_id, i18n.translate_outbound(
            result, request.lang, english_message=request.message,
        ))
        return ChatResponse(**result)
    except RequestStopped:
        logger.info("Guided request stopped by user: session=%s", request.session_id)
        return _stopped_response()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error(
            "[API_FAILURE] Ollama unreachable for /guided — %s", exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to process your request at the moment. Please try again.",
        ) from exc
    finally:
        _repo_scope.__exit__(None, None, None)