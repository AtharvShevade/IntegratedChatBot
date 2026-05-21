import os
import tempfile

import requests
from fastapi import APIRouter, File, HTTPException, UploadFile

from api.schemas import VoiceQueryResult
from api.utils import serialize_rows
from src.config import SARVAM_API_KEY
from src.executor import execute_query
from src.retriever import get_relevant_schema
from src.sql_generator import generate_sql, validate_sql

router = APIRouter(tags=["voice"])

_SARVAM_URL = "https://api.sarvam.ai/speech-to-text-translate"
_SARVAM_MODEL = "saaras:v2.5"


@router.post("/voice", response_model=VoiceQueryResult)
async def run_voice_query(audio: UploadFile = File(...), dialect: str = "Oracle"):
    if not SARVAM_API_KEY or SARVAM_API_KEY == "your_sarvam_api_key":
        raise HTTPException(status_code=500, detail="SARVAM_API_KEY is not configured in src/config.py")

    # Save uploaded audio to a temp file
    ext = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(await audio.read())

        # Transcribe + translate via Sarvam AI
        with open(tmp_path, "rb") as f:
            resp = requests.post(
                _SARVAM_URL,
                headers={"api-subscription-key": SARVAM_API_KEY},
                files={"file": (audio.filename or "audio.wav", f, audio.content_type or "audio/wav")},
                data={"model": _SARVAM_MODEL},
                timeout=60,
            )

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Sarvam AI error {resp.status_code}: {resp.text}")

        transcript = resp.json().get("transcript", "").strip()
        if not transcript:
            raise HTTPException(status_code=422, detail="No speech detected in the uploaded audio.")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Run the same pipeline as text query
    tables, columns, matched_labels = get_relevant_schema(transcript)

    if not tables:
        return VoiceQueryResult(
            query=transcript,
            transcript=transcript,
            matched_tables=[],
            matched_columns=[],
            sql="",
            is_valid=False,
            validation_reason="No matching tables found in the vector index.",
            columns=[],
            rows=[],
        )

    try:
        result = generate_sql(transcript, tables, columns, dialect=dialect, matched_labels=matched_labels)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    sql = result.get("sql", "")
    is_valid, reason = validate_sql(sql, tables, columns)

    col_names, rows, db_error = [], [], None
    if is_valid:
        col_names, rows, db_error = execute_query(sql)

    return VoiceQueryResult(
        query=transcript,
        transcript=transcript,
        matched_tables=[t["table"] for t in tables],
        matched_columns=[f"{c['table']}.{c['column']}" for c in columns],
        sql=sql,
        is_valid=is_valid,
        validation_reason=reason if not is_valid else None,
        columns=col_names,
        rows=serialize_rows(rows),
        db_error=db_error,
    )
