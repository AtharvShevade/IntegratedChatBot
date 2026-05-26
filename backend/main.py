# main.py — FastAPI entry point: /chat, /speech-to-text, /health.
# Start with: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

from __future__ import annotations

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
from backend.utils.logger import setup_logging  # noqa: E402
setup_logging()

from backend.agent import decide                      # noqa: E402
from backend.guided import guided_step, GUIDED_ACTIONS  # noqa: E402
from backend.models import ChatRequest, ChatResponse, CompareRequest  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm Ollama models, SentenceTransformer, and FAISS indexes on startup."""
    import asyncio

    # ── Pre-load SentenceTransformer + FAISS indexes in a thread so the async
    # event loop is not blocked.  This moves the cold-start penalty from the
    # first user query to server startup (invisible to users).
    def _warmup_embedding():
        try:
            import backend.sql_agent.vectorizer as _vec  # noqa: F401  triggers module-level load
            logger.info("[WARMUP] SentenceTransformer model loaded")
        except Exception as exc:
            logger.warning("[WARMUP] SentenceTransformer load failed: %s", exc)

        try:
            from backend.sql_agent.retriever import search
            from backend.sql_agent.config import (
                TABLE_INDEX_PATH, TABLE_META_PATH,
                COLUMN_INDEX_PATH, COLUMN_META_PATH,
            )
            import os as _os
            if _os.path.exists(TABLE_INDEX_PATH):
                search(TABLE_INDEX_PATH, TABLE_META_PATH, "warmup", k=1)
                logger.info("[WARMUP] Table FAISS index loaded")
            if _os.path.exists(COLUMN_INDEX_PATH):
                search(COLUMN_INDEX_PATH, COLUMN_META_PATH, "warmup", k=1)
                logger.info("[WARMUP] Column FAISS index loaded")
        except Exception as exc:
            logger.warning("[WARMUP] FAISS index load failed: %s", exc)

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
                logger.info("[WARMUP] model=%s loaded into memory", model)
            except Exception as exc:
                logger.warning("[WARMUP] failed for model=%s: %s", model, exc)
    yield


app = FastAPI(title="Report Assistant", version="3.0.0", lifespan=lifespan)

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
    logger.exception(
        "[UNHANDLED_ERROR] method=%s path=%s error=%s",
        request.method, request.url.path, type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again."},
    )


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    logger.info(
        "[REQUEST] mode=chat session=%s query=%r",
        request.session_id, request.message,
    )
    start = time.monotonic()
    try:
        result = await decide(
            request.message,
            session_id=request.session_id,
            asp_session=request.asp_session,
            login_id=request.login_id,
            conversation_history=request.conversation_history[-7:] if request.conversation_history else None,
        )
        elapsed = time.monotonic() - start
        logger.info(
            "[PERF] endpoint=/chat intent=%s duration=%.2fs session=%s",
            result.get("intent", "?"), elapsed, request.session_id,
        )
        return ChatResponse(**result)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error(
            "[LLM_UNAVAILABLE] Ollama unreachable for /chat — %s", exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI model unavailable. Make sure Ollama is running.",
        ) from exc


@app.post("/compare-execute", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def compare_execute(request: CompareRequest) -> ChatResponse:
    """Execute a pre-staged instance comparison directly — no intent detection.

    The frontend calls this after the user picks two instances from the dropdown
    UI. It resolves the full file paths from the server-side session state and
    runs the XBRL variance pipeline immediately.
    """
    from backend.agent import execute_comparison
    logger.info(
        "[REQUEST] mode=compare_execute session=%s instance_a=%d instance_b=%d",
        request.session_id, request.instance_a, request.instance_b,
    )
    start = time.monotonic()
    try:
        result = await execute_comparison(
            session_id=request.session_id,
            idx_a=request.instance_a,
            idx_b=request.instance_b,
        )
        elapsed = time.monotonic() - start
        logger.info(
            "[PERF] endpoint=/compare-execute duration=%.2fs session=%s",
            elapsed, request.session_id,
        )
        return ChatResponse(**result)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error(
            "[LLM_UNAVAILABLE] Ollama unreachable for /compare-execute — %s", exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI model unavailable. Make sure Ollama is running.",
        ) from exc


@app.post("/speech-to-text", status_code=status.HTTP_200_OK)
async def speech_to_text(file: UploadFile = File(...)) -> dict:
    sarvam_api_key = os.environ.get("SARVAM_API_KEY", "")
    if not sarvam_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SARVAM_API_KEY is not configured on the server.",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file received.",
        )

    logger.info("POST /speech-to-text ï¿½ forwarding %d bytes to Sarvam AI", len(audio_bytes))

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
            detail=f"Sarvam AI error: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Sarvam AI. Check network connectivity.",
        ) from exc

    transcript: str = resp.json().get("transcript", "").strip()
    logger.info("Sarvam AI transcript: %r", transcript)
    return {"transcript": transcript}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict:
    return {"status": "ok"}


@app.get("/download-file", status_code=status.HTTP_200_OK)
async def download_file(form_id: str, type: str, filename: str):
    """Serve a render or error file for download.

    Query params:
        form_id  — numeric report ID (non-numeric chars stripped server-side)
        type     — "render" | "error"
        filename — bare filename, no directory component allowed

    Security: form_id is sanitised to digits only; filename is reduced to its
    basename so path-traversal attempts ('../../../etc/passwd') are rejected.
    The resolved absolute path is verified to lie within the designated base
    directory before the file is opened.
    """
    import re as _re
    from pathlib import Path
    from fastapi.responses import FileResponse
    from backend.tools.report_lookup import build_render_file_path, build_error_file_path

    # ── Input validation ──────────────────────────────────────────────────────
    safe_fid  = _re.sub(r"[^0-9]", "", form_id)
    safe_name = os.path.basename(filename)  # strips any directory component

    if not safe_fid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form_id.")
    if not safe_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")
    if type not in ("render", "error"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be 'render' or 'error'.")

    # ── Path construction ─────────────────────────────────────────────────────
    if type == "render":
        from backend.config import RENDER_BASE_DIR
        file_path = build_render_file_path(safe_fid, safe_name)
        base_dir  = RENDER_BASE_DIR
        media     = "text/html"
    else:
        from backend.config import INSTANCE_BASE_DIR
        file_path = build_error_file_path(safe_fid, safe_name)
        base_dir  = INSTANCE_BASE_DIR
        media     = "application/xml"

    # ── Containment check — prevent directory traversal ───────────────────────
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
async def list_reports() -> dict:
    """Return all known report names from returns.xml — used for guided-mode autocomplete."""
    from backend.tools.report_lookup import _parse_returns
    names = sorted({r.get("Name", "") for r in _parse_returns() if r.get("Name")})
    return {"reports": names}


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
    try:
        result = await guided_step(
            request.message,
            session_id=request.session_id,
            asp_session=request.asp_session,
            login_id=request.login_id,
        )
        elapsed = time.monotonic() - start
        logger.info(
            "[PERF] endpoint=/guided result_type=%s duration=%.2fs session=%s",
            result.get("result_type", "?"), elapsed, request.session_id,
        )
        return ChatResponse(**result)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error(
            "[API_FAILURE] Ollama unreachable for /guided — %s", exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI model unavailable. Make sure Ollama is running.",
        ) from exc
