"""Schema selection for backend/db_qa's XMLStore."""
from __future__ import annotations

from backend.db_qa.versions.loader import EntitySpec
from backend.db_qa.versions import v5_5_schema


def get_schema_map() -> dict[str, EntitySpec]:
    """Return the entity schema dict."""
    return v5_5_schema.SCHEMA


__all__ = ["get_schema_map", "EntitySpec"]
