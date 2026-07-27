import os

from backend import version_config

# ---------------------------------------------------------------------------
# Base repository path (5.5 — single flat root)
# ---------------------------------------------------------------------------

BASE_REPO_PATH: str = os.getenv(
    "BASE_REPO_PATH",
    r"D:\Repo(new)"
)

# ---------------------------------------------------------------------------
# 6.0 filename overrides — only the entities actually renamed under the
# tenant-scoped repo layout. Anything not listed here keeps its 5.5 filename
# on both versions (loader degrades to [] / logs a warning if it's wrong,
# it never raises).
# ---------------------------------------------------------------------------

_USER_FILENAME:         str = "User.xml"         if version_config.IS_V6 else "XML_User.xml"
_DEPT_FILENAME:         str = "Department.xml"   if version_config.IS_V6 else "XML_Dept.xml"
_ROLE_FILENAME:         str = "Role.xml"         if version_config.IS_V6 else "XML_Role.xml"
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


def xml_role_path() -> str:
    return _db_path(_ROLE_FILENAME)


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
# SQL Agent — FAISS index output directory
# ---------------------------------------------------------------------------

_PROJECT_ROOT: str = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

FAISS_OUTPUT_DIR: str = os.getenv(
    "FAISS_OUTPUT_DIR",
    os.path.join(_PROJECT_ROOT, "sql_agent", "output"),
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
