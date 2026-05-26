# models.py â€” Pydantic request/response models for the /chat endpoint.
# ChatRequest: user message + optional session. ChatResponse: extracted intent, report_name, reply text.
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message:              str            = Field(..., min_length=1, max_length=2000)
    session_id:           Optional[str]  = Field(None, max_length=128)
    asp_session:          Optional[str]  = Field(None, max_length=1024)  # forwarded .AspNetCore.Session cookie
    login_id:             Optional[str]  = Field(None, max_length=256)   # user login ID for report authorisation
    conversation_history: list[dict]     = Field(default_factory=list)   # last 6-7 msgs: [{"role":"user"|"assistant","text":"..."}]


class ChatResponse(BaseModel):
    intent: str = ""
    report_name: Optional[str] = None
    response_text: str = ""
    need_clarification: bool = False
    result_type: str = ""  # final | variance_table | disambiguation | date_selection | error | ""
    options: list[str] = []
    variance_data:    list[dict] = []
    variance_label_a: str        = ""
    variance_label_b: str        = ""
    llm_summary:      str        = ""
    instances_data:   list[dict] = []   # rich metadata for instance_selection UI
    download_url:     str        = ""   # relative /download-file URL (empty when N/A)
    download_label:   str        = ""   # e.g. "Download Render File"
    status_note:      str        = ""   # e.g. in-progress message or "file not found"


    # ── SQL / Database query result fields ────────────────────────────────────
    db_columns:      list[str]       = []    # column headers from Oracle
    db_rows:         list[list]      = []    # serialized rows (JSON-safe types)
    db_sql:          str             = ""   # generated SQL shown to user
    db_error:        Optional[str]   = None  # Oracle error message if any
    accuracy_hint:   Optional[str]   = None  # soft tip to add time context
    needs_more_info: bool            = False # True when query is too vague
    more_info_hint:  Optional[str]   = None  # guidance for the user


class CompareRequest(BaseModel):
    """Direct compare-execute request — bypasses intent detection entirely."""
    session_id:  str = Field(..., max_length=128)
    instance_a:  int = Field(..., ge=0)   # 0-based index into session's cmp_instances
    instance_b:  int = Field(..., ge=0)
