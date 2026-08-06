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
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
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
from backend.models import (  # noqa: E402
    ChatRequest, ChatResponse, CompareRequest, ExplainCategoryRequest, FeedbackRequest,
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


async def _run_cancellable(request_id: str | None, coro):
    if not request_id:
        return await coro
    task = asyncio.ensure_future(coro)
    _inflight_tasks[request_id] = task
    try:
        return await task
    finally:
        _inflight_tasks.pop(request_id, None)

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
        result = await _run_cancellable(request.request_id, decide(
            request.message,
            session_id=request.session_id,
            asp_session=request.asp_session,
            login_id=request.login_id,
            user_id=request.user_id,
            role_id=request.role_id,
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
        if isinstance(result, ChatResponse):
            return result
        return ChatResponse(**result)
    except asyncio.CancelledError:
        logger.info("Chat request stopped by user: session=%s", request.session_id or "anonymous")
        raise
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
        return ChatResponse(**result)
    except asyncio.CancelledError:
        logger.info("Comparison request stopped by user: session=%s", request.session_id or "anonymous")
        raise
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
        return ChatResponse(**result)
    except asyncio.CancelledError:
        logger.info("Explain-category request stopped by user: category=%s", request.category)
        raise
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
async def speech_to_text(file: UploadFile = File(...)) -> dict:
    sarvam_api_key = os.environ.get("SARVAM_API_KEY", "")
    if not sarvam_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice transcription is unavailable right now. Please try again later.",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file received.",
        )

    logger.info("Speech-to-text request received: %d bytes", len(audio_bytes))

    # Sarvam rejects MIME types with codec parameters (e.g. "audio/webm;codecs=opus").
    # Strip everything after the first semicolon to get the bare MIME type.
    content_type = (file.content_type or "audio/webm").split(";")[0].strip()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": sarvam_api_key},
                files={
                    "file": (
                        file.filename or "audio.webm",
                        audio_bytes,
                        content_type,
                    )
                },
                data={"model": "saaras:v3", "mode": "transcribe", "language_code": "en-IN"},
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to transcribe audio right now. Please try again.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to transcribe audio right now. Please try again.",
        ) from exc

    transcript: str = resp.json().get("transcript", "").strip()
    logger.info("Speech-to-text completed successfully")
    return {"transcript": transcript}


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
async def get_status_errors(job_id: str) -> dict:
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
    return {"status": "done", **(payload or {})}


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
        return ChatResponse(**result)
    except asyncio.CancelledError:
        logger.info("Guided request stopped by user: session=%s", request.session_id)
        raise
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