from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    dialect: str = "Oracle"


class QueryResult(BaseModel):
    query: str
    matched_tables: List[str]
    matched_columns: List[str]
    sql: str
    is_valid: bool
    validation_reason: Optional[str] = None
    columns: List[str]
    rows: List[List[Any]]
    db_error: Optional[str] = None
    needs_more_info: bool = False
    more_info_hint: Optional[str] = None
    accuracy_hint: Optional[str] = None
    source: str = "llm_generated"  # "direct_match" when served from a near-exact qa_pairs.json example, no LLM call made
    match_score: Optional[float] = None  # literal text-similarity ratio (0-1) vs the matched qa_pairs.json question, when source == "direct_match"
    timings_ms: Optional[Dict[str, float]] = None  # per-stage wall-clock time in milliseconds, so latency is measured, not guessed at
