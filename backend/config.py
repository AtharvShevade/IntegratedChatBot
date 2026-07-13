import os

# ---------------------------------------------------------------------------
# Base repository path
# ---------------------------------------------------------------------------

BASE_REPO_PATH: str = os.getenv(
    "BASE_REPO_PATH",
    r"D:\Repo(new)"
)

# ---------------------------------------------------------------------------
# Repository XML file paths
# ---------------------------------------------------------------------------

RETURNS_XML_PATH: str = os.path.join(
    BASE_REPO_PATH,
    "DataBase",
    "Returns.xml"
)

INSTANCE_LOG_XML_PATH: str = os.path.join(
    BASE_REPO_PATH,
    "DataBase",
    "XML_InstanceLog.xml"
)

# ---------------------------------------------------------------------------
# Instance / Render directories
# ---------------------------------------------------------------------------

INSTANCE_BASE_DIR: str = os.path.join(
    BASE_REPO_PATH,
    "Instance"
)

RENDER_BASE_DIR: str = os.path.join(
    BASE_REPO_PATH,
    "Render"
)

# ---------------------------------------------------------------------------
# User / Department authorisation XML file paths
# ---------------------------------------------------------------------------

XML_USER_PATH: str = os.path.join(
    BASE_REPO_PATH,
    "DataBase",
    "XML_User.xml"
)

XML_DEPT_PATH: str = os.path.join(
    BASE_REPO_PATH,
    "DataBase",
    "XML_Dept.xml"
)

# ---------------------------------------------------------------------------
# Role access XML
# ---------------------------------------------------------------------------

XML_ROLE_ACCESS_PATH: str = os.path.join(
    BASE_REPO_PATH,
    "DataBase",
    "XML_RoleAccess.xml"
)

# ---------------------------------------------------------------------------
# Scheduler Queue XML — one PENDING entry is appended per confirmed schedule
# ---------------------------------------------------------------------------



SCHEDULER_QUEUE_XML_PATH: str = os.path.join(
    BASE_REPO_PATH,
    "DataBase",
    "SchedulerQueue.xml"
)

# ---------------------------------------------------------------------------
# Application Database Q&A
# ---------------------------------------------------------------------------

APP_DB_BASE_PATH: str = os.path.join(
    BASE_REPO_PATH,
    "DataBase"
)

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

# ---------------------------------------------------------------------------
# Tenant-aware path resolution (6.0 only)
# ---------------------------------------------------------------------------
# These functions mirror the constants above but accept an optional
# tenant_id. When tenant_id is None (all 5.5 traffic), they return exactly
# the same value as the bare constant — zero behaviour change. When
# tenant_id is provided (6.0 traffic), paths are resolved under
# BASE_REPO_PATH/<tenant_id>/... using 6.0's filenames (see config_6_0.py —
# the 6.0 repo tree uses different XML filenames than 5.5, e.g. "User.xml"
# instead of "XML_User.xml").
#
# Existing code that imports the bare constants above is untouched and
# keeps working as-is. Only new/updated call sites that need tenant
# awareness should call these functions instead.


def _tenant_base(tenant_id: str | None) -> str:
    from backend.services.tenant_repo_service import get_repo_base_path
    return get_repo_base_path(tenant_id)


def get_returns_xml_path(tenant_id: str | None = None) -> str:
    if tenant_id:
        from backend import config_6_0
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.RETURN_XML_FILENAME)
    return RETURNS_XML_PATH


def get_instance_log_xml_path(tenant_id: str | None = None) -> str:
    if tenant_id:
        from backend import config_6_0
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.INSTANCE_LOG_XML_FILENAME)
    return INSTANCE_LOG_XML_PATH


def get_instance_base_dir(tenant_id: str | None = None) -> str:
    return os.path.join(_tenant_base(tenant_id), "Instance")


def get_render_base_dir(tenant_id: str | None = None) -> str:
    return os.path.join(_tenant_base(tenant_id), "Render")


def get_user_xml_path(tenant_id: str | None = None) -> str:
    if tenant_id:
        from backend import config_6_0
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.USER_XML_FILENAME)
    return XML_USER_PATH


def get_dept_xml_path(tenant_id: str | None = None) -> str:
    if tenant_id:
        from backend import config_6_0
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.DEPT_XML_FILENAME)
    return XML_DEPT_PATH


def get_role_access_xml_path(tenant_id: str | None = None) -> str:
    if tenant_id:
        from backend import config_6_0
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.ROLE_ACCESS_XML_FILENAME)
    return XML_ROLE_ACCESS_PATH


def get_scheduler_queue_xml_path(tenant_id: str | None = None) -> str:
    if tenant_id:
        from backend import config_6_0
        if not config_6_0.SCHEDULER_QUEUE_XML_FILENAME:
            raise NotImplementedError(
                "No confirmed 6.0 XBRL scheduler queue file exists yet "
                "(set XML_6_0_SCHEDULER_FILENAME once one does)."
            )
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.SCHEDULER_QUEUE_XML_FILENAME)
    return SCHEDULER_QUEUE_XML_PATH


def get_period_xml_path(tenant_id: str | None = None) -> str:
    """6.0-only — 5.5 uses a project-relative logs/period.xml, not a repo path."""
    if tenant_id:
        from backend import config_6_0
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.PERIOD_XML_FILENAME)
    raise NotImplementedError("period.xml is project-relative in 5.5 — see instance_generator.py._PERIOD_FILE")


def get_option_xml_path(tenant_id: str | None = None) -> str:
    """6.0-only — Option.xml (menu/permission-option registry) has no 5.5 equivalent.

    5.5's XML_RoleAccess.xml uses self-describing string OptionIds directly
    (e.g. "CreateInstance"), so no separate option-name lookup table is needed.
    """
    if tenant_id:
        from backend import config_6_0
        return os.path.join(_tenant_base(tenant_id), "DataBase", config_6_0.OPTION_XML_FILENAME)
    raise NotImplementedError("Option.xml has no 5.5 equivalent — 5.5's RoleAccess.xml OptionId is self-describing.")


def get_app_db_base_path(tenant_id: str | None = None) -> str:
    return os.path.join(_tenant_base(tenant_id), "DataBase")


# import os

# # ---------------------------------------------------------------------------
# # Base repository path
# # ---------------------------------------------------------------------------

# BASE_REPO_PATH = os.getenv(
#     "BASE_REPO_PATH",
#     r"D:\Repo\Repo5.5 3\Repo5.5"
# )

# # ---------------------------------------------------------------------------
# # Database folder
# # ---------------------------------------------------------------------------

# DATABASE_DIR = os.path.join(BASE_REPO_PATH, "Database")

# # ---------------------------------------------------------------------------
# # Repository XML files
# # ---------------------------------------------------------------------------

# RETURNS_XML_PATH = os.path.join(DATABASE_DIR, "Returns.xml")

# INSTANCE_LOG_XML_PATH = os.path.join(
#     DATABASE_DIR,
#     "XML_InstanceLog.xml"
# )

# XML_USER_PATH = os.path.join(
#     DATABASE_DIR,
#     "XML_User.xml"
# )

# XML_DEPT_PATH = os.path.join(
#     DATABASE_DIR,
#     "XML_Dept.xml"
# )

# XML_ROLE_ACCESS_PATH = os.path.join(
#     DATABASE_DIR,
#     "XML_RoleAccess.xml"
# )

# SCHEDULER_QUEUE_XML_PATH = os.path.join(
#     DATABASE_DIR,
#     "SchedulerQueue.xml"
# )

# # ---------------------------------------------------------------------------
# # Instance / Render directories
# # ---------------------------------------------------------------------------

# INSTANCE_BASE_DIR = os.path.join(
#     BASE_REPO_PATH,
#     "Instance"
# )

# RENDER_BASE_DIR = os.path.join(
#     BASE_REPO_PATH,
#     "Render"
# )

# # ---------------------------------------------------------------------------
# # Application Database Q&A
# # ---------------------------------------------------------------------------

# APP_DB_BASE_PATH = DATABASE_DIR

# # ---------------------------------------------------------------------------
# # SQL Agent FAISS output
# # ---------------------------------------------------------------------------

# _PROJECT_ROOT = os.path.dirname(
#     os.path.dirname(os.path.abspath(__file__))
# )

# FAISS_OUTPUT_DIR = os.getenv(
#     "FAISS_OUTPUT_DIR",
#     os.path.join(_PROJECT_ROOT, "sql_agent", "output")
# )

# # ---------------------------------------------------------------------------
# # Admin role
# # ---------------------------------------------------------------------------

# APP_DB_ADMIN_ROLE_ID = os.getenv(
#     "APP_DB_ADMIN_ROLE_ID",
#     "101"
# )

# # ---------------------------------------------------------------------------
# # Beautification
# # ---------------------------------------------------------------------------

# APP_DB_ENABLE_BEAUTIFY = (
#     os.getenv("APP_DB_ENABLE_BEAUTIFY", "true").lower() == "true"
# )

# APP_DB_BEAUTIFY_MODEL = os.getenv(
#     "APP_DB_BEAUTIFY_MODEL",
#     "phi3:mini"
# )