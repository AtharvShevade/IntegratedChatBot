"""Version-aware schema selection for backend/db_qa's XMLStore.

get_schema_map() branches purely on backend.version_mode.IS_6_0 / IS_5_5 —
it does NOT take a tenant_id. This is a deliberate assumption, confirmed
against backend/config_6_0.py: 6.0 filenames are fixed across every
tenant (only the containing folder differs per tenant, resolved separately
via tenant_repo_service.get_repo_base_path). If a future 6.0 deployment
ever needs per-tenant filename overrides, get_schema_map's signature must
change deliberately — do not silently assume this still holds.
"""
from __future__ import annotations

from backend import version_mode
from backend.db_qa.versions.loader import EntitySpec
from backend.db_qa.versions import v5_5_schema, v6_0_schema


def get_schema_map() -> dict[str, EntitySpec]:
    """Return the entity schema dict for the currently active APP_VERSION."""
    if version_mode.IS_6_0:
        return v6_0_schema.SCHEMA
    return v5_5_schema.SCHEMA


__all__ = ["get_schema_map", "EntitySpec"]
