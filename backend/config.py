# # config.py — Centralised path configuration for the Chat-System backend.
# # All file paths that point outside the project root are declared here so
# # they can be changed in one place without touching business logic.

# from __future__ import annotations

# import os

# # ---------------------------------------------------------------------------
# # Repository XML file paths
# # These files live in the external repository and are read live at runtime —
# # no static copies are kept inside the project.
# # Override any path via the corresponding environment variable.
# # ---------------------------------------------------------------------------

# RETURNS_XML_PATH: str = os.getenv(
#     "RETURNS_XML_PATH",
#     r"D:\Repo\Repo5.5 3\Repo5.5\Database\Returns.xml",
# )

# INSTANCE_LOG_XML_PATH: str = os.getenv(
#     "INSTANCE_LOG_XML_PATH",
#     r"D:\Repo\Repo5.5 3\Repo5.5\Database\XML_InstanceLog.xml",
# )

# # Base directory that contains one sub-folder per Report ID.
# # Structure: {INSTANCE_BASE_DIR}\{report_id}\*.xml
# INSTANCE_BASE_DIR: str = os.getenv(
#     "INSTANCE_BASE_DIR",
#     r"D:\Repo\Repo5.5 3\Repo5.5\Instance",  
# )

# # Base directory for rendered output files (HTML render documents).
# # Structure: {RENDER_BASE_DIR}\{report_id}\<RenderedExcelDocPath>
# RENDER_BASE_DIR: str = os.getenv(
#     "RENDER_BASE_DIR",
#     r"D:\Repo\Repo5.5 3\Repo5.5\Render",
# )

# # ---------------------------------------------------------------------------
# # User / Department authorisation XML file paths
# # XML_User.xml  : maps LoginId → DeptId
# # XML_Dept.xml  : maps DeptId  → pipe-separated list of allowed FormIds
# # ---------------------------------------------------------------------------

# XML_USER_PATH: str = os.getenv(
#     "XML_USER_PATH",
#     r"D:\Repo\Repo5.5 3\Repo5.5\Database\XML_User.xml",
# )

# XML_DEPT_PATH: str = os.getenv(
#     "XML_DEPT_PATH",
#     r"D:\Repo\Repo5.5 3\Repo5.5\Database\XML_Dept.xml",
# )

# # ---------------------------------------------------------------------------
# # SQL Agent — FAISS index output directory
# # Produced by running:  python sql_agent/main.py  (one-time setup)
# # Override via FAISS_OUTPUT_DIR env var.
# # ---------------------------------------------------------------------------
# _PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# FAISS_OUTPUT_DIR: str = os.getenv(
#     "FAISS_OUTPUT_DIR",
#     os.path.join(_PROJECT_ROOT, "sql_agent", "output"),
# )

# # XML_RoleAccess.xml: maps RoleId + OptionId → access flags (HasNew, HasEdit, HasView)
# XML_ROLE_ACCESS_PATH: str = os.getenv(
#     "XML_ROLE_ACCESS_PATH",
#     r"D:\Repo\Repo5.5 3\Repo5.5\Database\XML_RoleAccess.xml",
# )

# # ---------------------------------------------------------------------------
# # Application Database Q&A (optional feature — disabled if not configured)
# # Base directory containing iDEAL application XML files for Q&A queries
# # Structure: {APP_DB_BASE_PATH}/XML_User.xml, XML_Dept.xml, Returns.xml, etc.
# # If not set, DB Q&A feature is gracefully disabled
# # ---------------------------------------------------------------------------

# APP_DB_BASE_PATH: str | None = os.getenv("APP_DB_BASE_PATH") or None

# # Admin role ID for DB Q&A access control (default: "101" for iDEAL Admin)
# APP_DB_ADMIN_ROLE_ID: str = os.getenv("APP_DB_ADMIN_ROLE_ID", "101")

# # Enable LLM beautification of DB Q&A responses (default: true)
# APP_DB_ENABLE_BEAUTIFY: bool = os.getenv("APP_DB_ENABLE_BEAUTIFY", "true").lower() == "true"

# # Ollama model for DB Q&A beautification (default: phi3:mini)
# APP_DB_BEAUTIFY_MODEL: str = os.getenv("APP_DB_BEAUTIFY_MODEL", "phi3:mini")


# config.py — Centralised path configuration for the Chat-System backend.

# from __future__ import annotations

# import os

# # ---------------------------------------------------------------------------
# # Repository XML file paths
# # ---------------------------------------------------------------------------

# RETURNS_XML_PATH: str = os.getenv(
#     "RETURNS_XML_PATH",
#     r"D:\Repo(new)\DataBase\Returns.xml",
# )

# INSTANCE_LOG_XML_PATH: str = os.getenv(
#     "INSTANCE_LOG_XML_PATH",
#     r"D:\Repo(new)\DataBase\XML_InstanceLog.xml",
# )

# # ---------------------------------------------------------------------------
# # Instance / Render directories
# # ---------------------------------------------------------------------------

# INSTANCE_BASE_DIR: str = os.getenv(
#     "INSTANCE_BASE_DIR",
#     r"D:\Repo(new)\Instance",
# )

# RENDER_BASE_DIR: str = os.getenv(
#     "RENDER_BASE_DIR",
#     r"D:\Repo(new)\Render",
# )

# # ---------------------------------------------------------------------------
# # User / Department authorisation XML file paths
# # ---------------------------------------------------------------------------

# XML_USER_PATH: str = os.getenv(
#     "XML_USER_PATH",
#     r"D:\Repo(new)\DataBase\XML_User.xml",
# )

# XML_DEPT_PATH: str = os.getenv(
#     "XML_DEPT_PATH",
#     r"D:\Repo(new)\DataBase\XML_Dept.xml",
# )

# # ---------------------------------------------------------------------------
# # SQL Agent — FAISS index output directory
# # ---------------------------------------------------------------------------

# _PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# FAISS_OUTPUT_DIR: str = os.getenv(
#     "FAISS_OUTPUT_DIR",
#     os.path.join(_PROJECT_ROOT, "sql_agent", "output"),
# )

# # ---------------------------------------------------------------------------
# # Role access XML
# # ---------------------------------------------------------------------------



# XML_ROLE_ACCESS_PATH: str = os.getenv(
#     "XML_ROLE_ACCESS_PATH",
#     r"D:\Repo(new)\DataBase\XML_RoleAccess.xml",
# )

# # ---------------------------------------------------------------------------
# # Application Database Q&A
# # ---------------------------------------------------------------------------

# APP_DB_BASE_PATH: str | None = os.getenv(
#     "APP_DB_BASE_PATH",
#     r"D:\Repo(new)\DataBase",
# )

# # Admin role ID for DB Q&A access control
# APP_DB_ADMIN_ROLE_ID: str = os.getenv(
#     "APP_DB_ADMIN_ROLE_ID",
#     "101",
# )

# # Enable LLM beautification of DB Q&A responses
# APP_DB_ENABLE_BEAUTIFY: bool = (
#     os.getenv("APP_DB_ENABLE_BEAUTIFY", "true").lower() == "true"
# )

# # Ollama model for DB Q&A beautification
# APP_DB_BEAUTIFY_MODEL: str = os.getenv(
#     "APP_DB_BEAUTIFY_MODEL",
#     "phi3:mini",
# )


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