import os

# ---------------------------------------------------------------------------
# Base repository path
# ---------------------------------------------------------------------------

BASE_REPO_PATH: str = os.getenv(
    "BASE_REPO_PATH",
    r"D:\Repo\Repo5.5 3\Repo5.5"
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