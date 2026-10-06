# models.py â€” Pydantic request/response models for the /chat endpoint.
# ChatRequest: user message + optional session. ChatResponse: extracted intent, report_name, reply text.
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    """One prior turn replayed by the client for conversational context.

    H-04 (M-04 in the review numbering): the client is the only source of
    truth for this history — there is no server-side session transcript to
    check it against — so this model can only close the *shape* gaps (an
    arbitrary role value, an unbounded message, an unbounded history list),
    not verify that an "assistant" turn was genuinely said by the assistant.
    That is a standing architectural limitation, not something this model
    can fix on its own.
    """
    role: Literal["user", "assistant"]
    text: str = Field(..., max_length=2000)


class ChatRequest(BaseModel):
    message:              str            = Field(..., min_length=1, max_length=2000)
    session_id:           Optional[str]  = Field(None, max_length=128)
    asp_session:          Optional[str]  = Field(None, max_length=1024)  # forwarded .AspNetCore.Session cookie
    login_id:             Optional[str]  = Field(None, max_length=256)   # user login ID for report authorisation
    # last 6-7 msgs; role restricted to user/assistant (no system/tool/developer
    # injection), each message capped, and the list itself capped at 7 items.
    conversation_history: list[HistoryItem] = Field(default_factory=list, max_length=7)
    beautify:             bool           = Field(True)  # when True, use LLM to format DB Q&A results
    user_id:              Optional[str]  = Field(None, max_length=128)  # current user's ID (for DB Q&A role check)
    role_id:              Optional[str]  = Field(None, max_length=64)   # current user's role ID (for DB Q&A admin check)
    request_id:           Optional[str]  = Field(None, max_length=64)   # client-generated ID; enables Stop Generation
    # Language the USER is writing in / wants replies in. BCP-47 base tag:
    # en | fr | ar | hi. Absent, empty or "en" => the request takes the exact
    # English path it took before multilingual support existed, with no
    # translation call. An unsupported tag degrades to English rather than
    # erroring — see backend/i18n/boundary.normalize_lang.
    lang:                 Optional[str]  = Field(None, max_length=8)

    # ── APP_VERSION=6.0 only — tenant resolution + instance-gen auth ──────────
    tenant_id:            Optional[str]  = Field(None, max_length=64)   # resolved TenantId, forwarded by the React frontend
    domain:               Optional[str]  = Field(None, max_length=256)  # fallback: looked up in XML_Tenant.xml if tenant_id absent
    jwt:                  Optional[str]  = Field(None, max_length=4096) # from CHATBOT_AUTH postMessage; replaces asp_session for 6.0's .NET API calls


class ChatResponse(BaseModel):
    intent: str = ""
    report_name: Optional[str] = None
    response_text: str = ""
    need_clarification: bool = False
    result_type: str = ""  # final | variance_table | disambiguation | date_selection | error | stopped | ""
    options: list[str] = []
    variance_data:    list[dict] = []   # TABLE dataset — top 30 rows
    # CHART dataset — every comparable row. Deliberately separate from
    # variance_data so the visualisation is never handed the table's slice.
    variance_all:     list[dict] = []
    # Coverage counts for the comparison (compared / concepts / dimensional /
    # significant / …) so the UI can state what the chart actually represents.
    variance_meta:    dict       = {}
    variance_label_a: str        = ""
    variance_label_b: str        = ""
    llm_summary:      str        = ""
    # True when llm_summary is Python's deterministic draft and has NOT been
    # through the model yet. The frontend uses it to decide whether to request
    # the polished version from /compare-summary — without it, any non-empty
    # summary looks final and the LLM never runs.
    llm_summary_is_draft: bool   = False
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

    # Chat language, same contract as ChatRequest.lang: absent/"en" keeps the
    # exact English behaviour and makes no translation call.
    lang:        Optional[str] = Field(None, max_length=8)

    # ── APP_VERSION=6.0 only — same contract as ChatRequest ───────────────────
    tenant_id:   Optional[str] = Field(None, max_length=64)    # resolved TenantId, forwarded by the React frontend
    domain:      Optional[str] = Field(None, max_length=256)   # fallback: looked up in XML_Tenant.xml if tenant_id absent
    jwt:         Optional[str] = Field(None, max_length=4096)  # from CHATBOT_AUTH postMessage

class CompareSummaryRow(BaseModel):
    """One variance row, in the shape the frontend already holds it (the
    `variance_data` it was sent). Posted back rather than re-derived from
    server-side session state, which expires — the comparison table is
    often still on screen long after the session that produced it is gone."""
    concept:     str                 = Field("", max_length=512)
    val_a:       Optional[float]     = None
    val_b:       Optional[float]     = None
    diff:        Optional[float]     = None
    pct_change:  Optional[float]     = None
    significant: bool                = False
    # Regulatory-importance context, echoed back so the ASYNC narrative reads
    # the same section/tier the table on screen was ranked by. Optional: a
    # return with no readable taxonomy posts these empty and the prompt falls
    # back to the plain variance wording.
    section:         str       = Field("", max_length=256)
    importance_tier: str       = Field("", max_length=16)
    mandated_by:     list[str] = Field(default_factory=list, max_length=8)
    # Needed by the explanation builder: selection reads concept_base (for the
    # max-3-variants-per-concept cap), importance/priority (for ordering) and
    # importance_matched (eligibility); share-of-total needs context_key to
    # find the parent row, and unit decides whether ₹ Cr formatting applies.
    concept_base:       str            = Field("", max_length=512)
    context_key:        str            = Field("", max_length=512)
    unit:               str            = Field("", max_length=64)
    section_code:       str            = Field("", max_length=16)
    importance:         Optional[float] = None
    priority:           Optional[float] = None
    importance_matched: bool            = False


class CompareSummaryRequest(BaseModel):
    """Request body for /compare-summary — the AI narrative for a variance
    table that has ALREADY been rendered.

    Split out from /compare-execute so the table and chart appear
    immediately: the summary takes ~140s against llama3.1 on CPU, which is
    far too long to hold the comparison response open for (see
    generate_llm_summary's own docstring)."""
    rows:        list[CompareSummaryRow] = Field(default_factory=list, max_length=2000)
    label_a:     str = Field("", max_length=256)
    label_b:     str = Field("", max_length=256)
    report_name: str = Field("", max_length=256)
    request_id:  Optional[str] = Field(None, max_length=64)  # enables Stop Generation
    # M-05: optional so existing callers that don't send it are unaffected;
    # checked by main.py's _caller_is_authenticated() fail-closed gate.
    login_id:    Optional[str] = Field(None, max_length=256)

    # APP_VERSION=6.0: without these, _caller_is_authenticated() resolves
    # login_id against the default/unscoped repo root instead of the
    # caller's own tenant -- a real 6.0 login_id is then never found and the
    # endpoint 403s every time, which this function's own error handling
    # silently turns into "AI analysis is unavailable" with no visible
    # cause. Same three fields ExplainCategoryRequest already carries for
    # the identical reason. No-op for 5.5 (all None -> _make_repo_scope's
    # root stays None).
    tenant_id:   Optional[str] = Field(None, max_length=128)
    domain:      Optional[str] = Field(None, max_length=256)
    jwt:         Optional[str] = Field(None, max_length=4096)

    # Chat language, same contract as ChatRequest.lang: absent/"en" keeps the
    # exact English behaviour and makes no translation call.
    lang:        Optional[str] = Field(None, max_length=8)


class ExplainCategoryRequest(BaseModel):
    """Request body for /explain-category — on-demand error explanation.

    L-17 / C-04: the client supplies only a bare filename (never a full
    path) plus form_id; the server rebuilds the real path via
    build_error_file_path() (backend/agent/error_explanation.py), the same
    helper /download-file already uses, instead of trusting a client-sent
    path. form_id is now required -- it's the other half of that rebuild.
    """
    filename:        str = Field(..., max_length=255)
    category:        str = Field(..., max_length=64)   # formula_error | xbrl_schema | dimensional
    form_id:         str = Field(..., max_length=64)
    report_name:     Optional[str] = Field(None, max_length=256)
    request_id:      Optional[str] = Field(None, max_length=64)  # client-generated ID; enables Stop Generation
    offset:          int = Field(0, ge=0)  # how many errors in this category are already explained (batching)

    # Chat language, same contract as ChatRequest.lang: absent/"en" keeps the
    # exact English behaviour and makes no translation call.
    lang:        Optional[str] = Field(None, max_length=8)

    # ── APP_VERSION=6.0 only — same contract as ChatRequest ───────────────────
    tenant_id:   Optional[str] = Field(None, max_length=64)    # resolved TenantId, forwarded by the React frontend
    domain:      Optional[str] = Field(None, max_length=256)   # fallback: looked up in XML_Tenant.xml if tenant_id absent
    jwt:         Optional[str] = Field(None, max_length=4096)  # from CHATBOT_AUTH postMessage


class FeedbackRequest(BaseModel):
    """Request body for /feedback — thumbs up/down on a completed assistant response."""
    rating:      str            = Field(..., pattern="^(up|down)$")
    query:       Optional[str]  = Field(None, max_length=2000)  # the user question this feedback is about
    intent:      Optional[str]  = Field(None, max_length=128)   # detected intent for that response, if any
    result_type: Optional[str]  = Field(None, max_length=64)    # e.g. db_qa_result, final, error
    session_id:  Optional[str]  = Field(None, max_length=128)



