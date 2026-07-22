"""Schema selection for backend/db_qa's XMLStore."""
from __future__ import annotations

from backend import version_config
from backend.db_qa.versions.loader import EntitySpec
from backend.db_qa.versions import v5_5_schema
from backend.db_qa.versions import v6_0_schema


def get_schema_map() -> dict[str, EntitySpec]:
    """Return the entity schema dict for the active APP_VERSION."""
    return v6_0_schema.SCHEMA if version_config.IS_V6 else v5_5_schema.SCHEMA


__all__ = ["get_schema_map", "EntitySpec"]
