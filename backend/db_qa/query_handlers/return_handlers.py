"""New-taxonomy handlers — PERIOD, XBRL_RETURNS, NON_XBRL_RETURNS,
DEPT_RETURN_MAPPING categories."""
from __future__ import annotations

import calendar
import re
from collections import Counter
from datetime import date, datetime, timedelta

from backend.db_qa.xml_store import XMLStore, get_attr
from backend.db_qa.query_handlers._return_resolution import resolve_named_return
from backend.db_qa.query_handlers.role_handlers import _UNDERSTAND_FAILURE_MSG

# Same date vocabulary as instance_generator.py's _DATE_FMT/_EXTRA_FMTS,
# plus a bare "Month YYYY" form (e.g. "June 2025") since date-range
# questions commonly name a month rather than a specific day, and
# space-separated "1 Jan 2026"/"01 January 2026" forms.
_DATE_FMTS = [
    "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y",
]
_MONTH_YEAR_FMTS = ["%B %Y", "%b %Y"]


def _parse_flexible_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_month_year(s: str) -> tuple[int, int] | None:
    """Return (year, month) for a bare "June 2025"/"Jun 2025" token."""
    s = (s or "").strip()
    for fmt in _MONTH_YEAR_FMTS:
        try:
            d = datetime.strptime(s, fmt)
            return d.year, d.month
        except ValueError:
            continue
    return None


def resolve_date_range(date_from: str | None, date_to: str | None, question: str = "") -> tuple[date, date] | None:
    """Resolve (date_from, date_to) entity strings into a concrete (start,
    end) date pair — handles specific dates, a bare month ("June 2025"
    covers the whole month), and, when neither entity was extracted,
    relative phrases in *question* ("next month" / "this month"). Returns
    None if nothing resolvable was found.
    """
    if date_from and date_to:
        start = _parse_flexible_date(date_from)
        end = _parse_flexible_date(date_to)
        if start and end:
            return (start, end) if start <= end else (end, start)

        # One or both sides may be a bare "Month YYYY" instead of an exact
        # date (e.g. "during January 2026 to December 2026") — resolve
        # each side independently: a bare month on the "from" side starts
        # at day 1, a bare month on the "to" side ends at that month's
        # last day. An already-resolved exact date on either side (from
        # the block above) is reused as-is rather than re-parsed.
        if start is None:
            my_from = _parse_month_year(date_from)
            if my_from:
                start = date(my_from[0], my_from[1], 1)
        if end is None:
            my_to = _parse_month_year(date_to)
            if my_to:
                last_day = calendar.monthrange(my_to[0], my_to[1])[1]
                end = date(my_to[0], my_to[1], last_day)
        if start and end:
            return (start, end) if start <= end else (end, start)

    q = (question or "").lower()
    today = date.today()
    if re.search(r"\bnext\s+month\b", q):
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)
    if re.search(r"\bthis\s+month\b", q):
        last_day = calendar.monthrange(today.year, today.month)[1]
        return date(today.year, today.month, 1), date(today.year, today.month, last_day)

    return None

# Some Return records leave both Frequency and RepFreq empty — so the
# "resolve frequency" chain (Frequency -> RepFreq) can come up empty.
# PeriodName is always present, so it's the last-resort fallback: same
# canonical PeriodName -> Frequency-code mapping as logs/period.xml
# (Daily->D, Weekly->W, ... Yearly->Y).
_PERIOD_NAME_TO_FREQUENCY: dict[str, str] = {
    "daily": "D",
    "weekly": "W",
    "fortnightly": "F",
    "monthly": "M",
    "quarterly": "Q",
    "half yearly": "H",
    "yearly": "Y",
    "half yearly(calendar year)": "C",
    "yearly(calendar year)": "B",
}


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _resolve_target_department(store: XMLStore, scope: dict, entities: dict) -> dict | None:
    """Resolve which department's data a query should be scoped to.

    "self" (any user): the caller's own department, resolved from their
    own XML_User.xml row — never influenced by entities, so a regular
    user can never widen scope by naming a different department in the
    question text.

    "department" (admin only — enforced upstream by access_control.
    scope_query, which raises PermissionError before a handler ever
    runs): a named department from entities["target_department"].

    "system_wide" is NOT handled here — callers that accept it must
    check scope["target_type"] == "system_wide" themselves and aggregate
    across every department, since there's no single dept dict to return
    for that case. See _dept_allowed_return_ids_system_wide().
    """
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return None
        dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
        return store.dept_by_id(dept_id) if dept_id else None
    target = entities.get("target_department", "")
    return store.resolve_dept(target) if target else None


# ── PERIOD ───────────────────────────────────────────────────────────────

def _all_period_returns(store: XMLStore) -> list[dict]:
    """XBRL + non-XBRL returns combined — PERIOD questions ("which returns
    share the same frequency", "any returns with no notification days")
    never distinguish XBRL vs non-XBRL, unlike XBRL_RETURNS-category
    questions, so both sets are always considered together here."""
    return [store.enrich_return(r) for r in store.returns()] + \
           [store.enrich_return(r) for r in store.non_xbrl_returns()]


def _resolve_period(store: XMLStore, token: str) -> dict | None:
    """Resolve *token* (a period name, EBR code, or numeric Period_Id) to
    its period dict — tried in this order: exact Period_Id, exact
    case-insensitive PeriodName, exact case-insensitive EBRFrequency,
    then a substring PeriodName match (declines if ambiguous across
    multiple periods, same "don't guess" rule as every other fuzzy
    resolver in this module)."""
    token = (token or "").strip()
    if not token:
        return None
    periods = store.periods()
    if token.isdigit():
        exact_id = next((p for p in periods if get_attr(p, "Period_Id", "Id", default="") == token), None)
        if exact_id:
            return exact_id
    tl = token.lower()
    exact_name = next((p for p in periods if p.get("PeriodName", "").lower() == tl), None)
    if exact_name:
        return exact_name
    exact_ebr = next((p for p in periods if (p.get("EBRFrequency") or "").lower() == tl), None)
    if exact_ebr:
        return exact_ebr
    # PERIOD_ALIASES' canonical forms are space-free ("HalfYearly",
    # "BiMonthly") but real PeriodName rows contain a space ("Half
    # Yearly") — normalize both sides (strip spaces/hyphens) before
    # giving up on an exact match.
    tl_norm = re.sub(r"[\s\-]+", "", tl)
    norm_name = next((p for p in periods if re.sub(r"[\s\-]+", "", p.get("PeriodName", "").lower()) == tl_norm), None)
    if norm_name:
        return norm_name
    substr = [p for p in periods if tl in p.get("PeriodName", "").lower()]
    return substr[0] if len(substr) == 1 else None


def handle_period_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    periods = list(store.periods())
    query_type = entities.get("query_type")

    if query_type == "shared_frequency":
        rets = _all_period_returns(store)
        by_period: dict[str, list[dict]] = {}
        for r in rets:
            pid = get_attr(r, "PeriodId", "Period_Id", default="")
            if pid:
                by_period.setdefault(pid, []).append(r)
        rows = []
        for pid, group in by_period.items():
            if len(group) < 2:
                continue
            period_name = store.period_name_by_id(pid)
            rows.append({
                "Frequency": period_name,
                "ReturnCount": len(group),
                "Returns": ", ".join(r.get("Name", "") for r in group),
            })
        rows.sort(key=lambda row: row["ReturnCount"], reverse=True)
        if not rows:
            return _result("period_list", "Returns Sharing a Frequency", [],
                           "No two returns currently share the same reporting frequency.", count=0)
        return _result("period_list", "Returns Sharing a Frequency", rows,
                       f"{len(rows)} frequency group(s) have more than one return assigned.", count=len(rows))

    if query_type == "most_returns":
        rets = _all_period_returns(store)
        counts = Counter(get_attr(r, "PeriodId", "Period_Id", default="") for r in rets if get_attr(r, "PeriodId", "Period_Id", default=""))
        if not counts:
            return _not_found("period_list", "Frequency With Most Returns", "No returns are assigned to any reporting frequency.")
        top_pid, top_count = counts.most_common(1)[0]
        period_name = store.period_name_by_id(top_pid)
        row = {"Frequency": period_name, "ReturnCount": top_count}
        return _result("period_list", "Frequency With Most Returns", [row],
                       f"'{period_name}' has the most returns scheduled under it, with {top_count} return(s).")

    return _result("period_list", "Reporting Periods", periods,
                   f"There are {len(periods)} reporting period(s) configured.", count=len(periods))


def handle_period_lookup(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = entities.get("query_type")

    if query_type == "personal_calendar":
        today = date.today()
        date_from = date(today.year, 1, 1).strftime("%d-%b-%Y")
        date_to = date(today.year, 12, 31).strftime("%d-%b-%Y")
        result = handle_reports_upcoming_in_range(
            scope, {**entities, "date_from": date_from, "date_to": date_to}, store)
        result["intent"] = "period_lookup"
        result["label"] = f"My Reporting Calendar {today.year}"
        return result

    if query_type == "no_notification":
        no_notif_ids = {
            get_attr(p, "Period_Id", "Id", default="")
            for p in store.periods()
            if not (p.get("AdvanceNotificationDays") or "").strip()
            or (p.get("AdvanceNotificationDays") or "").strip() == "0"
        }
        rets = [r for r in _all_period_returns(store)
                if get_attr(r, "PeriodId", "Period_Id", default="") in no_notif_ids]
        if not rets:
            return _result("period_lookup", "Returns With No Advance Notification", [],
                           "No, every return's reporting frequency has advance notification days configured.", count=0)
        rows = [{"ReturnName": r.get("Name", ""), "Frequency": r.get("PeriodName", "")} for r in rets]
        return _result("period_lookup", "Returns With No Advance Notification", rows,
                       f"Yes, {len(rows)} return(s) have no advance notification days configured.", count=len(rows))

    if query_type == "compare":
        name_a = entities.get("period_name", "")
        name_b = entities.get("period_b", "")
        period_a = _resolve_period(store, name_a)
        period_b = _resolve_period(store, name_b)
        if not period_a or not period_b:
            missing = name_a if not period_a else name_b
            return _not_found("period_lookup", "Frequency Comparison",
                              _UNDERSTAND_FAILURE_MSG if not (name_a or name_b)
                              else f"No period/frequency found matching '{missing}'.")
        rows = [
            {
                "Frequency": p.get("PeriodName"),
                "EBRCode": p.get("EBRFrequency") or "",
                "PeriodId": get_attr(p, "Period_Id", "Id", default=""),
                "AdvanceNotificationDays": p.get("AdvanceNotificationDays") or "",
            }
            for p in (period_a, period_b)
        ]
        summary = (
            f"'{period_a.get('PeriodName')}' (EBR: {period_a.get('EBRFrequency') or 'n/a'}, "
            f"{period_a.get('AdvanceNotificationDays') or '0'} advance notification day(s)) vs. "
            f"'{period_b.get('PeriodName')}' (EBR: {period_b.get('EBRFrequency') or 'n/a'}, "
            f"{period_b.get('AdvanceNotificationDays') or '0'} advance notification day(s))."
        )
        return _result("period_lookup", "Frequency Comparison", rows, summary)

    if query_type == "notification_gt":
        threshold = entities.get("threshold_days") or 0
        matches = [p for p in store.periods() if _safe_int(p.get("AdvanceNotificationDays")) > threshold]
        if not matches:
            return _result("period_lookup", "Periods Over Notification Threshold", [],
                           f"No periods have an advance notification period greater than {threshold} day(s).", count=0)
        return _result("period_lookup", "Periods Over Notification Threshold", matches,
                       f"{len(matches)} period(s) have an advance notification period greater than {threshold} day(s).",
                       count=len(matches))

    period_name = entities.get("period_name", "")
    period_id = entities.get("period_id", "")
    match = None
    if period_id:
        match = next((p for p in store.periods() if get_attr(p, "Period_Id", "Id", default="") == str(period_id)), None)
    elif period_name:
        match = _resolve_period(store, period_name)
    if not match:
        return _not_found("period_lookup", "Period Lookup",
                          _UNDERSTAND_FAILURE_MSG if not (period_name or period_id)
                          else f"No period found matching '{period_name or period_id}'.")

    field = entities.get("field")
    ebr = match.get("EBRFrequency") or "n/a"
    notif_days = match.get("AdvanceNotificationDays") or "0"
    pid = get_attr(match, "Period_Id", "Id", default="")
    if field == "id":
        summary = f"The period ID for '{match.get('PeriodName')}' is {pid}."
    elif field == "name":
        summary = f"Period ID {pid} is '{match.get('PeriodName')}'."
    elif field == "ebr_code":
        summary = f"The EBR frequency code for '{match.get('PeriodName')}' is '{ebr}'."
    elif field == "notification_days":
        summary = f"'{match.get('PeriodName')}' has {notif_days} advance notification day(s)."
    else:
        summary = (
            f"Period '{match.get('PeriodName')}' has id {pid}, EBR code '{ebr}', "
            f"and {notif_days} advance notification day(s)."
        )
    return _result("period_lookup", f"Period: {match.get('PeriodName')}", [match], summary)


def _safe_int(v) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return 0


def handle_returns_by_frequency(scope: dict, entities: dict, store: XMLStore) -> dict:
    period_name = entities.get("period_name", "")
    period = _resolve_period(store, period_name) if period_name else None
    if not period:
        return _not_found("returns_by_frequency", "Returns by Frequency",
                          _UNDERSTAND_FAILURE_MSG if not period_name
                          else f"No period found matching '{period_name}'.")
    period_id = get_attr(period, "Period_Id", "Id", default="")

    rets = [r for r in _all_period_returns(store) if get_attr(r, "PeriodId", "Period_Id", default="") == period_id]
    # Frequency and TYPE are independent filters and must compose: "XBRL
    # returns filed monthly" and "Non-XBRL returns filed monthly" are
    # different questions. _all_period_returns() deliberately combines both
    # sets (PERIOD_LIST/PERIOD_LOOKUP genuinely don't distinguish them), so
    # the narrowing belongs here rather than in that helper.
    xbrl_type = entities.get("xbrl_type")
    rets = _filter_by_xbrl_type(store, rets, xbrl_type)
    if scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        allowed = _dept_allowed_return_ids(store, dept)
        if allowed is not None:
            rets = [r for r in rets if r.get("Id") in allowed or r.get("ReturnId") in allowed]
    display_name = period.get("PeriodName", period_name)
    type_word = _TYPE_WORD.get(xbrl_type, "")
    label = f"{display_name} {type_word}Returns".replace("  ", " ") + (
        " (Mine)" if scope["target_type"] == "self" else "")
    return _result("returns_by_frequency", label, rets,
                   f"Found {len(rets)} {display_name} {type_word}return(s).".replace("  ", " "),
                   count=len(rets), xbrl_type=xbrl_type)


# ── XBRL_RETURNS ─────────────────────────────────────────────────────────

def handle_return_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    category = entities.get("category", "")
    # This intent's attribute filters (CIMS-enabled, RBI validation, table
    # linkbase, due period, category) are properties of ANY return, not just
    # XBRL ones, and its patterns match either type. Starting from
    # store.returns() alone answered "which non-XBRL returns are CIMS
    # enabled?" with the XBRL set, and answered every unqualified "which
    # returns ..." as XBRL-only. None = both, per _extract_xbrl_type.
    xbrl_type = entities.get("xbrl_type")
    returns = [store.enrich_return(r) for r in _returns_of_type(store, xbrl_type)]

    if scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        # Both access lists, then narrowed by type above — scoping to Forms
        # (XBRL) alone dropped every non-XBRL return the caller can access.
        allowed = _dept_allowed_return_ids(store, dept)
        if allowed is not None:
            returns = [r for r in returns if r.get("Id") in allowed or r.get("ReturnId") in allowed]

    if category:
        returns = [r for r in returns if category.lower() in (r.get("Name") or "").lower()
                   or category.lower() in (r.get("ReturnId") or "").lower()]

    if query_type == "next_three_dates":
        today = date.today()
        rows = []
        for r in returns:
            frequency, period_name = _resolve_return_frequency_code(store, r)
            due_days = (r.get("DueDays") or "").strip() or None
            occurrences = _occurrences_forward(frequency, due_days, today, count=3)
            rows.append({
                "ReturnName": r.get("Name", ""),
                "Frequency": period_name or frequency or "Unspecified",
                "UpcomingDueDates": ", ".join(o["period_end"] for o in occurrences) if occurrences else "N/A",
            })
        return _result("return_list", "Returns — Next 3 Upcoming Due Dates", rows,
                       f"Showing the next 3 upcoming due dates for {len(rows)} return(s).", count=len(rows))

    if query_type in ("active", "active_count"):
        returns = [r for r in returns if (r.get("Status") or "").lower() == "true"]
    elif query_type in ("inactive", "inactive_count"):
        returns = [r for r in returns if (r.get("Status") or "").lower() != "true"]
    elif query_type == "cims":
        returns = [r for r in returns if (r.get("IsCims") or "").lower() == "true"]
    elif query_type == "istbl":
        returns = [r for r in returns if (r.get("IsTBL") or "").lower() == "true"]
    elif query_type == "large_validator":
        returns = [r for r in returns if (r.get("IsLargeValidator") or "").lower() == "true"]
    elif query_type == "rbi":
        returns = [r for r in returns if (r.get("IsRBIValidation") or "").lower() == "true"]
    elif query_type == "formula_and_schema":
        returns = [r for r in returns if (r.get("IsFormulaValidation") or "").lower() == "true"
                   and (r.get("IsSchCalValidation") or "").lower() == "true"]
    elif query_type == "due_gt":
        threshold = entities.get("threshold_days") or 21
        returns = [r for r in returns if _safe_int(r.get("DueDays")) > threshold]
    elif query_type == "no_due_days":
        returns = [r for r in returns if not (r.get("DueDays") or "").strip()]

    # Labels must state the type actually answered — a "Non-XBRL" question
    # headed "XBRL Returns" reads as the wrong answer even when the rows are
    # right, and an unqualified one must not claim either type.
    type_word = _TYPE_WORD.get(xbrl_type, "")
    label = (f"My {type_word}Returns" if scope["target_type"] == "self"
             else f"{type_word}Returns").replace("  ", " ")
    active_count = sum(1 for r in returns if (r.get("Status") or "").lower() == "true")
    _FILTER_LABELS = {
        "due_gt": ("Returns With Long Due Period",
                   f"{{n}} return(s) have a due period of more than {entities.get('threshold_days') or 21} day(s)."),
        "cims": ("CIMS-Enabled Returns", "{n} return(s) are CIMS-enabled."),
        "no_due_days": ("Returns With No Due Days", "{n} return(s) have no due days configured."),
        "istbl": ("Table-Linkbase (IsTBL) Returns", "{n} return(s) use the table linkbase (IsTBL)."),
        "large_validator": ("Returns Using the Large Validator", "{n} return(s) use the large validator."),
        "rbi": ("Returns With RBI Validation", "{n} return(s) have RBI validation enabled."),
        "formula_and_schema": ("Returns With Formula + Schema-Calc Validation",
                                "{n} return(s) have both formula validation and schema-calculation validation enabled."),
    }
    if query_type in _FILTER_LABELS:
        filt_label, summary_tpl = _FILTER_LABELS[query_type]
        if type_word:
            filt_label = f"{type_word}{filt_label}"
        if category:
            filt_label = f"{filt_label} ({category.upper()})"
        summary = summary_tpl.format(n=len(returns))
        if type_word:
            summary = summary.replace("return(s)", f"{type_word}return(s)", 1)
        return _result("return_list", filt_label, returns, summary,
                       count=len(returns), xbrl_type=xbrl_type)
    if category and query_type in ("all", ""):
        return _result("return_list", f"{category.upper()} {type_word}Returns".replace("  ", " "), returns,
                       f"Found {len(returns)} {type_word}return(s) in the {category.upper()} category.".replace("  ", " "),
                       count=len(returns), xbrl_type=xbrl_type)
    return _result("return_list", label, returns,
                   f"There are {len(returns)} {type_word}returns ({active_count} active).".replace("  ", " "),
                   count=len(returns), active=active_count, xbrl_type=xbrl_type)


def handle_return_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    ret, early = resolve_named_return(store, scope, target, intent="return_profile", label="Return Profile",
                                      xbrl_type=entities.get("xbrl_type"))
    if early:
        return early
    return _result("return_profile", f"Return: {ret.get('Name')}", [store.enrich_return(ret)],
                   f"Details for return '{ret.get('Name')}'.")


_RETURN_FIELD_LABELS: dict[str, str] = {
    "return_id": "return ID",
    "frequency": "reporting frequency",
}


def _resolve_return_frequency_label(store: XMLStore, ret: dict) -> str:
    """The human-readable period/frequency label for *ret* (e.g.
    "Quarterly") — same PeriodName -> Frequency-code resolution order used
    by handle_next_reporting_date, but this only needs the display label,
    not the code itself."""
    period_id = get_attr(ret, "PeriodId", "Period_Id", default="")
    from backend.tools.instance_generator import get_period_info
    period_info = get_period_info(period_id) or {}
    period_name = (period_info.get("PeriodName") or "").strip()
    if period_name:
        return period_name
    frequency = (ret.get("RepFreq") or "").strip().upper()
    for name, code in _PERIOD_NAME_TO_FREQUENCY.items():
        if code == frequency:
            return name.title()
    return "Unspecified"


def handle_return_field(scope: dict, entities: dict, store: XMLStore) -> dict:
    """A single field of a named return — e.g. "what is the return id for
    CIMS_ROR" or "what is the reporting frequency of CIMS_ROR" — NOT the
    full profile (return_profile intercepts phrasings this doesn't own,
    e.g. "xsd path for"/"taxonomy version of"). Only the field the user
    actually asked about goes into records/summary, so the answer never
    leaks the return's other technical attributes."""
    field = entities.get("field", "")
    field_label = _RETURN_FIELD_LABELS.get(field, field or "field")
    target = entities.get("target_return", "")

    ret, early = resolve_named_return(store, scope, target, intent="return_field", label="Return Field",
                                      xbrl_type=entities.get("xbrl_type"))
    if early:
        return early

    ret_name = ret.get("Name", target)

    if field == "return_id":
        value = ret.get("ReturnId") or ret.get("Id", "") or "Not set"
        return _result("return_field", f"Return ID: {ret_name}", [{"ReturnName": ret_name, "ReturnId": value}],
                       f"The return ID for '{ret_name}' is {value}.")

    if field == "internal_form_id":
        value = ret.get("Id", "") or "Not set"
        return _result("return_field", f"Internal Form ID: {ret_name}", [{"ReturnName": ret_name, "InternalFormId": value}],
                       f"The internal form ID for '{ret_name}' is {value}.")

    if field == "frequency":
        value = _resolve_return_frequency_label(store, ret)
        return _result("return_field", f"Frequency: {ret_name}", [{"ReturnName": ret_name, "Frequency": value}],
                       f"'{ret_name}' is filed on a '{value}' basis.")

    if field == "due_days":
        value = (ret.get("DueDays") or "").strip()
        if not value:
            return _result("return_field", f"Due Days: {ret_name}", [{"ReturnName": ret_name, "DueDays": None}],
                           f"'{ret_name}' has no due-days value configured.")
        return _result("return_field", f"Due Days: {ret_name}", [{"ReturnName": ret_name, "DueDays": value}],
                       f"'{ret_name}' has {value} due day(s) for submission.")

    if field == "formats":
        # IsExcel is the only per-return format flag this system tracks —
        # every XBRL return always produces an XML instance document, and
        # IsExcel additionally marks whether a rendered Excel version is
        # also generated. There's no separate PDF/HTML flag on a Return
        # row, so this is a best-effort answer grounded in the one field
        # that actually exists, not a literal PDF/Excel/HTML breakdown.
        has_excel = (ret.get("IsExcel") or "").lower() == "true"
        formats = "XML instance and rendered Excel" if has_excel else "XML instance only"
        return _result("return_field", f"Report Formats: {ret_name}",
                       [{"ReturnName": ret_name, "Formats": formats}],
                       f"'{ret_name}' generates {formats.lower()} format(s).")

    return _not_found("return_field", "Return Field", f"Unrecognized return field {field!r} for '{ret_name}'.")


def handle_return_validation_config(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    detail_type = (entities.get("detail_type") or "").lower()

    if target:
        ret, early = resolve_named_return(store, scope, target, intent="return_validation_config", label="Validation Configuration")
        if early:
            return early
        row = store.enrich_return(ret)
        row["HasFormulaValidation"] = ret.get("IsFormulaValidation", "false")
        row["HasSchCalcValidation"] = ret.get("IsSchCalValidation", "false")
        row["HasRBIValidation"] = ret.get("IsRBIValidation", "false")
        return _result("return_validation_config", f"Validation Config: {ret.get('Name')}", [row],
                       f"Validation configuration for return '{ret.get('Name')}'.")

    results = []
    for r in store.returns():
        row = store.enrich_return(r)
        row["HasFormulaValidation"] = r.get("IsFormulaValidation") or "false"
        row["HasSchCalcValidation"] = r.get("IsSchCalValidation") or "false"
        row["HasLargeValidator"] = r.get("IsLargeValidator") or "false"
        row["HasRBIValidation"] = r.get("IsRBIValidation") or "false"
        row["IsCIMS"] = r.get("IsCims") or "false"
        results.append(row)

    _DETAIL_SUMMARY = {
        "formula": "{n} return(s) have formula validation enabled.",
        "schema": "{n} return(s) use schema-calculation validation.",
        "sch": "{n} return(s) use schema-calculation validation.",
        "formula_and_schema": "{n} return(s) have both formula validation and schema-calculation validation enabled.",
        "rbi": "{n} return(s) have RBI validation enabled.",
        "large": "{n} return(s) use the large validator.",
    }
    if detail_type == "formula":
        results = [r for r in results if r["HasFormulaValidation"].lower() == "true"]
        label = "Returns with Formula Validation"
    elif detail_type in ("schema", "sch"):
        results = [r for r in results if r["HasSchCalcValidation"].lower() == "true"]
        label = "Returns with Schema-Calculation Validation"
    elif detail_type == "formula_and_schema":
        results = [r for r in results if r["HasFormulaValidation"].lower() == "true"
                   and r["HasSchCalcValidation"].lower() == "true"]
        label = "Returns with Formula + Schema-Calculation Validation"
    elif detail_type == "rbi":
        results = [r for r in results if r["HasRBIValidation"].lower() == "true"]
        label = "Returns with RBI Validation"
    elif detail_type == "large":
        results = [r for r in results if r["HasLargeValidator"].lower() == "true"]
        label = "Returns Using Large Validator"
    else:
        label = "Returns with Validation Settings"

    summary = _DETAIL_SUMMARY.get(detail_type, "Found {n} return(s) with validation settings.").format(n=len(results))
    return _result("return_validation_config", label, results, summary, count=len(results))


def handle_returns_submittable_by_dept(scope: dict, entities: dict, store: XMLStore) -> dict:
    target_return = entities.get("target_return", "")
    if target_return:
        # "which departments can submit return X" — same as
        # departments_with_return_access: a cross-department audit
        # question, so enforce_department_auth=False (the caller's own
        # department not having this return is irrelevant to answering
        # which OTHER departments can submit it).
        ret, early = resolve_named_return(
            store, scope, target_return, intent="returns_submittable_by_dept", label="Departments That Can Submit",
            enforce_department_auth=False,
        )
        if early:
            return early
        ret_id, ret_code = ret.get("Id", ""), ret.get("ReturnId", "")
        # A non-XBRL return is listed in the department's NXForms attribute,
        # never in Forms — checking Forms alone returned "0 departments can
        # submit this" for every non-XBRL return in the data.
        matches = []
        for d in store.departments():
            allowed = _dept_allowed_return_ids(store, d) or set()
            if ret_id in allowed or ret_code in allowed:
                matches.append(d)
        return _result("returns_submittable_by_dept", f"Departments That Can Submit {ret.get('Name')}",
                       matches, f"{len(matches)} department(s) can submit '{ret.get('Name')}'.", count=len(matches))

    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_department', '')}'"
        return _not_found("returns_submittable_by_dept", "Submittable Returns", f"{who} department could not be found.")
    # Same both-lists reasoning, then narrowed to whichever type the question
    # named (None = both, per _extract_xbrl_type).
    xbrl_type = entities.get("xbrl_type")
    allowed = _dept_allowed_return_ids(store, dept) or set()
    rets = [store.enrich_return(r) for r in _returns_of_type(store, xbrl_type)
            if r.get("Id") in allowed or r.get("ReturnId") in allowed]
    type_word = _TYPE_WORD.get(xbrl_type, "")
    who_phrase = "You can" if scope["target_type"] == "self" else f"Department '{dept.get('Name')}' can"
    return _result("returns_submittable_by_dept", f"Submittable {type_word}Returns".replace("  ", " "),
                   rets, f"{who_phrase} submit {len(rets)} {type_word}return(s).".replace("  ", " "),
                   count=len(rets), xbrl_type=xbrl_type)


def _resolve_return_frequency_code(store: XMLStore, ret: dict) -> tuple[str, str]:
    """Return (frequency_code, period_name) for *ret*, using the same
    resolution order as handle_next_reporting_date: PeriodMaster's own
    Frequency code (authoritative) -> PeriodName mapped through the
    canonical table -> the return's own RepFreq as a last resort. RepFreq
    is checked LAST, not second, because it isn't guaranteed to use the
    same code alphabet next_reporting_date() understands (RepFreq="A" has
    been seen on a return whose actual period is Yearly/"Y" — "A" isn't
    one of next_reporting_date()'s recognised codes, so trusting RepFreq
    over the unambiguous PeriodName->code mapping silently produced "no
    fixed period-end" for a return that plainly has one). Shared by
    handle_next_reporting_date and handle_reports_upcoming_in_range so the
    two can never disagree.
    """
    from backend.tools.instance_generator import get_period_info

    period_id = get_attr(ret, "PeriodId", "Period_Id", default="")
    period_info = get_period_info(period_id) or {}
    period_name = (period_info.get("PeriodName") or "").strip()

    frequency = (period_info.get("Frequency") or "").strip().upper()
    if not frequency:
        frequency = _PERIOD_NAME_TO_FREQUENCY.get(period_name.lower(), "")
    if not frequency:
        frequency = (ret.get("RepFreq") or "").strip().upper()
    return frequency, period_name


def handle_next_reporting_date(scope: dict, entities: dict, store: XMLStore) -> dict:
    """Next period-end / due date for a named return, e.g. 'what is the
    next reporting date for the CIMS RoR return'. Frequency comes from the
    return's PeriodId, resolved against period.xml via
    instance_generator.get_period_info() — the same source used to
    validate reporting dates during instance generation, so the two paths
    can never disagree on what a period's frequency means."""
    from backend.tools.instance_generator import next_reporting_date

    target = (entities.get("target_return") or "").strip()
    ret, early = resolve_named_return(
        store, scope, target, intent="next_reporting_date", label="Next Reporting Date",
        no_target_message=(
            "Which return would you like the next reporting date for? "
            "Please name the return (e.g. \"what is the next reporting date for DPSS09\")."
        ),
        xbrl_type=entities.get("xbrl_type"),
    )
    if early:
        return early

    frequency, period_name = _resolve_return_frequency_code(store, ret)
    due_days = (ret.get("DueDays") or "").strip() or None
    ret_name = ret.get("Name", target)

    if entities.get("query_type") == "calendar":
        today = date.today()
        year_end = date(today.year, 12, 31)
        occurrences = _occurrences_forward(frequency, due_days, today, end=year_end)
        if not occurrences:
            return _result(
                "next_reporting_date", f"Reporting Calendar: {ret_name}",
                [{"ReturnName": ret_name, "Frequency": period_name or frequency or "Unspecified"}],
                f"'{ret_name}' is filed on a '{period_name or frequency or 'unspecified'}' "
                "basis, which has no fixed period-end date — there's no calendar of dates to list.",
            )
        rows = [{"ReturnName": ret_name, "PeriodEnd": o["period_end"], "DueDate": o.get("due_date")}
                for o in occurrences]
        return _result(
            "next_reporting_date", f"Reporting Calendar: {ret_name}", rows,
            f"'{ret_name}' has {len(rows)} reporting period(s) ending in {today.year}: "
            + ", ".join(o["period_end"] for o in occurrences) + ".",
            count=len(rows),
        )

    result = next_reporting_date(frequency, due_days)

    if result.get("period_end") is None:
        # records holds only the fields relevant to THIS question (return
        # name + period label) — never the raw enriched XML row, which
        # would otherwise dump every technical attribute (XSDPath,
        # namespaces, validation flags, ...) via the generic table
        # renderer for a question that only asked about a reporting date.
        return _result(
            "next_reporting_date", f"Next Reporting Date: {ret_name}",
            [{"ReturnName": ret_name, "Frequency": period_name or frequency or "Unspecified"}],
            f"'{ret_name}' is filed on a '{period_name or frequency or 'unspecified'}' "
            "basis, which has no fixed period-end date (e.g. daily or as-and-when returns are due continuously).",
            frequency=frequency,
        )

    row = {
        "ReturnName": ret_name,
        "Frequency": period_name or frequency,
        "NextPeriodEnd": result["period_end"],
        "DueDate": result["due_date"],
    }
    if result["due_date"]:
        summary = (
            f"The next reporting period for '{ret_name}' ends on {result['period_end']}, "
            f"and the submission is due by {result['due_date']}."
        )
    else:
        summary = f"The next reporting period for '{ret_name}' ends on {result['period_end']}."
    return _result("next_reporting_date", f"Next Reporting Date: {ret_name}", [row], summary,
                   period_end=result["period_end"], due_date=result["due_date"])


# Type word for labels/summaries. None -> "" so an unqualified question
# reads "Found 12 Monthly return(s)." rather than claiming a type the user
# never asked about.
_TYPE_WORD: dict[str | None, str] = {"xbrl": "XBRL ", "non_xbrl": "Non-XBRL ", None: ""}


def _returns_of_type(store: XMLStore, xbrl_type: str | None) -> list[dict]:
    """The source return rows for *xbrl_type*, with None meaning BOTH sets.

    Matches _extract_xbrl_type's documented contract ("None if the question
    doesn't specify -- handlers treat None as both"). Handlers that start
    from store.returns() alone silently answer every unqualified question
    with XBRL-only data.
    """
    if xbrl_type == "xbrl":
        return list(store.returns())
    if xbrl_type == "non_xbrl":
        return list(store.non_xbrl_returns())
    return list(store.returns()) + list(store.non_xbrl_returns())


def _filter_by_xbrl_type(store: XMLStore, returns: list[dict], xbrl_type: str | None) -> list[dict]:
    # Matches on Id, not ReturnId: Id is disjoint across the two sets, while
    # ReturnId collides for 2 rows in the real data -- keying on it would
    # leak a return of the wrong type into a type-filtered answer.
    if xbrl_type == "xbrl":
        xbrl_ids = {r.get("Id", "") for r in store.returns()}
        return [r for r in returns if r.get("Id", "") in xbrl_ids]
    if xbrl_type == "non_xbrl":
        nx_ids = {r.get("Id", "") for r in store.non_xbrl_returns()}
        return [r for r in returns if r.get("Id", "") in nx_ids]
    return returns


def _dept_allowed_return_ids(store: XMLStore, dept: dict | None) -> set[str] | None:
    """Return the set of Id/ReturnId values *dept* can access (both Forms
    and NXForms combined), or None if dept is unknown (caller should then
    skip department filtering rather than incorrectly return zero results)."""
    if not dept:
        return None
    form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
    nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
    return form_ids | nx_ids


def _all_return_ids_system_wide(store: XMLStore) -> set[str]:
    """Return every return ID accessible by ANY department combined —
    used only for target_type == "system_wide" (admin-only, enforced by
    access_control.scope_query before a handler runs), where the caller
    explicitly asked across all departments rather than one."""
    ids: set[str] = set()
    for dept in store.departments():
        ids |= _dept_allowed_return_ids(store, dept) or set()
    return ids


def handle_reports_filed_in_range(scope: dict, entities: dict, store: XMLStore) -> dict:
    """Returns actually SUBMITTED (an InstanceLog row exists) with a filing
    timestamp (DTC) between two dates — e.g. 'show me all XBRL reports
    filed between 01-Jan-2026 and 31-Mar-2026'. 'Filed between' is read as
    the actual submission timestamp falling in the window, not the
    ReportingDate (the period the submission is FOR) — those are
    different questions.

    Scope: target_type "self" (any user) is restricted to the caller's own
    department. "department" (a named other department) and "system_wide"
    (across every department) are admin-only — access_control.scope_query
    already raises PermissionError for a non-admin caller before this
    handler ever runs, so reaching either branch here means the caller is
    confirmed admin.
    """
    date_from = entities.get("date_from")
    date_to = entities.get("date_to")
    resolved = resolve_date_range(date_from, date_to)
    if not resolved:
        return _not_found(
            "reports_filed_in_range", "Reports Filed",
            "Please specify a date range, e.g. \"show me all XBRL reports filed between 01-Jan-2026 and 31-Mar-2026\".",
        )
    start, end = resolved

    target_type = scope.get("target_type", "self")
    scope_phrase = "by your department"
    if target_type == "system_wide":
        allowed_ids = _all_return_ids_system_wide(store)
        scope_phrase = "across all departments"
    else:
        dept = _resolve_target_department(store, scope, entities)
        if not dept:
            return _not_found(
                "reports_filed_in_range", "Reports Filed",
                "Your department could not be found, so filed returns can't be determined."
                if target_type == "self" else
                "That department could not be found.",
            )
        allowed_ids = _dept_allowed_return_ids(store, dept) or set()
        if target_type == "department":
            scope_phrase = f"by department '{dept.get('Name', '')}'"

    xbrl_type = entities.get("xbrl_type")
    all_returns = list(store.returns()) + list(store.non_xbrl_returns())
    all_returns = _filter_by_xbrl_type(store, all_returns, xbrl_type)
    return_by_id = {r.get("Id", ""): r for r in all_returns if r.get("Id")}

    matches = []
    for log in store.instance_log():
        form_id = log.get("FormId", "")
        if form_id not in return_by_id:
            continue
        if form_id not in allowed_ids:
            continue
        filed_on = _parse_flexible_date((log.get("DTC") or "").split(" ")[0])
        if not filed_on or not (start <= filed_on <= end):
            continue
        enriched = store.enrich_instance_log_entry(log)
        enriched["ReturnName"] = return_by_id[form_id].get("Name", "")
        matches.append(enriched)

    matches.sort(key=lambda l: l.get("DTC", ""), reverse=True)
    type_phrase = {"xbrl": "XBRL ", "non_xbrl": "non-XBRL "}.get(xbrl_type, "")
    label = f"{type_phrase}Reports Filed {start.strftime('%d-%b-%Y')} to {end.strftime('%d-%b-%Y')}"
    return _result(
        "reports_filed_in_range", label, matches,
        f"Found {len(matches)} {type_phrase}report(s) filed {scope_phrase} between "
        f"{start.strftime('%d-%b-%Y')} and {end.strftime('%d-%b-%Y')}.",
        count=len(matches),
    )


def _occurrences_forward(frequency: str, due_days: str | None, start: date,
                          *, count: int | None = None, end: date | None = None) -> list[dict]:
    """Successive next_reporting_date() occurrences starting after
    *start*, stopping once *count* occurrences are collected or the next
    one's period_end would exceed *end* — used for both "reporting
    calendar for return X this year" (bounded by end, uncapped count) and
    "next N due dates" (capped count, uncapped end). Frequencies with no
    fixed period-end (daily, as-and-when) return next_reporting_date's own
    single {"period_end": None, ...} result and stop immediately, same as
    every other caller of next_reporting_date."""
    from backend.tools.instance_generator import next_reporting_date

    out: list[dict] = []
    cursor = start
    for _ in range(60):
        if count is not None and len(out) >= count:
            break
        result = next_reporting_date(frequency, due_days, after=cursor)
        period_end = result.get("period_end")
        if not period_end:
            break
        pe_date = _parse_flexible_date(period_end)
        if not pe_date:
            break
        if end is not None and pe_date > end:
            break
        out.append(result)
        cursor = pe_date
    return out


def _most_recently_completed_occurrence(frequency: str, due_days: str | None, before: date) -> dict | None:
    """The LAST occurrence of *frequency* whose period_end falls on or
    before *before* — i.e. the most recently completed reporting period,
    as opposed to next_reporting_date()'s own "next one AFTER before"
    default. Walks forward from ~800 days back (comfortably more than one
    full cycle of even a yearly frequency) one occurrence at a time,
    keeping the last one that hasn't exceeded *before* yet. Capped at 40
    iterations as a safety backstop — no real frequency in this system
    needs anywhere near that many steps to cover ~2+ years."""
    from backend.tools.instance_generator import next_reporting_date

    cursor = before - timedelta(days=800)
    last = None
    for _ in range(40):
        result = next_reporting_date(frequency, due_days, after=cursor)
        period_end = result.get("period_end")
        if not period_end:
            return last
        pe_date = _parse_flexible_date(period_end)
        if not pe_date or pe_date > before:
            break
        last = result
        cursor = pe_date
    return last


def _find_overdue_returns(store: XMLStore, all_returns: list[dict], scope_phrase: str) -> dict:
    """Which of *all_returns* have a most-recently-completed reporting
    period whose due date has already passed with no matching InstanceLog
    submission on record — "are any of my returns overdue?" /
    "which returns are overdue for submission across all departments?"."""
    today = date.today()
    overdue = []
    for ret in all_returns:
        frequency, period_name = _resolve_return_frequency_code(store, ret)
        due_days = (ret.get("DueDays") or "").strip() or None
        occ = _most_recently_completed_occurrence(frequency, due_days, today)
        if not occ or not occ.get("period_end"):
            continue
        due_date_str = occ.get("due_date") or occ.get("period_end")
        due_date_obj = _parse_flexible_date(due_date_str)
        if not due_date_obj or due_date_obj >= today:
            continue
        form_id = ret.get("ReturnId") or ret.get("Id", "")
        period_end = occ["period_end"]
        filed = any(
            log.get("FormId") == form_id and log.get("ReportingDate") == period_end
            for log in store.instance_log()
        )
        if not filed:
            overdue.append({
                "ReturnName": ret.get("Name", ""),
                "Frequency": period_name or frequency,
                "PeriodEnd": period_end,
                "DueDate": due_date_str,
            })
    overdue.sort(key=lambda r: r["DueDate"])
    if not overdue:
        return _result("reports_upcoming_in_range", "Overdue Returns", [],
                       f"No returns are overdue for {scope_phrase}.", count=0)
    return _result("reports_upcoming_in_range", "Overdue Returns", overdue,
                   f"{len(overdue)} return(s) are overdue for {scope_phrase}.", count=len(overdue))


def _find_next_due_return(store: XMLStore, all_returns: list[dict], scope_phrase: str,
                           type_phrase: str) -> dict:
    """The single soonest UPCOMING due date across *all_returns* — "what is
    my next non-XBRL return due?".

    Mirror image of _find_overdue_returns: same per-return frequency/due-
    days computation, but taking the earliest occurrence still ahead of
    today instead of the last one already past. Returns the winner plus the
    next few runners-up, since "what's next" is nearly always followed by
    "and after that" — and ties (two returns sharing a due date) would
    otherwise silently drop one.
    """
    from backend.tools.instance_generator import next_reporting_date

    today = date.today()
    upcoming = []
    for ret in all_returns:
        frequency, period_name = _resolve_return_frequency_code(store, ret)
        due_days = (ret.get("DueDays") or "").strip() or None
        result = next_reporting_date(frequency, due_days, after=today)
        period_end = result.get("period_end")
        if not period_end:
            # Daily/as-and-when frequencies have no fixed period end, so
            # there is no discrete "next due date" to rank them by.
            continue
        due_date_obj = _parse_flexible_date(result.get("due_date") or period_end)
        if not due_date_obj or due_date_obj < today:
            continue
        upcoming.append({
            "ReturnName": ret.get("Name", ""),
            "Frequency": period_name or frequency,
            "NextPeriodEnd": period_end,
            "DueDate": result.get("due_date") or period_end,
            "_sort": due_date_obj,
        })

    if not upcoming:
        return _result("reports_upcoming_in_range", f"Next {type_phrase}Return Due".strip(), [],
                       f"No {type_phrase}return with a scheduled due date was found for {scope_phrase}.",
                       count=0)

    upcoming.sort(key=lambda r: r["_sort"])
    soonest = upcoming[0]["_sort"]
    rows = [r for r in upcoming if r["_sort"] == soonest] + \
           [r for r in upcoming if r["_sort"] != soonest][:4]
    for r in rows:
        r.pop("_sort", None)
    tied = [r for r in rows if r.get("DueDate") == rows[0].get("DueDate")]
    if len(tied) > 1:
        summary = (f"Your next {type_phrase}returns are due on {rows[0]['DueDate']}: "
                   + ", ".join(f"'{r['ReturnName']}'" for r in tied) + ".")
    else:
        summary = (f"Your next {type_phrase}return is '{rows[0]['ReturnName']}' "
                   f"({rows[0]['Frequency']}), due on {rows[0]['DueDate']} "
                   f"for the period ending {rows[0]['NextPeriodEnd']}.")
    return _result("reports_upcoming_in_range", f"Next {type_phrase}Return Due".strip(), rows,
                   summary, count=len(rows), next_due_date=rows[0].get("DueDate"))


def handle_reports_upcoming_in_range(scope: dict, entities: dict, store: XMLStore) -> dict:
    """Returns whose computed NEXT reporting/due date falls between two
    dates — e.g. 'what XBRL reports are coming up between 01-Jul-2026 and
    31-Jul-2026'. Computes one candidate next-due-date per return (today
    forward) using the same logic as handle_next_reporting_date, and lists
    the ones landing inside the window — this covers 'next month'/'this
    month'/a short explicit window; it does not enumerate multiple future
    occurrences of a return across a longer span.

    Scope: target_type "self" (any user) is restricted to the caller's own
    department. "department" (a named other department) and "system_wide"
    (across every department) are admin-only — access_control.scope_query
    already raises PermissionError for a non-admin caller before this
    handler ever runs, so reaching either branch here means the caller is
    confirmed admin.
    """
    from backend.tools.instance_generator import next_reporting_date

    target_type = scope.get("target_type", "self")
    scope_phrase = "your department"
    if target_type == "system_wide":
        allowed_ids = _all_return_ids_system_wide(store)
        scope_phrase = "all departments"
    else:
        dept = _resolve_target_department(store, scope, entities)
        if not dept:
            return _not_found(
                "reports_upcoming_in_range", "Upcoming Reports",
                "Your department could not be found, so upcoming returns can't be determined."
                if target_type == "self" else
                "That department could not be found.",
            )
        allowed_ids = _dept_allowed_return_ids(store, dept) or set()
        if target_type == "department":
            scope_phrase = f"department '{dept.get('Name', '')}'"

    xbrl_type = entities.get("xbrl_type")
    all_returns = list(store.returns()) + list(store.non_xbrl_returns())
    all_returns = _filter_by_xbrl_type(store, all_returns, xbrl_type)
    all_returns = [r for r in all_returns if r.get("Id", "") in allowed_ids or r.get("ReturnId", "") in allowed_ids]

    if entities.get("query_type") == "overdue":
        return _find_overdue_returns(store, all_returns, scope_phrase)
    if entities.get("query_type") == "next_due":
        return _find_next_due_return(store, all_returns, scope_phrase,
                                     {"xbrl": "XBRL ", "non_xbrl": "non-XBRL "}.get(xbrl_type, ""))

    date_from = entities.get("date_from")
    date_to = entities.get("date_to")
    resolved = resolve_date_range(date_from, date_to)
    if not resolved:
        return _not_found(
            "reports_upcoming_in_range", "Upcoming Reports",
            "Please specify a date range, e.g. \"what XBRL reports are coming up between 01-Jul-2026 and 31-Jul-2026\", "
            "or \"what non-XBRL returns are upcoming next month\".",
        )
    start, end = resolved

    matches = []
    for ret in all_returns:
        frequency, period_name = _resolve_return_frequency_code(store, ret)
        due_days = (ret.get("DueDays") or "").strip() or None
        result = next_reporting_date(frequency, due_days, after=start - __import__("datetime").timedelta(days=1))
        period_end = result.get("period_end")
        if not period_end:
            continue
        period_end_date = _parse_flexible_date(period_end)
        if not period_end_date or not (start <= period_end_date <= end):
            continue
        matches.append({
            "ReturnName": ret.get("Name", ""),
            "Frequency": period_name or frequency,
            "NextPeriodEnd": period_end,
            "DueDate": result.get("due_date"),
        })

    matches.sort(key=lambda m: m.get("NextPeriodEnd", ""))
    type_phrase = {"xbrl": "XBRL ", "non_xbrl": "non-XBRL "}.get(xbrl_type, "")
    label = f"{type_phrase}Reports Upcoming {start.strftime('%d-%b-%Y')} to {end.strftime('%d-%b-%Y')}"
    return _result(
        "reports_upcoming_in_range", label, matches,
        f"Found {len(matches)} {type_phrase}return(s) due for {scope_phrase} between "
        f"{start.strftime('%d-%b-%Y')} and {end.strftime('%d-%b-%Y')}.",
        count=len(matches),
    )


# Fixed (day, month) period-end pairs per frequency code, same terminal
# dates instance_generator.next_reporting_date()/validate_reporting_date()
# use — duplicated here (rather than importing instance_generator's
# underscore-prefixed module-private sets) since this only needs to answer
# "does this frequency end in month M", not compute an actual next date.
_Q_END_MONTHS: dict[str, set[int]] = {
    "Q": {3, 6, 9, 12},
    "H": {3, 9},
    "C": {6, 12},
    "Y": {3},
    "B": {12},
}


def _period_end_day(frequency: str, year: int, month: int) -> int | None:
    """The period-end day-of-month for *frequency* in (year, month), or
    None if *frequency* has no period-end falling in that month at all
    (e.g. a Quarterly return has no period-end in April)."""
    freq = (frequency or "").strip().upper()
    if freq in _Q_END_MONTHS:
        return calendar.monthrange(year, month)[1] if month in _Q_END_MONTHS[freq] else None
    if freq == "M":
        return calendar.monthrange(year, month)[1]
    if freq == "F":
        # Fortnightly ends both mid-month (15th) and month-end — for a
        # monthly roll-up, the month-end occurrence stands in for the
        # period; the 15th's own filing is a separate InstanceLog entry
        # this simplified monthly view doesn't split out.
        return calendar.monthrange(year, month)[1]
    if freq == "W":
        # Weekly (Friday-ending) has no single "period-end day of the
        # month" — every week in the month is its own period. Not
        # representable in a one-row-per-return monthly view; excluded
        # from monthly status entirely (same as D/G/HM below).
        return None
    return None  # D, G (as-and-when), HM, and unrecognised: no fixed period-end


def handle_monthly_filing_status(scope: dict, entities: dict, store: XMLStore) -> dict:
    """Per-return filed/not-filed roll-up for a single calendar month, e.g.
    "what's my XBRL filing status for June 2025?" or "what dates are
    non-XBRL reports expected in June 2025?".

    Only returns whose reporting frequency has a period-end date landing in
    the target month are considered "due" that month (a Quarterly return is
    not due every month, only quarter-end months) — this is a narrower,
    single-month view of the same frequency/period-end resolution
    handle_next_reporting_date and handle_reports_upcoming_in_range use, not
    a re-derivation of it. "Filed" means an InstanceLog entry exists whose
    ReportingDate equals that period-end (the period the submission is FOR,
    not when it was actually submitted — same distinction documented on
    handle_reports_filed_in_range).

    Scope: target_type "self" is restricted to the caller's own department;
    "department" (named other) and "system_wide" (all departments) are
    admin-only, already enforced by access_control.scope_query before this
    handler runs.
    """
    month_year = entities.get("month_year")
    if not month_year:
        return _not_found(
            "monthly_filing_status", "Filing Status",
            "Please specify a month, e.g. \"what's my XBRL filing status for June 2025?\" "
            "or \"non-XBRL status for this month\".",
        )
    my = _parse_month_year(month_year)
    if not my:
        return _not_found(
            "monthly_filing_status", "Filing Status",
            f"Could not understand the month {month_year!r}.",
        )
    year, month = my
    month_label = date(year, month, 1).strftime("%B %Y")

    target_type = scope.get("target_type", "self")
    scope_phrase = "your department"
    if target_type == "system_wide":
        allowed_ids = _all_return_ids_system_wide(store)
        scope_phrase = "all departments"
    else:
        dept = _resolve_target_department(store, scope, entities)
        if not dept:
            return _not_found(
                "monthly_filing_status", "Filing Status",
                "Your department could not be found, so filing status can't be determined."
                if target_type == "self" else
                "That department could not be found.",
            )
        allowed_ids = _dept_allowed_return_ids(store, dept) or set()
        if target_type == "department":
            scope_phrase = f"department '{dept.get('Name', '')}'"

    xbrl_type = entities.get("xbrl_type")
    all_returns = list(store.returns()) + list(store.non_xbrl_returns())
    all_returns = _filter_by_xbrl_type(store, all_returns, xbrl_type)
    all_returns = [r for r in all_returns if r.get("Id", "") in allowed_ids or r.get("ReturnId", "") in allowed_ids]

    logs_by_form: dict[str, list[dict]] = {}
    for log in store.instance_log():
        logs_by_form.setdefault(log.get("FormId", ""), []).append(log)

    rows = []
    for ret in all_returns:
        frequency, period_name = _resolve_return_frequency_code(store, ret)
        end_day = _period_end_day(frequency, year, month)
        if end_day is None:
            continue
        period_end = date(year, month, end_day)
        period_end_str = period_end.strftime("%d-%b-%Y")

        form_id = ret.get("Id", "") or ret.get("ReturnId", "")
        filed_entry = next(
            (l for l in logs_by_form.get(form_id, [])
             if _parse_flexible_date((l.get("ReportingDate") or "").split(" ")[0]) == period_end),
            None,
        )
        rows.append({
            "ReturnName": ret.get("Name", ""),
            "Frequency": period_name or frequency,
            "ExpectedDate": period_end_str,
            "Filed": bool(filed_entry),
            "FiledOn": (filed_entry.get("DTC") or "").split(" ")[0] if filed_entry else None,
        })

    rows.sort(key=lambda r: (r["Filed"], r["ReturnName"]))
    filed_count = sum(1 for r in rows if r["Filed"])
    type_phrase = {"xbrl": "XBRL ", "non_xbrl": "non-XBRL "}.get(xbrl_type, "")
    label = f"{type_phrase}Filing Status — {month_label}"
    if not rows:
        return _result(
            "monthly_filing_status", label, [],
            f"No {type_phrase}return(s) due for {scope_phrase} in {month_label}.",
            count=0,
        )
    return _result(
        "monthly_filing_status", label, rows,
        f"{filed_count} of {len(rows)} {type_phrase}return(s) due for {scope_phrase} "
        f"in {month_label} have been filed.",
        count=len(rows), filed=filed_count,
    )


# ── NON_XBRL_RETURNS ─────────────────────────────────────────────────────

def handle_nonxbrl_return_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    target_department = entities.get("target_department", "")
    returns = list(store.non_xbrl_returns())

    if target_department:
        dept = store.dept_by_name(target_department)
        if not dept:
            return _not_found("nonxbrl_return_list", "Non-XBRL Returns", f"Department '{target_department}' not found.")
        nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
        returns = [r for r in returns if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]
    elif scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        if dept:
            nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
            returns = [r for r in returns if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]

    if query_type == "no_due_days":
        returns = [r for r in returns if not (r.get("DueDays") or "").strip()]
        return _result("nonxbrl_return_list", "Non-XBRL Returns With No Due Days", returns,
                       f"{len(returns)} non-XBRL return(s) have no due days configured.", count=len(returns))
    if query_type == "has_folder":
        returns = [r for r in returns if (r.get("HasFolder") or "").lower() == "true"]
        return _result("nonxbrl_return_list", "Non-XBRL Returns With a Folder Structure", returns,
                       f"{len(returns)} non-XBRL return(s) have a folder structure.", count=len(returns))

    # The self-scoped list is already filtered to the caller's department
    # NXForms above, so it must SAY so — "there are N non-XBRL returns"
    # read as a system-wide total while actually reporting a much smaller
    # department-scoped number, with nothing in the answer to tell the two
    # apart.
    if scope["target_type"] == "self":
        return _result("nonxbrl_return_list", "My Non-XBRL Returns", returns,
                       f"You have access to {len(returns)} non-XBRL return(s)." if returns
                       else "You don't currently have access to any non-XBRL returns.",
                       count=len(returns))
    if target_department:
        return _result("nonxbrl_return_list", f"Non-XBRL Returns of {target_department}", returns,
                       f"Department '{target_department}' has access to {len(returns)} non-XBRL return(s).",
                       count=len(returns))
    return _result("nonxbrl_return_list", "Non-XBRL Returns", returns,
                   f"There are {len(returns)} non-XBRL returns.", count=len(returns))


def handle_nonxbrl_return_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    # enforce_department_auth=False: this intent's own fields (frequency,
    # due days, CIMS flag, job processing id, report format) describe the
    # RETURN's static definition, not department-specific access — the
    # same "reference data" category access_control.py's own comment
    # already carves out for target_type="return" queries. Without this,
    # asking about a return outside the caller's own department's NXForms
    # list (the admin_only "report generation status"/"reporting
    # schedule"/"report formats" phrasings never name the caller's own
    # department at all) wrongly failed to resolve before ever reaching
    # this handler's own not-a-non-XBRL-return check below.
    ret, early = resolve_named_return(
        store, scope, target, intent="nonxbrl_return_profile", label="Non-XBRL Return Profile",
        no_target_message="Please specify a non-XBRL return name.",
        enforce_department_auth=False,
        # Type enforced at the DATA layer, not checked after the fact: this
        # handler only ever describes non-XBRL returns, so an XBRL row must
        # never be a candidate in the first place. Resolving across both
        # sets and rejecting afterwards meant a partial/fuzzy name that
        # ranked an XBRL return higher failed with "that's an XBRL return"
        # even when a perfectly good non-XBRL match existed.
        xbrl_type="non_xbrl",
    )
    if early:
        return early

    period_name = store.period_name_by_id(get_attr(ret, "PeriodId", "Period_Id", default=""))
    due_days = (ret.get("DueDays") or "").strip() or "not configured"
    is_cims = (ret.get("IsCims") or "").lower() == "true"
    row = {
        "ReturnName": ret.get("Name"),
        "ReturnId": ret.get("ReturnId") or ret.get("Id", ""),
        "JobProcessingId": ret.get("JobProcessingId", ""),
        "Frequency": period_name,
        "DueDays": ret.get("DueDays"),
        "IsCIMS": is_cims,
        "HasFolder": (ret.get("HasFolder") or "").lower() == "true",
        "ReportFormat": "Excel",
    }
    return _result(
        "nonxbrl_return_profile", f"Non-XBRL Return: {ret.get('Name')}", [row],
        f"'{ret.get('Name')}' is filed on a '{period_name}' basis with {due_days} due day(s); "
        f"{'is' if is_cims else 'is not'} CIMS-enabled; uses the Excel report format.",
    )


# ── DEPT_RETURN_MAPPING ──────────────────────────────────────────────────

def handle_dept_return_access_matrix(scope: dict, entities: dict, store: XMLStore) -> dict:
    depts = store.departments()
    access_counter: Counter = Counter()
    for d in depts:
        form_ids = {f.strip() for f in d.get("Forms", "").split("|") if f.strip()}
        for rid in form_ids:
            access_counter[rid] += 1

    return_index = {r.get("Id", ""): r for r in store.returns()}
    rows = []
    for rid, count in access_counter.most_common():
        ret = return_index.get(rid)
        rows.append({"ReturnId": rid, "ReturnName": ret.get("Name", "") if ret else "", "DepartmentCount": count})

    dept_counts = []
    for d in depts:
        form_ids = {f.strip() for f in d.get("Forms", "").split("|") if f.strip()}
        dept_counts.append({"DeptName": d.get("Name", ""), "ReturnCount": len(form_ids)})
    dept_counts.sort(key=lambda x: x["ReturnCount"], reverse=True)

    query_type = entities.get("query_type")

    if query_type == "all_departments":
        # "which returns are accessible by ALL departments" — a genuinely
        # different question from the ranking dump: only returns whose
        # DepartmentCount equals the total department count qualify, which
        # may be none at all (that's a valid, informative answer, not an
        # error).
        universal = [r for r in rows if r["DepartmentCount"] == len(depts)]
        return _result("dept_return_access_matrix", "Returns Accessible By All Departments",
                       universal,
                       f"{len(universal)} return(s) are accessible by all {len(depts)} department(s)."
                       if universal else f"No returns are accessible by all {len(depts)} department(s).",
                       count=len(universal))

    if query_type == "max_access":
        # "which return is accessible by the MAXIMUM number of
        # departments" — the single top return, not the whole ranking.
        top = rows[:1]
        return _result("dept_return_access_matrix", "Return With Widest Department Access",
                       top,
                       f"'{top[0]['ReturnName']}' is accessible by the most departments ({top[0]['DepartmentCount']})."
                       if top else "No department-return mappings found.")

    return _result("dept_return_access_matrix", "Department <-> Return Access Matrix",
                   rows, f"{len(rows)} return(s) have at least one department with access; "
                         f"'{dept_counts[0]['DeptName']}' has the most returns ({dept_counts[0]['ReturnCount']})."
                         if rows and dept_counts else "No department-return mappings found.",
                   top_department=dept_counts[0] if dept_counts else None)


def handle_my_return_access(scope: dict, entities: dict, store: XMLStore) -> dict:
    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        return _not_found("my_return_access", "My Return Access", "Your department could not be found.")
    target_return = entities.get("target_return", "")
    form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
    nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}

    if target_return:
        # enforce_department_auth=False: this handler answers "does MY
        # department have access to X" — a return outside the caller's
        # allowed set is a valid "No" answer here, not something to deny
        # asking about (unlike return_profile/next_reporting_date/etc.,
        # which would leak the return's own content).
        ret, early = resolve_named_return(
            store, scope, target_return, intent="my_return_access", label="My Return Access",
            enforce_department_auth=False,
        )
        if early:
            return early
        has_access = ret.get("Id", "") in form_ids or ret.get("ReturnId", "") in form_ids \
            or ret.get("Id", "") in nx_ids or ret.get("ReturnId", "") in nx_ids
        verb = "does" if has_access else "does not"
        return _result("my_return_access", f"My Access: {ret.get('Name')}",
                       [{"ReturnName": ret.get("Name"), "HasAccess": has_access}],
                       f"Your department {verb} have access to return '{ret.get('Name')}'.", has_access=has_access)

    xbrl = [store.enrich_return(r) for r in store.returns() if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    non_xbrl = [dict(r) for r in store.non_xbrl_returns() if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]
    records = [{"type": "XBRL", **r} for r in xbrl] + [{"type": "Non-XBRL", **r} for r in non_xbrl]
    return _result("my_return_access", "My Return Access", records,
                   f"You have access to {len(xbrl)} XBRL and {len(non_xbrl)} non-XBRL returns "
                   f"({len(xbrl) + len(non_xbrl)} total).",
                   total=len(xbrl) + len(non_xbrl))


def handle_dept_full_return_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_department", "")
    dept = store.resolve_dept(target) if target else None
    if not dept:
        return _not_found("dept_full_return_list", "Department Return List",
                          f"Department '{target}' not found." if target else "Please specify a department name.")
    form_ids = [f.strip() for f in dept.get("Forms", "").split("|") if f.strip()]
    nx_ids = [f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()]
    xbrl = [store.enrich_return(r) for r in store.returns() if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    non_xbrl = [dict(r) for r in store.non_xbrl_returns() if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]
    records = [{"type": "XBRL", **r} for r in xbrl] + [{"type": "Non-XBRL", **r} for r in non_xbrl]
    return _result("dept_full_return_list", f"Complete Return List: {dept.get('Name')}", records,
                   f"Department '{dept.get('Name')}' has {len(xbrl)} XBRL and {len(non_xbrl)} non-XBRL returns "
                   f"({len(records)} total).", total=len(records),
                   show_dept_id=bool(entities.get("want_dept_id")))
