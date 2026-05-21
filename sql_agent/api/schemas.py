from typing import Any, List, Optional
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


class VoiceQueryResult(QueryResult):
    transcript: str
