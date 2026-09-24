import os

from backend import version_config

# ---------------------------------------------------------------------------
# Backend port — single source of truth is BACKEND_PORT in the process's
# .env file. No port number is hardcoded here or anywhere else: each
# deployed instance (5.5, 6.0, or any future one) sets its own value
# directly in its own .env, e.g. BACKEND_PORT=8001. dev_server.py,
# service_server.py and backend/main.py's startup log all import this one
# constant instead of each reading/defaulting BACKEND_PORT independently,
# so changing the port for a deployment is a one-line .env edit.
# ---------------------------------------------------------------------------

def _read_backend_port() -> int:
    raw = os.getenv("BACKEND_PORT")
    if not raw or not raw.strip():
        raise RuntimeError(
            "BACKEND_PORT is not set. Set it in this process's .env file "
            "(e.g. BACKEND_PORT=8001) -- there is no hardcoded default."
        )
    return int(raw.strip())


BACKEND_PORT: int = _read_backend_port()

# ---------------------------------------------------------------------------
# Base repository path (5.5 — single flat root)
#
# Required on APP_VERSION=5.5 -- there is no hardcoded default. Each deployed
# instance sets its own repo root in its own .env; a missing value fails fast
# at import time instead of silently resolving paths under a stale/wrong
# drive. Not required on APP_VERSION=6.0 (which resolves its root per-tenant
# from APP_600_REPO_ROOT instead -- see version_config.py), so a 6.0-only
# deployment's .env does not need to carry this var.
# ---------------------------------------------------------------------------


def _read_base_repo_path() -> str:
    raw = os.getenv("BASE_REPO_PATH")
    if raw and raw.strip():
        return raw.strip()
    if version_config.IS_V6:
        # Not used on 6.0 (per-request tenant root instead); keep a harmless
        # placeholder so accidental 5.5-path helper calls fail loudly rather
        # than resolving under someone else's real repo root.
        return ""
    raise RuntimeError(
        "BASE_REPO_PATH is not set. Set it in this process's .env file "
        "(e.g. BASE_REPO_PATH=D:\\RepoCore_5.5) -- there is no hardcoded default."
    )


BASE_REPO_PATH: str = _read_base_repo_path()

# ---------------------------------------------------------------------------
# 6.0 filename overrides — only the entities actually renamed under the
# tenant-scoped repo layout. Anything not listed here keeps its 5.5 filename
# on both versions (loader degrades to [] / logs a warning if it's wrong,
# it never raises).
# ---------------------------------------------------------------------------

_USER_FILENAME:         str = "User.xml"         if version_config.IS_V6 else "XML_User.xml"
_DEPT_FILENAME:         str = "Department.xml"   if version_config.IS_V6 else "XML_Dept.xml"
_ROLE_ACCESS_FILENAME:  str = "RoleAccess.xml"   if version_config.IS_V6 else "XML_RoleAccess.xml"
_OPTION_FILENAME:       str = "Option.xml"       if version_config.IS_V6 else "XML_Option.xml"
_RETURNS_FILENAME:      str = "Return.xml"       if version_config.IS_V6 else "Returns.xml"
_INSTANCE_LOG_FILENAME: str = "InstanceLog.xml"  if version_config.IS_V6 else "XML_InstanceLog.xml"
_PERIOD_FILENAME:       str = "Period.xml"       if version_config.IS_V6 else "XML_Period.xml"
_SCHEDULER_QUEUE_FILENAME: str = "SchedulerQueue.xml"  # identical on both versions


def _active_root() -> str:
    """The repo root for the current request — BASE_REPO_PATH on 5.5,
    D:\\Repo6\\Repo6\\{TenantId} on 6.0 (see version_config.repo_scope)."""
    return version_config.get_repo_root_override() or BASE_REPO_PATH


def _db_path(filename: str) -> str:
    return os.path.join(_active_root(), "DataBase", filename)


# ---------------------------------------------------------------------------
# Repository XML file paths — version-aware functions.
#
# Call these instead of a frozen module-level string: the active root can
# change per-request under APP_VERSION=6.0 (one tenant per request), so the
# path must be resolved fresh on every call rather than once at import time.
# ---------------------------------------------------------------------------

def returns_xml_path() -> str:
    return _db_path(_RETURNS_FILENAME)


def instance_log_xml_path() -> str:
    return _db_path(_INSTANCE_LOG_FILENAME)


def xml_user_path() -> str:
    return _db_path(_USER_FILENAME)


def xml_dept_path() -> str:
    return _db_path(_DEPT_FILENAME)


def xml_role_access_path() -> str:
    return _db_path(_ROLE_ACCESS_FILENAME)


def xml_option_path() -> str:
    return _db_path(_OPTION_FILENAME)


def period_xml_path() -> str:
    return _db_path(_PERIOD_FILENAME)


def scheduler_queue_xml_path() -> str:
    return _db_path(_SCHEDULER_QUEUE_FILENAME)


def app_db_base_path() -> str:
    return os.path.join(_active_root(), "DataBase")


def instance_base_dir() -> str:
    return os.path.join(_active_root(), "Instance")


def render_base_dir() -> str:
    return os.path.join(_active_root(), "Render")


def json_metadata_base_dir() -> str:
    """Root of the per-return taxonomy-metadata JSON tree: Json/<form_id>/*.json."""
    return os.path.join(_active_root(), "Json")


# ---------------------------------------------------------------------------
# Backward-compatible module-level constants.
#
# These preserve the original 5.5 import style (`from backend.config import
# XML_USER_PATH`) for any caller not yet migrated to the function form above.
# IMPORTANT: because these are computed once at import time, they only ever
# reflect the root active at process startup — they are NOT tenant-aware.
# All 6.0-facing code (auth_service, report_lookup, instance_service,
# xml_store, scheduler_queue_service) must use the *_path()/*_dir() function
# forms above instead of these constants.
# ---------------------------------------------------------------------------

RETURNS_XML_PATH: str = returns_xml_path()
INSTANCE_LOG_XML_PATH: str = instance_log_xml_path()
INSTANCE_BASE_DIR: str = instance_base_dir()
RENDER_BASE_DIR: str = render_base_dir()
XML_USER_PATH: str = xml_user_path()
XML_DEPT_PATH: str = xml_dept_path()
XML_ROLE_ACCESS_PATH: str = xml_role_access_path()
SCHEDULER_QUEUE_XML_PATH: str = scheduler_queue_xml_path()
APP_DB_BASE_PATH: str = app_db_base_path()

# ---------------------------------------------------------------------------
# SQL Agent — FAISS index directory
# ---------------------------------------------------------------------------
# The agent resolves its own artefact paths from EMBEDDING_DIR (see
# backend/sql_agent/_bootstrap.py); this stays only as the historical name and
# now points at the same scoped folder rather than the retired output/ one.
# ---------------------------------------------------------------------------

_PROJECT_ROOT: str = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

FAISS_OUTPUT_DIR: str = os.getenv(
    "EMBEDDING_DIR",
    os.path.join(
        _PROJECT_ROOT, "sql_agent", "embedding_building", "cims_raq_quarterly"
    ),
)

# ---------------------------------------------------------------------------
# Admin role ID for DB Q&A access control
# ---------------------------------------------------------------------------

APP_DB_ADMIN_ROLE_ID: str = os.getenv(
    "APP_DB_ADMIN_ROLE_ID",
    "101",
)

# ---------------------------------------------------------------------------
# Enable LLM beautification of DB Q&A responses
# ---------------------------------------------------------------------------

APP_DB_ENABLE_BEAUTIFY: bool = (
    os.getenv("APP_DB_ENABLE_BEAUTIFY", "true").lower() == "true"
)

# ---------------------------------------------------------------------------
# Ollama model for DB Q&A beautification
# ---------------------------------------------------------------------------

APP_DB_BEAUTIFY_MODEL: str = os.getenv(
    "APP_DB_BEAUTIFY_MODEL",
    "phi3:mini",
)
