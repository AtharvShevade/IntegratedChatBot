# config.py — Centralised path configuration for the Chat-System backend.
# All file paths that point outside the project root are declared here so
# they can be changed in one place without touching business logic.

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Repository XML file paths
# These files live in the external repository and are read live at runtime —
# no static copies are kept inside the project.
# Override any path via the corresponding environment variable.
# ---------------------------------------------------------------------------

RETURNS_XML_PATH: str = os.getenv(
    "RETURNS_XML_PATH",
    r"D:\Repo\Repo5.5 3\Repo5.5\Database\Returns.xml",
)

INSTANCE_LOG_XML_PATH: str = os.getenv(
    "INSTANCE_LOG_XML_PATH",
    r"D:\Repo\Repo5.5 3\Repo5.5\Database\XML_InstanceLog.xml",
)

# Base directory that contains one sub-folder per Report ID.
# Structure: {INSTANCE_BASE_DIR}\{report_id}\*.xml
INSTANCE_BASE_DIR: str = os.getenv(
    "INSTANCE_BASE_DIR",
    r"D:\Repo\Repo5.5 3\Repo5.5\Instance",
)

# ---------------------------------------------------------------------------
# User / Department authorisation XML file paths
# XML_User.xml  : maps LoginId → DeptId
# XML_Dept.xml  : maps DeptId  → pipe-separated list of allowed FormIds
# ---------------------------------------------------------------------------

XML_USER_PATH: str = os.getenv(
    "XML_USER_PATH",
    r"D:\Repo\Repo5.5 3\Repo5.5\Database\XML_User.xml",
)

XML_DEPT_PATH: str = os.getenv(
    "XML_DEPT_PATH",
    r"D:\Repo\Repo5.5 3\Repo5.5\Database\XML_Dept.xml",
)
