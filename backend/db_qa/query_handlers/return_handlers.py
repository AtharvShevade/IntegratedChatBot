"""New-taxonomy handlers — PERIOD, XBRL_RETURNS, NON_XBRL_RETURNS,
DEPT_RETURN_MAPPING categories."""
from __future__ import annotations

import calendar
import re
from collections import Counter
from datetime import date, datetime

from backend.db_qa.xml_store import XMLStore, get_attr
from backend.db_qa.query_handlers._return_resolution import resolve_named_return

# Same date vocabulary as instance_generator.py's _DATE_FMT/_EXTRA_FMTS,
# plus a bare "Month YYYY" form (e.g. "June 2025") since date-range
# questions commonly name a month rather than a specific day.
_DATE_FMTS = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"]
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
        my = _parse_month_year(date_from)
        if my:
            year, month = my
            last_day = calendar.monthrange(year, month)[1]
            return date(year, month, 1), date(year, month, last_day)

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

# 6.0's Period.xml has no Frequency attribute at all (5.5's does) and many
# 6.0 Return records also leave RepFreq empty — so the "resolve frequency"
# chain (Frequency -> RepFreq) that works for 5.5 can come up completely
# empty for 6.0. PeriodName is always present in both versions, so it's
# the last-resort fallback: same canonical PeriodName -> Frequency-code
# mapping as 5.5's logs/period.xml (Daily->D, Weekly->W, ... Yearly->Y).
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
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return None
        dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
        return store.dept_by_id(dept_id) if dept_id else None
    target = entities.get("target_department", "")
    return store.resolve_dept(target) if target else None


# ── PERIOD ───────────────────────────────────────────────────────────────

def handle_period_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    periods = list(store.periods())
    return _result("period_list", "Reporting Periods", periods,
                   f"There are {len(periods)} reporting period(s) configured.", count=len(periods))


def handle_period_lookup(scope: dict, entities: dict, store: XMLStore) -> dict:
    period_name = entities.get("period_name", "")
    period_id = entities.get("period_id", "")
    periods = store.periods()
    match = None
    if period_id:
        match = next((p for p in periods if get_attr(p, "Period_Id", "Id", default="") == str(period_id)), None)
    elif period_name:
        match = next((p for p in periods if p.get("PeriodName", "").lower() == period_name.lower()), None)
    if not match:
        return _not_found("period_lookup", "Period Lookup",
                          "Please specify a period name or id." if not (period_name or period_id)
                          else f"No period found matching {period_name or period_id!r}.")
    return _result("period_lookup", f"Period: {match.get('PeriodName')}", [match],
                   f"Period '{match.get('PeriodName')}' has id {get_attr(match, 'Period_Id', 'Id', default='')}.")


def handle_returns_by_frequency(scope: dict, entities: dict, store: XMLStore) -> dict:
    period_name = entities.get("period_name", "")
    periods = store.periods()
    period_id = None
    for p in periods:
        if p.get("PeriodName", "").lower() == period_name.lower():
            period_id = get_attr(p, "Period_Id", "Id", default="")
            break
    if not period_id:
        return _not_found("returns_by_frequency", "Returns by Frequency",
                          f"Period '{period_name}' not found." if period_name else "Please specify a period.")

    rets = [store.enrich_return(r) for r in store.returns() if r.get("PeriodId") == period_id]
    if scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        if dept:
            form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
            rets = [r for r in rets if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    label = f"{period_name} Returns" + (" (Mine)" if scope["target_type"] == "self" else "")
    return _result("returns_by_frequency", label, rets, f"Found {len(rets)} {period_name} return(s).", count=len(rets))


# ── XBRL_RETURNS ─────────────────────────────────────────────────────────

def handle_return_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    category = entities.get("category", "")
    returns = [store.enrich_return(r) for r in store.returns()]

    if scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        if dept:
            form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
            returns = [r for r in returns if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]

    if category:
        returns = [r for r in returns if category.lower() in r.get("Name", "").lower()
                   or category.lower() in r.get("ReturnId", "").lower()]

    if query_type == "active":
        returns = [r for r in returns if r.get("Status", "").lower() == "true"]
    elif query_type == "inactive":
        returns = [r for r in returns if r.get("Status", "").lower() != "true"]
    elif query_type == "cims":
        returns = [r for r in returns if r.get("IsCims", "").lower() == "true"]
    elif query_type == "istbl":
        returns = [r for r in returns if r.get("IsTBL", "").lower() == "true"]

    label = "My XBRL Returns" if scope["target_type"] == "self" else "XBRL Returns"
    active_count = sum(1 for r in returns if r.get("Status", "").lower() == "true")
    return _result("return_list", label, returns,
                   f"There are {len(returns)} XBRL returns ({active_count} active).",
                   count=len(returns), active=active_count)


def handle_return_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    ret, early = resolve_named_return(store, scope, target, intent="return_profile", label="Return Profile")
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
    period_info = get_period_info(period_id, store._tenant_id) or {}
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

    ret, early = resolve_named_return(store, scope, target, intent="return_field", label="Return Field")
    if early:
        return early

    ret_name = ret.get("Name", target)

    if field == "return_id":
        value = ret.get("ReturnId") or ret.get("Id", "") or "Not set"
        return _result("return_field", f"Return ID: {ret_name}", [{"ReturnName": ret_name, "ReturnId": value}],
                       f"The return ID for '{ret_name}' is {value}.")

    if field == "frequency":
        value = _resolve_return_frequency_label(store, ret)
        return _result("return_field", f"Frequency: {ret_name}", [{"ReturnName": ret_name, "Frequency": value}],
                       f"'{ret_name}' is filed on a '{value}' basis.")

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
        row["HasFormulaValidation"] = r.get("IsFormulaValidation", "false")
        row["HasSchCalcValidation"] = r.get("IsSchCalValidation", "false")
        row["HasLargeValidator"] = r.get("IsLargeValidator", "false")
        row["HasRBIValidation"] = r.get("IsRBIValidation", "false")
        row["IsCIMS"] = r.get("IsCims", "false")
        results.append(row)

    if detail_type == "formula":
        results = [r for r in results if r["HasFormulaValidation"].lower() == "true"]
        label = "Returns with Formula Validation"
    elif detail_type in ("schema", "sch"):
        results = [r for r in results if r["HasSchCalcValidation"].lower() == "true"]
        label = "Returns with Schema-Calculation Validation"
    elif detail_type == "rbi":
        results = [r for r in results if r["HasRBIValidation"].lower() == "true"]
        label = "Returns with RBI Validation"
    elif detail_type == "large":
        results = [r for r in results if r["HasLargeValidator"].lower() == "true"]
        label = "Returns Using Large Validator"
    else:
        label = "Returns with Validation Settings"

    return _result("return_validation_config", label, results,
                   f"Found {len(results)} return(s) matching validation criteria.", count=len(results))


def handle_returns_submittable_by_dept(scope: dict, entities: dict, store: XMLStore) -> dict:
    target_return = entities.get("target_return", "")
    if target_return:
        # "which departments can submit return X" — same as departments_with_return_access
        ret, early = resolve_named_return(store, scope, target_return, intent="returns_submittable_by_dept", label="Departments That Can Submit")
        if early:
            return early
        ret_id, ret_code = ret.get("Id", ""), ret.get("ReturnId", "")
        matches = []
        for d in store.departments():
            form_ids = {f.strip() for f in d.get("Forms", "").split("|") if f.strip()}
            if ret_id in form_ids or ret_code in form_ids:
                matches.append(d)
        return _result("returns_submittable_by_dept", f"Departments That Can Submit {ret.get('Name')}",
                       matches, f"{len(matches)} department(s) can submit '{ret.get('Name')}'.", count=len(matches))

    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_department', '')}'"
        return _not_found("returns_submittable_by_dept", "Submittable Returns", f"{who} department could not be found.")
    form_ids = [f.strip() for f in dept.get("Forms", "").split("|") if f.strip()]
    rets = [store.enrich_return(r) for r in store.returns() if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    who_phrase = "You can" if scope["target_type"] == "self" else f"Department '{dept.get('Name')}' can"
    return _result("returns_submittable_by_dept", "Submittable XBRL Returns",
                   rets, f"{who_phrase} submit {len(rets)} XBRL return(s).", count=len(rets))


def _resolve_return_frequency_code(store: XMLStore, ret: dict) -> tuple[str, str]:
    """Return (frequency_code, period_name) for *ret*, using the same
    resolution order as handle_next_reporting_date: PeriodMaster's own
    Frequency code (5.5, authoritative) -> PeriodName mapped through the
    canonical table -> the return's own RepFreq as a last resort. RepFreq
    is checked LAST, not second, because it isn't guaranteed to use the
    same code alphabet next_reporting_date() understands (e.g. 6.0 data
    has been seen with RepFreq="A" on a return whose actual period is
    Yearly/"Y" — "A" isn't one of next_reporting_date()'s recognised
    codes, so trusting RepFreq over the unambiguous PeriodName->code
    mapping silently produced "no fixed period-end" for a return that
    plainly has one). Shared by handle_next_reporting_date and
    handle_reports_upcoming_in_range so the two can never disagree.
    """
    from backend.tools.instance_generator import get_period_info

    period_id = get_attr(ret, "PeriodId", "Period_Id", default="")
    period_info = get_period_info(period_id, store._tenant_id) or {}
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
    return's PeriodId, resolved against period.xml (5.5) / Period.xml (6.0)
    via instance_generator.get_period_info() — the same source used to
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
    )
    if early:
        return early

    frequency, period_name = _resolve_return_frequency_code(store, ret)
    due_days = (ret.get("DueDays") or "").strip() or None

    result = next_reporting_date(frequency, due_days)
    ret_name = ret.get("Name", target)

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


def _filter_by_xbrl_type(store: XMLStore, returns: list[dict], xbrl_type: str | None) -> list[dict]:
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


def handle_reports_filed_in_range(scope: dict, entities: dict, store: XMLStore) -> dict:
    """Returns actually SUBMITTED (an InstanceLog row exists) with a filing
    timestamp (DTC) between two dates — e.g. 'show me all XBRL reports
    filed between 01-Jan-2026 and 31-Mar-2026'. 'Filed between' is read as
    the actual submission timestamp falling in the window, not the
    ReportingDate (the period the submission is FOR) — those are
    different questions."""
    date_from = entities.get("date_from")
    date_to = entities.get("date_to")
    resolved = resolve_date_range(date_from, date_to)
    if not resolved:
        return _not_found(
            "reports_filed_in_range", "Reports Filed",
            "Please specify a date range, e.g. \"show me all XBRL reports filed between 01-Jan-2026 and 31-Mar-2026\".",
        )
    start, end = resolved

    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        return _not_found(
            "reports_filed_in_range", "Reports Filed",
            "Your department could not be found, so filed returns can't be determined.",
        )
    allowed_ids = _dept_allowed_return_ids(store, dept) or set()

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
        f"Found {len(matches)} {type_phrase}report(s) filed by your department between "
        f"{start.strftime('%d-%b-%Y')} and {end.strftime('%d-%b-%Y')}.",
        count=len(matches),
    )


def handle_reports_upcoming_in_range(scope: dict, entities: dict, store: XMLStore) -> dict:
    """Returns whose computed NEXT reporting/due date falls between two
    dates — e.g. 'what XBRL reports are coming up between 01-Jul-2026 and
    31-Jul-2026'. Computes one candidate next-due-date per return (today
    forward) using the same logic as handle_next_reporting_date, and lists
    the ones landing inside the window — this covers 'next month'/'this
    month'/a short explicit window; it does not enumerate multiple future
    occurrences of a return across a longer span."""
    from backend.tools.instance_generator import next_reporting_date

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

    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        return _not_found(
            "reports_upcoming_in_range", "Upcoming Reports",
            "Your department could not be found, so upcoming returns can't be determined.",
        )
    allowed_ids = _dept_allowed_return_ids(store, dept) or set()

    xbrl_type = entities.get("xbrl_type")
    all_returns = list(store.returns()) + list(store.non_xbrl_returns())
    all_returns = _filter_by_xbrl_type(store, all_returns, xbrl_type)
    all_returns = [r for r in all_returns if r.get("Id", "") in allowed_ids or r.get("ReturnId", "") in allowed_ids]

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
        f"Found {len(matches)} {type_phrase}return(s) due for your department between "
        f"{start.strftime('%d-%b-%Y')} and {end.strftime('%d-%b-%Y')}.",
        count=len(matches),
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
        returns = [r for r in returns if not r.get("DueDays", "").strip()]
    elif query_type == "has_folder":
        returns = [r for r in returns if r.get("HasFolder", "").lower() == "true"]

    label = "My Non-XBRL Returns" if scope["target_type"] == "self" else "Non-XBRL Returns"
    return _result("nonxbrl_return_list", label, returns,
                   f"There are {len(returns)} non-XBRL returns.", count=len(returns))


def handle_nonxbrl_return_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    ret = None
    for r in store.non_xbrl_returns():
        if target and (r.get("Name", "").lower() == target.lower() or r.get("ReturnId", "") == target or r.get("Id", "") == target):
            ret = r
            break
    if not ret:
        return _not_found("nonxbrl_return_profile", "Non-XBRL Return Profile",
                          f"Non-XBRL return '{target}' not found." if target else "Please specify a return name.")
    return _result("nonxbrl_return_profile", f"Non-XBRL Return: {ret.get('Name')}", [ret],
                   f"Details for non-XBRL return '{ret.get('Name')}'.")


# ── DEPT_RETURN_MAPPING ──────────────────────────────────────────────────

def handle_dept_return_access_matrix(scope: dict, entities: dict, store: XMLStore) -> dict:
    depts = store.departments()
    all_return_ids = [r.get("Id", "") for r in store.returns() if r.get("Id")]
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
                   f"({len(records)} total).", total=len(records))
