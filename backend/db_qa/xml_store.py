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
        """O(1) role-name lookup via the role index."""
        by_id, _ = self._role_index()
        r = by_id.get(str(role_id).strip())
        return r.get("Name", role_id) if r else role_id

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

    def _user_index(self) -> tuple[dict, dict]:
        """Build and cache (by_id, by_loginid) lookup maps from XML_User.xml.

        Avoids repeated O(n) linear scans across the user list for every call.
        The index is stored in the shared _cache under a sentinel key so it is
        built at most once per XMLStore lifetime.
        """
        key = "__user_index__"
        if key not in self._cache:
            by_id: dict[str, dict] = {}
            by_loginid: dict[str, dict] = {}
            for u in self.users():
                uid = u.get("UserId", "")
                lid = u.get("LoginId", "").strip().lower()
                if uid:
                    by_id[str(uid)] = u
                if lid:
                    by_loginid[lid] = u
            self._cache[key] = (by_id, by_loginid)  # type: ignore[assignment]
        return self._cache[key]  # type: ignore[return-value]

    def user_by_id(self, user_id: str) -> dict | None:
        by_id, _ = self._user_index()
        u = by_id.get(str(user_id))
        return _safe(u) if u else None

    def user_by_name(self, name: str) -> dict | None:
        """Find a user by display Name, LoginId, or numeric UserId string."""
        nl = name.strip().lower()
        by_id, by_loginid = self._user_index()
        # O(1): LoginId index
        if nl in by_loginid:
            return _safe(by_loginid[nl])
        # O(1): numeric UserId
        u = by_id.get(name.strip())
        if u:
            return _safe(u)
        # Fallback: linear scan on display Name only
        for u in self.users():
            if u.get("Name", "").strip().lower() == nl:
                return _safe(u)
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

    # ── enrichment helpers ───────────────────────────────────────────────────

    def option_name_by_id(self, option_id: str) -> str:
        """Return human-readable OptionName for an OptionId from XML_Option.xml."""
        for o in self.options():
            if o.get("OptionId") == option_id:
                return o.get("OptionName", option_id)
        return option_id

    def enrich_role_access(self, access: dict) -> dict:
        """Add OptionName (human-readable module name) to a RoleAccess row."""
        r = dict(access)
        r["OptionName"] = self.option_name_by_id(r.get("OptionId", ""))
        return r

    def login_id_to_name(self, login_id: str) -> str:
        """Resolve a LoginId string to the user's display Name (best-effort)."""
        if not login_id:
            return login_id
        u = self.user_by_name(login_id)
        return u.get("Name", login_id) if u else login_id

    def enrich_log_entry(self, entry: dict, id_field: str = "UserId") -> dict:
        """Add UserName by resolving *id_field* (LoginId) in audit/upload log rows."""
        r = dict(entry)
        login_id = r.get(id_field, "")
        if login_id:
            r["UserName"] = self.login_id_to_name(login_id)
        return r

    def enrich_cross_val_entry(self, entry: dict) -> dict:
        """Enrich a cross-validation log row with UserName (resolved from GeneratedBy)."""
        r = dict(entry)
        generated_by = r.get("GeneratedBy", "")
        if generated_by:
            r["UserName"] = self.login_id_to_name(generated_by)
        return r

    def enrich_instance_log_entry(self, log_entry: dict) -> dict:
        """Enrich an instance log row with StatusLabel, ReturnName, and UserName.

        XML_InstanceLog.xml stores LoginId (e.g. 'iris810') in its UserId field,
        not the numeric UserId from XML_User.xml.  This method resolves that to a
        display Name so callers get 'Abhay Pandey' instead of 'iris810'.
        """
        r = dict(log_entry)
        r["StatusLabel"] = SUBMISSION_STATUS_LABELS.get(r.get("Status", ""), r.get("Status", "Unknown"))
        r["ReturnName"] = self.return_name_by_id(r.get("FormId", ""))
        login_id = r.get("UserId", "")
        if login_id:
            r["UserName"] = self.login_id_to_name(login_id)
        return r

    # ── Generic indexes (built once, O(1) lookups after first call) ──────────

    def _dept_index(self) -> tuple[dict, dict]:
        """Build and cache (by_id, by_name_lower) maps for departments."""
        key = "__dept_index__"
        if key not in self._cache:
            by_id: dict[str, dict] = {}
            by_name: dict[str, dict] = {}
            for d in self.departments():
                did = get_attr(d, "DeptId", "Id", default="")
                nl = d.get("Name", "").strip().lower()
                if did:
                    by_id[did] = d
                if nl:
                    by_name[nl] = d
            self._cache[key] = (by_id, by_name)  # type: ignore[assignment]
        return self._cache[key]  # type: ignore[return-value]

    def _role_index(self) -> tuple[dict, dict]:
        """Build and cache (by_id, by_name_lower) maps for roles."""
        key = "__role_index__"
        if key not in self._cache:
            by_id: dict[str, dict] = {}
            by_name: dict[str, dict] = {}
            for r in self.roles():
                rid = get_attr(r, "RoleId", "Role_Id", default="")
                nl = r.get("Name", "").strip().lower()
                if rid:
                    by_id[rid] = r
                if nl:
                    by_name[nl] = r
            self._cache[key] = (by_id, by_name)  # type: ignore[assignment]
        return self._cache[key]  # type: ignore[return-value]

    def _return_index(self) -> tuple[dict, dict]:
        """Build and cache (by_id, by_name_lower) maps for returns (XBRL + non-XBRL)."""
        key = "__return_index__"
        if key not in self._cache:
            by_id: dict[str, dict] = {}
            by_name: dict[str, dict] = {}
            for r in list(self.returns()) + list(self.non_xbrl_returns()):
                rid = get_attr(r, "ReturnId", "Id", default="")
                nl = r.get("Name", "").strip().lower()
                if rid:
                    by_id[rid] = r
                if nl:
                    by_name[nl] = r
            self._cache[key] = (by_id, by_name)  # type: ignore[assignment]
        return self._cache[key]  # type: ignore[return-value]

    # ── Optimised lookups using indexes ──────────────────────────────────────

    def dept_by_id(self, dept_id: str) -> dict | None:
        """O(1) lookup: department by DeptId.  Returns None when ID is empty."""
        did = str(dept_id).strip()
        if not did:
            return None
        by_id, _ = self._dept_index()
        return by_id.get(did)

    def dept_by_name(self, name: str) -> dict | None:
        """O(1) case-insensitive lookup: department by Name."""
        nl = name.strip().lower()
        _, by_name = self._dept_index()
        return by_name.get(nl)

    def role_by_name(self, name: str) -> dict | None:
        """O(1) case-insensitive lookup: role by Name."""
        nl = name.strip().lower()
        _, by_name = self._role_index()
        return by_name.get(nl)

    def role_by_id(self, role_id: str) -> dict | None:
        """O(1) lookup: role by RoleId."""
        by_id, _ = self._role_index()
        return by_id.get(str(role_id).strip())

    def return_by_name(self, name: str) -> dict | None:
        """O(1) case-insensitive lookup: return by Name (XBRL + non-XBRL)."""
        nl = name.strip().lower()
        _, by_name = self._return_index()
        return by_name.get(nl)

    def return_by_id(self, return_id: str) -> dict | None:
        """O(1) lookup: return by ReturnId (XBRL + non-XBRL)."""
        by_id, _ = self._return_index()
        return by_id.get(str(return_id).strip())

    # ── Fuzzy resolve helpers (uses difflib — no ML) ──────────────────────────

    def resolve_user(self, query: str) -> dict | None:
        """Best-effort user lookup: exact by LoginId/Name/UserId, then fuzzy on Name.

        Suitable for entity extraction where the user typed a partial name.
        Returns a safe (password-stripped) user dict, or None.
        """
        if not query:
            return None
        # Fast path — exact matches
        u = self.user_by_name(query) or self.user_by_id(query)
        if u:
            return u
        # Fuzzy fallback on display names
        import difflib
        names = [u.get("Name", "") for u in self.users() if u.get("Name")]
        matches = difflib.get_close_matches(query, names, n=1, cutoff=0.65)
        if matches:
            return self.user_by_name(matches[0])
        return None

    def resolve_dept(self, query: str) -> dict | None:
        """Best-effort department lookup: exact by Name, then fuzzy."""
        if not query:
            return None
        d = self.dept_by_name(query)
        if d:
            return d
        import difflib
        names = [d.get("Name", "") for d in self.departments() if d.get("Name")]
        matches = difflib.get_close_matches(query, names, n=1, cutoff=0.70)
        if matches:
            return self.dept_by_name(matches[0])
        return None

    def resolve_role(self, query: str) -> dict | None:
        """Best-effort role lookup: exact by Name, then fuzzy."""
        if not query:
            return None
        r = self.role_by_name(query)
        if r:
            return r
        import difflib
        names = [r.get("Name", "") for r in self.roles() if r.get("Name")]
        matches = difflib.get_close_matches(query, names, n=1, cutoff=0.70)
        if matches:
            return self.role_by_name(matches[0])
        return None

    def resolve_return(self, query: str) -> dict | None:
        """Best-effort return lookup: exact by Name or ID, then fuzzy on Name."""
        if not query:
            return None
        r = self.return_by_name(query) or self.return_by_id(query)
        if r:
            return r
        import difflib
        _, by_name = self._return_index()
        names = list(by_name.keys())
        matches = difflib.get_close_matches(query.lower(), names, n=1, cutoff=0.65)
        if matches:
            return by_name.get(matches[0])
        return None
