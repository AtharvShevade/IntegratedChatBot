# models.py â€” Pydantic request/response models for the /chat endpoint.
# ChatRequest: user message + optional session. ChatResponse: extracted intent, report_name, reply text.
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message:              str            = Field(..., min_length=1, max_length=2000)
    session_id:           Optional[str]  = Field(None, max_length=128)
    asp_session:          Optional[str]  = Field(None, max_length=1024)  # forwarded .AspNetCore.Session cookie (5.5 only)
    login_id:             Optional[str]  = Field(None, max_length=256)   # user login ID for report authorisation
    tenant_id:            Optional[str]  = Field(None, max_length=64)    # 6.0 only — resolved client-side from JWT claim
    jwt:                  Optional[str]  = Field(None, max_length=4096)  # 6.0 only — raw JWT, forwarded as Bearer token to .NET APIs that need it (e.g. instance generation)
    conversation_history: list[dict]     = Field(default_factory=list)   # last 6-7 msgs: [{"role":"user"|"assistant","text":"..."}]
    beautify:             bool           = Field(True)  # when True, use LLM to format DB Q&A results
    user_id:              Optional[str]  = Field(None, max_length=128)  # current user's ID (for DB Q&A role check)
    role_id:              Optional[str]  = Field(None, max_length=64)   # current user's role ID (for DB Q&A admin check)
    request_id:           Optional[str]  = Field(None, max_length=64)   # client-generated ID; enables Stop Generation


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
    error_details:    list[dict] = []   # structured XBRL validation errors with LLM explanations

    # ── NEW: generic status/error metadata for frontend (status_code, error_category_counts) ──
    data: dict = {}

    # ── SQL / Database query result fields ────────────────────────────────────
    db_columns:      list[str]       = []    # column headers from Oracle
    db_rows:         list[list]      = []    # serialized rows (JSON-safe types)
    db_sql:          str             = ""   # generated SQL shown to user
    db_error:        Optional[str]   = None  # Oracle error message if any
    accuracy_hint:   Optional[str]   = None  # soft tip to add time context
    needs_more_info: bool            = False # True when query is too vague
    more_info_hint:  Optional[str]   = None  # guidance for the user

    # ── App Database (XML) Q&A result fields ──────────────────────────────────
    db_intent:       str             = ""   # detected intent (e.g., USER_LIST, DEPT_INFO)
    db_found:        bool            = False # True if query returned records
    db_records:      list[dict]      = []   # structured rows from XML lookup
    db_summary:      str             = ""   # plain-text fallback response
    db_beautified:   str             = ""   # LLM-formatted response (when beautify=True)
    db_qa_data:      dict            = {}   # structured table data for frontend renderer

    # ── Async error enrichment ─────────────────────────────────────────────────
    job_id: Optional[str] = None

class CompareRequest(BaseModel):
    """Direct compare-execute request — bypasses intent detection entirely."""
    session_id:  str = Field(..., max_length=128)
    instance_a:  int = Field(..., ge=0)   # 0-based index into session's cmp_instances
    instance_b:  int = Field(..., ge=0)
    request_id:  Optional[str] = Field(None, max_length=64)  # client-generated ID; enables Stop Generation
    tenant_id:   Optional[str] = Field(None, max_length=64)   # 6.0 only

class ExplainCategoryRequest(BaseModel):
    """Request body for /explain-category — on-demand error explanation."""
    error_file_path: str = Field(..., max_length=1024)
    category:        str = Field(..., max_length=64)   # formula_error | xbrl_schema | dimensional
    form_id:         Optional[str] = Field(None, max_length=64)
    report_name:     Optional[str] = Field(None, max_length=256)
    request_id:      Optional[str] = Field(None, max_length=64)  # client-generated ID; enables Stop Generation
    tenant_id:       Optional[str] = Field(None, max_length=64)   # 6.0 only



