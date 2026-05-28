# config.py — Database Q&A module configuration.
# Database path for iDEAL application XML files (users, departments, roles, returns, etc.)
# Override via environment variable APP_DB_BASE_PATH.

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# iDEAL Application Database XML directory
# Should contain: XML_User.xml, XML_Dept.xml, XML_Role.xml, Returns.xml, etc.
# Feature is disabled if this path is not set (graceful degradation).
# ---------------------------------------------------------------------------

APP_DB_BASE_PATH: str | None = os.getenv(
    "APP_DB_BASE_PATH",
    None,  # No default; set explicitly to enable feature
)

# Admin role ID for access control (default iDEAL convention: 101 = "Admin User")
APP_DB_ADMIN_ROLE_ID: str = os.getenv(
    "APP_DB_ADMIN_ROLE_ID",
    "101",
)

# Enable LLM beautifier for natural language formatting (default: True)
# If False, returns plain-text summaries without calling Ollama
APP_DB_ENABLE_BEAUTIFY: bool = os.getenv("APP_DB_ENABLE_BEAUTIFY", "true").lower() == "true"

# Ollama model to use for beautifier (must match a running Ollama instance)
APP_DB_BEAUTIFY_MODEL: str = os.getenv(
    "APP_DB_BEAUTIFY_MODEL",
    "phi3:mini",
)
