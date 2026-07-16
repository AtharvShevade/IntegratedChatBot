"""XML data store — loads and caches all iDEAL application XML files.

All data is held in memory as plain dicts.  Files are parsed on first access
and re-parsed automatically whenever the underlying file changes on disk
(detected via mtime comparison).  The cache is never stale for more than one
request cycle, without requiring a backend restart.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from backend.db_qa.versions import loader

logger = logging.getLogger("xml_store")


def is_active_status(value: str | None) -> bool:
    """True when a User/Department/Role `Status` value means active/enabled."""
    v = (value or "").strip().lower()
    return v == "true" or v == "1"


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
    "RefreshToken", "RefreshTokenExpiryTime",
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


def _safe(record: dict) -> dict:
    """Return a copy of *record* with sensitive fields removed."""
    return {k: v for k, v in record.items() if k not in _SENSITIVE_FIELDS}


class XMLStore:
    """Thread-safe, lazily-populated in-memory cache for iDEAL XML databases.

    Each raw XML file is loaded on first access and automatically reloaded
    whenever its on-disk modification time changes.  Derived in-memory indexes
    (user, dept, role, return) are evicted whenever their source file is
    reloaded so they are rebuilt on the next access.

    Usage::

        store = XMLStore("D:/Repo5.5/Database")
        active = [u for u in store.users() if u["Status"] == "true"]
    """

    # Maps each logical entity name → derived index sentinel keys that must
    # be evicted from _cache whenever that entity is reloaded.
    _INDEX_DEPS: dict[str, list[str]] = {
        "users":            ["__user_index__"],
        "departments":      ["__dept_index__"],
        "roles":            ["__role_index__"],
        "returns":          ["__return_index__"],
        "nonxbrl_returns":  ["__return_index__"],
    }

    # Entities not present in the schema still resolve here as best-effort
    # filenames so the file-not-found path (empty list, not an error) keeps
    # working exactly as before for any entity the schema doesn't define.
    _LEGACY_FALLBACK_FILENAMES: dict[str, str] = {
        "user_levels":            "XML_UserLevels.xml",
        "notifications":          "Notifications.xml",
        "notification_details":   "NotificationReturnDetails.xml",
        "segments":                "XML_Segment.xml",
        "error_log":               "XML_ErrorLog.xml",
        "uploaded_file_log":       "XML_UploadedFileLog.xml",
        "cross_validation_log":    "XML_CrossValidationLog.xml",
    }

    def __init__(self, db_path: str | Path | None = None):
        if db_path is not None:
            self._db = Path(db_path)
        else:
            from backend import config as _config
            self._db = Path(_config.APP_DB_BASE_PATH)

        from backend.db_qa import versions as _versions
        self._schema = _versions.v5_5_schema.SCHEMA

        # Raw-data cache: entity_name → list[row_dict]
        self._cache: dict[str, list[dict[str, str]]] = {}
        # Last-known mtime for each cached entity's source file
        self._mtime: dict[str, float] = {}
        # One lock per store instance; guards both _cache and _mtime
        self._lock = threading.Lock()

    def _resolve_source_path(self, entity_name: str) -> Path:
        """Return the on-disk path _load() should mtime-check for *entity_name*.

        Entities defined in the schema use their schema filename. Entities
        NOT in the schema at all (legacy-only lookups like
        user_levels/notifications) fall back to their 5.5-style filename so
        a missing file still resolves to a real (non-existent) path and
        degrades to [] via the existing OSError branch below, rather than
        raising or silently misbehaving.
        """
        spec = self._schema.get(entity_name)
        if spec is not None:
            return self._db / spec.filename
        filename = self._LEGACY_FALLBACK_FILENAMES.get(entity_name, entity_name)
        return self._db / filename

    def _load(self, entity_name: str) -> list[dict[str, str]]:
        """Return cached rows for *entity_name*, reloading from disk if the
        source file has been modified since the last load.

        Thread-safe: concurrent callers block on the per-store lock only for
        the brief mtime check (cache hit) or the full re-parse (cache miss /
        file changed).

        Edge cases:
        - File deleted / inaccessible: logs a warning and returns the stale
          cache if available, otherwise returns an empty list.
        - Parse error on reload: logs an error, keeps the previous good cache,
          and does NOT advance the stored mtime so the next request will retry.
        - Concurrent reload: the lock serialises all loaders; only the first
          thread does the actual disk I/O; subsequent threads see the freshly
          updated cache.
        - Entity not in the schema at all (e.g. user_levels): resolves to a
          non-existent path, degrades to [] the same way a genuinely-missing
          file always has.
        """
        path = self._resolve_source_path(entity_name)

        # ── 1. Read current mtime outside the lock (fast syscall, no I/O)
        try:
            current_mtime = os.path.getmtime(path)
        except OSError:
            # File is missing or inaccessible.
            with self._lock:
                if entity_name in self._cache:
                    logger.warning(
                        "[XMLStore] File inaccessible: %s — serving stale cache (%d rows)",
                        path, len(self._cache[entity_name]),
                    )
                    return self._cache[entity_name]
            logger.warning(
                "[XMLStore] File inaccessible and no prior cache for %s (entity=%s) — returning []",
                path, entity_name,
            )
            return []

        # ── 2. Fast-path cache hit: no lock needed for a pure read check
        #    (safe because Python dict reads are GIL-protected and we only
        #    confirm validity under the lock below when a reload is needed)
        if self._mtime.get(entity_name) == current_mtime and entity_name in self._cache:
            logger.debug("[XMLStore] Cache HIT: %s", entity_name)
            return self._cache[entity_name]

        # ── 3. Cache miss or file changed — acquire lock and re-check
        with self._lock:
            # Re-check inside the lock in case another thread already reloaded
            if self._mtime.get(entity_name) == current_mtime and entity_name in self._cache:
                logger.debug("[XMLStore] Cache HIT (post-lock): %s", entity_name)
                return self._cache[entity_name]

            prev_mtime = self._mtime.get(entity_name)
            if prev_mtime is None:
                logger.info("[XMLStore] Cache LOAD: %s", entity_name)
            else:
                logger.info(
                    "[XMLStore] File changed (mtime %.3f → %.3f), reloading: %s",
                    prev_mtime, current_mtime, entity_name,
                )

            spec = self._schema.get(entity_name)
            if spec is not None:
                data = loader.load_entity(
                    entity_name, self._db, schema=self._schema,
                )
            else:
                # Not in the schema — same degrade-to-[] behavior as a
                # missing file (e.g. user_levels).
                data = []

            if not data and entity_name in self._cache:
                # Parse returned nothing (error or genuinely empty file).
                # Keep the previous good cache rather than silently wiping data.
                # Do NOT update _mtime so the next request will retry.
                logger.warning(
                    "[XMLStore] Reload of %s returned 0 rows — keeping stale cache",
                    entity_name,
                )
                return self._cache[entity_name]

            self._cache[entity_name] = data
            self._mtime[entity_name] = current_mtime

            # Evict derived indexes whose source data just changed
            for idx_key in self._INDEX_DEPS.get(entity_name, []):
                if self._cache.pop(idx_key, None) is not None:
                    logger.debug(
                        "[XMLStore] Evicted derived index %s (source: %s)",
                        idx_key, entity_name,
                    )

            logger.info(
                "[XMLStore] Loaded %d rows from %s", len(data), entity_name
            )
            return data

    # ── raw data accessors ───────────────────────────────────────────────────

    def users(self) -> list[dict]:
        return self._load("users")

    def departments(self) -> list[dict]:
        return self._load("departments")

    def roles(self) -> list[dict]:
        return self._load("roles")

    def role_access(self) -> list[dict]:
        return self._load("role_access")

    def user_levels(self) -> list[dict]:
        return self._load("user_levels")

    def periods(self) -> list[dict]:
        return self._load("periods")

    def returns(self) -> list[dict]:
        return self._load("returns")

    def non_xbrl_returns(self) -> list[dict]:
        return self._load("nonxbrl_returns")

    def options(self) -> list[dict]:
        return self._load("options")

    def instance_log(self) -> list[dict]:
        return self._load("instance_log")

    def segments(self) -> list[dict]:
        return self._load("segments")

    def bank_details(self) -> list[dict]:
        return self._load("bank_details")

    def notifications(self) -> list[dict]:
        return self._load("notifications")

    def notification_details(self) -> list[dict]:
        return self._load("notification_details")

    def audit_log(self) -> list[dict]:
        """XML_Audit.xml — OptionId, AuditDateTime, AuditType, UserId (LoginId), Remark, VersionSelected."""
        return self._load("audit")

    def upload_file_log(self) -> list[dict]:
        """XML_UploadedFileLog.xml — attrs: Id, FileName, DateTime, UserId (LoginId)."""
        return self._load("uploaded_file_log")

    def cross_validation_log(self) -> list[dict]:
        """XML_CrossValidationLog.xml — attrs: Id, FirstInstanceName, SecondInstanceName,
        FirstReportName, SecondReportName, FileName, DTC, ReportingDate, Status, GeneratedBy (LoginId)."""
        return self._load("cross_validation_log")

    def nonxbrl_instance_log(self) -> list[dict]:
        """XML_NonXBRLInstanceLog.xml."""
        return self._load("nonxbrl_instance_log")

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

    def find_return_candidates(self, query: str, limit: int | None = 10) -> list[dict]:
        """Return ALL plausible return matches for *query*, not just one —
        for callers (e.g. next-reporting-date) that must ask the user to
        disambiguate rather than silently guess when a partial name like
        "cims" matches many returns (resolve_return()/return_by_name()
        collapse to a single best guess, which is wrong for that case).

        Cascades: exact Name/ReturnId -> compact-normalised exact match
        (so "cims ror" == "CIMS_ROR" == "cims-ror", same underscore/space/
        hyphen/paren-insensitive matching backend.tools.report_lookup.
        find_matching_reports() uses for status/generate/schedule — this
        store's return records differ from that module's Oracle-backed
        lookups, so the normalisation is duplicated locally rather than
        importing it, but the matching CONTRACT is intentionally the same)
        -> name starts-with query -> query appears anywhere in name ->
        fuzzy (difflib). Stops at the first tier that produces any match.

        *limit* caps how many rows are returned (None = unlimited) — pass
        None when the caller needs the true total match count (e.g. to show
        "found N matches" without silently truncating that count).
        """
        if not query:
            return []
        q = query.strip().lower()
        if not q:
            return []

        exact = self.return_by_name(query) or self.return_by_id(query)
        if exact:
            return [exact]

        all_returns = list(self.returns()) + list(self.non_xbrl_returns())
        seen: set[str] = set()

        def _dedup_add(rows: list[dict]) -> list[dict]:
            out = []
            for r in rows:
                key = r.get("Name", "") + "|" + r.get("Id", "")
                if key and key not in seen:
                    seen.add(key)
                    out.append(r)
            return out

        def _cap(rows: list[dict]) -> list[dict]:
            return rows if limit is None else rows[:limit]

        import re as _re

        def _compact(s: str) -> str:
            return _re.sub(r"[_\-\s/()]+", "", s.lower())

        q_compact = _compact(q)
        if q_compact:
            compact_exact = _dedup_add([
                r for r in all_returns
                if _compact(r.get("Name", "")) == q_compact or _compact(r.get("ReturnId", "") or "") == q_compact
            ])
            if compact_exact:
                return _cap(compact_exact)

        starts_with = _dedup_add([r for r in all_returns if r.get("Name", "").lower().startswith(q)])
        if starts_with:
            return _cap(starts_with)

        contains = _dedup_add([r for r in all_returns if q in r.get("Name", "").lower()])
        if contains:
            return _cap(contains)

        if q_compact:
            compact_contains = _dedup_add([r for r in all_returns if q_compact in _compact(r.get("Name", ""))])
            if compact_contains:
                return _cap(compact_contains)

        import difflib
        names = sorted({r.get("Name", "") for r in all_returns if r.get("Name")})
        fuzzy_n = limit if limit is not None else len(names)
        fuzzy_names = difflib.get_close_matches(query, names, n=fuzzy_n, cutoff=0.6)
        if not fuzzy_names:
            return []
        by_name_lower = {r.get("Name", "").lower(): r for r in all_returns if r.get("Name")}
        return _dedup_add([by_name_lower[n.lower()] for n in fuzzy_names if n.lower() in by_name_lower])
