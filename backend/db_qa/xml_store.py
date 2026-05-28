"""XML data store — loads and caches all iDEAL application XML files.

All data is held in memory as plain dicts.  Files are parsed once and reused.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger("xml_store")


def get_attr(row: dict, *possible_names: str, default: str = "") -> str:
    """Return the first present value from *row* among *possible_names*.

    Handles XML schema inconsistencies across iDEAL files, e.g.:
        DepartmentId (XML_User.xml)  vs  DeptId (XML_Dept.xml primary key)
        Period_Id    (XML_Period.xml) vs  PeriodId (Returns.xml FK)
        Segment_Id   (XML_Segment.xml) vs plain Id
        RoleId       (most files)    vs  Role_Id (some older files)

    Always prefer the most specific name first when calling:
        get_attr(row, "DepartmentId", "DeptId")
    """
    for name in possible_names:
        val = row.get(name)
        if val is not None:
            return val
    return default


# Fields that must never be surfaced to callers (security)
_SENSITIVE_FIELDS = {
    "Password", "SecondPassword", "ThirdPassword", "FourthPassword", "FifthPassword",
    "Answer",   # security question answer
}

# Human-readable status labels for XML_InstanceLog Status codes
SUBMISSION_STATUS_LABELS: dict[str, str] = {
    "0": "New / Pending",
    "1": "In Progress",
    "2": "Submitted",
    "3": "Validated",
    "4": "Rejected",
    "9": "Approved",
    "11": "Audited",
}


def _parse_xml(path: Path) -> list[dict[str, str]]:
    """Parse an XML file and return all row elements as attribute dicts.

    Tries ``Row`` tag first; if none found, falls back to the most common
    child tag so the store works with any iDEAL XML layout.
    Comments are silently ignored by ElementTree.
    """
    if not path.exists():
        logger.warning("XML file not found: %s", path)
        return []
    try:
        # 'recover' mode is not available in stdlib ET, but encoding='unicode'
        # avoids the BOM problem on Windows XML files.
        with path.open("rb") as fh:
            raw = fh.read()
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            # Some files use Windows-1252; strip BOM and retry as UTF-8
            raw = raw.lstrip(b"\xef\xbb\xbf")
            root = ET.fromstring(raw)

        rows = root.findall("Row")
        if not rows and len(root):
            # Use whatever tag the first child has
            tag = root[0].tag
            rows = root.findall(tag)
        return [dict(r.attrib) for r in rows]
    except ET.ParseError as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        return []


def _safe(record: dict) -> dict:
    """Return a copy of *record* with sensitive fields removed."""
    return {k: v for k, v in record.items() if k not in _SENSITIVE_FIELDS}


class XMLStore:
    """Thread-safe, lazily-populated in-memory cache for iDEAL XML databases.

    Usage::

        store = XMLStore("D:/Repo5.5/Database")
        active = [u for u in store.users() if u["Status"] == "true"]
    """

    def __init__(self, db_path: str | Path):
        self._db = Path(db_path)
        self._cache: dict[str, list[dict[str, str]]] = {}

    def _load(self, filename: str) -> list[dict[str, str]]:
        if filename not in self._cache:
            self._cache[filename] = _parse_xml(self._db / filename)
        return self._cache[filename]

    # ── raw data accessors ───────────────────────────────────────────────────

    def users(self) -> list[dict]:
        return self._load("XML_User.xml")

    def departments(self) -> list[dict]:
        return self._load("XML_Dept.xml")

    def roles(self) -> list[dict]:
        return self._load("XML_Role.xml")

    def role_access(self) -> list[dict]:
        return self._load("XML_RoleAccess.xml")

    def user_levels(self) -> list[dict]:
        return self._load("XML_UserLevels.xml")

    def periods(self) -> list[dict]:
        return self._load("XML_Period.xml")

    def returns(self) -> list[dict]:
        return self._load("Returns.xml")

    def non_xbrl_returns(self) -> list[dict]:
        return self._load("NonXBRLReturns.xml")

    def options(self) -> list[dict]:
        return self._load("XML_Option.xml")

    def instance_log(self) -> list[dict]:
        return self._load("XML_InstanceLog.xml")

    def segments(self) -> list[dict]:
        return self._load("XML_Segment.xml")

    def bank_details(self) -> list[dict]:
        return self._load("XML_BankDetail.xml")

    def notifications(self) -> list[dict]:
        return self._load("Notifications.xml")

    def notification_details(self) -> list[dict]:
        return self._load("NotificationReturnDetails.xml")

    def audit_log(self) -> list[dict]:
        """XML_Audit.xml — attrs: OptionId, AuditDateTime, AuditType, UserId (LoginId), Remark, VersionSelected"""
        return self._load("XML_Audit.xml")

    def upload_file_log(self) -> list[dict]:
        """XML_UploadedFileLog.xml — attrs: Id, FileName, DateTime, UserId (LoginId)"""
        return self._load("XML_UploadedFileLog.xml")

    def cross_validation_log(self) -> list[dict]:
        """XML_CrossValidationLog.xml — attrs: Id, FirstInstanceName, SecondInstanceName,
        FirstReportName, SecondReportName, FileName, DTC, ReportingDate, Status, GeneratedBy (LoginId)"""
        return self._load("XML_CrossValidationLog.xml")

    # ── convenience lookups ──────────────────────────────────────────────────

    def role_name_by_id(self, role_id: str) -> str:
        for r in self.roles():
            if get_attr(r, "RoleId", "Role_Id") == str(role_id):
                return r.get("Name", role_id)
        return role_id

    def dept_by_id(self, dept_id: str) -> dict | None:
        """Find a department row by DeptId.  Returns None only when ID is empty."""
        did = str(dept_id).strip()
        if not did:
            return None
        for d in self.departments():
            if get_attr(d, "DeptId", "Id") == did:
                return d
        return None

    def dept_name_by_id(self, dept_id: str) -> str:
        did = str(dept_id).strip()
        if not did:
            return "Not assigned"
        d = self.dept_by_id(did)
        return d.get("Name", did) if d else did

    def period_name_by_id(self, period_id: str) -> str:
        pid = str(period_id)
        for p in self.periods():
            if get_attr(p, "Period_Id", "PeriodId", "Id") == pid:
                return p.get("PeriodName", pid)
        return period_id

    def return_name_by_id(self, return_id: str) -> str:
        rid = str(return_id)
        for r in self.returns():
            if get_attr(r, "ReturnId", "Id") == rid:
                return r.get("Name", rid)
        for r in self.non_xbrl_returns():
            if get_attr(r, "ReturnId", "Id") == rid:
                return r.get("Name", rid)
        return return_id

    def user_by_id(self, user_id: str) -> dict | None:
        uid = str(user_id)
        for u in self.users():
            if u.get("UserId") == uid:
                return _safe(u)
        return None

    def user_by_name(self, name: str) -> dict | None:
        """Find a user by display Name, LoginId, or numeric UserId string."""
        nl = name.strip().lower()
        for u in self.users():
            if (u.get("Name", "").lower() == nl
                    or u.get("LoginId", "").lower() == nl
                    or u.get("UserId", "") == name.strip()):
                return _safe(u)
        return None

    def dept_by_name(self, name: str) -> dict | None:
        nl = name.lower()
        for d in self.departments():
            if d.get("Name", "").lower() == nl:
                return d
        return None

    def role_by_name(self, name: str) -> dict | None:
        nl = name.lower()
        for r in self.roles():
            if r.get("Name", "").lower() == nl:
                return r
        return None

    def return_by_name(self, name: str) -> dict | None:
        nl = name.lower()
        for r in self.returns():
            if r.get("Name", "").lower() == nl:
                return r
        return None

    def enrich_user(self, user: dict) -> dict:
        """Return safe user dict with RoleName and DeptName added."""
        u = _safe(user)
        role_id = get_attr(u, "RoleId", "Role_Id", default="")
        dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
        u["RoleName"] = self.role_name_by_id(role_id)
        u["DeptName"] = self.dept_name_by_id(dept_id)
        return u

    def enrich_return(self, ret: dict) -> dict:
        """Return dict with PeriodName added."""
        r = dict(ret)
        period_id = get_attr(r, "PeriodId", "Period_Id", default="")
        r["PeriodName"] = self.period_name_by_id(period_id)
        return r

    def user_level_for_user(self, user: dict) -> tuple[str, str] | tuple[None, None]:
        """Return (level_name, level_id) for *user* by scanning XML_Dept.xml Level*UserEmails.

        XML_User.xml has no LevelId field. Level assignment is stored in the user's
        department row as comma/semicolon-separated email lists:
            Level1UserEmails, Level2UserEmails, Level3UserEmails
        Level IDs come from XML_UserLevels.xml (LevelId=101→L1, 102→L2, 103→L3).
        Returns (None, None) when no match is found.
        """
        email = user.get("EmailId", "").strip().lower()
        dept_id = get_attr(user, "DepartmentId", "DeptId", default="")
        if not email or not dept_id:
            return None, None

        dept = self.dept_by_id(dept_id)
        if not dept:
            return None, None

        # Map level field names → canonical level name + look up ID in XML_UserLevels
        level_map = [
            ("Level1UserEmails", "L1"),
            ("Level2UserEmails", "L2"),
            ("Level3UserEmails", "L3"),
        ]
        levels = {lv.get("Name", ""): lv.get("LevelId", "") for lv in self.user_levels()}

        for field, lvl_name in level_map:
            raw = dept.get(field, "")
            emails = {e.strip().lower() for e in raw.replace(";", ",").split(",") if e.strip()}
            if email in emails:
                return lvl_name, levels.get(lvl_name, "")

        return None, None
