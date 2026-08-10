"""Shared named-return resolution for every return-scoped db_qa handler.

Every handler that takes a `target_return` entity (return_profile,
return_validation_config, next_reporting_date, departments_with_return_access,
department_has_return, returns_submittable_by_dept, submissions_for_return,
my_submission_history, submission_list, notification_query, cross_entity_query,
...) used to call store.resolve_return() directly, which ALWAYS collapses to
a single best guess (or None) — so a partial/ambiguous name like "cims"
silently answered with whatever fuzzy match won, instead of asking the user
which return they meant. next_reporting_date got a proper disambiguation
flow first (find_return_candidates + a 0/1/many branch); this module lifts
that same behavior into one shared helper so every other return-scoped
handler gets identical treatment — same underscore/space/symbol-insensitive
matching, same "found N returns, which one?" prompt shape, same
department-authorization filtering — without duplicating that branch
13 times across 6 files.
"""
from __future__ import annotations

import difflib

from backend.db_qa.xml_store import XMLStore
from backend.db_qa.query_handlers._extraction_guard import (
    UNDERSTAND_FAILURE_MSG,
    looks_like_extraction_garbage,
)

_MAX_DISAMBIGUATION_OPTIONS = 15


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def return_form_ids(ret: dict) -> set[str]:
    """The Id/ReturnId pair used to key a return into a department's
    pipe-delimited Forms/NXForms access list."""
    return {v for v in (ret.get("Id", ""), ret.get("ReturnId", "")) if v}


def check_return_auth(ret: dict, scope: dict) -> dict | None:
    """Return an access-denied result dict if *ret* is outside the caller's
    department's allowed FormIds — or None if access is granted.

    scope["allowed_form_ids"] is populated by access_control.scope_query()
    for every target_type=="return" query. allowed_form_ids is None when
    authorization is disabled/not configured (allow), otherwise membership
    in the set is required — same convention as agent/__init__.py's
    _check_name_auth().
    """
    allowed = scope.get("allowed_form_ids")
    if allowed is None:
        return None
    if return_form_ids(ret) & allowed:
        return None
    return _not_found(
        "access_denied", "Access Denied",
        f"You don't have access to return '{ret.get('Name', '')}'.",
    )


def _fuzzy_name_suggestions(store: XMLStore, query: str, limit: int = 5,
                             xbrl_type: str | None = None) -> list[str]:
    pool: list[dict] = []
    if xbrl_type != "non_xbrl":
        pool += list(store.returns())
    if xbrl_type != "xbrl":
        pool += list(store.non_xbrl_returns())
    names = sorted({r.get("Name", "") for r in pool if r.get("Name")})
    return difflib.get_close_matches(query, names, n=limit, cutoff=0.4)


def resolve_named_return(
    store: XMLStore,
    scope: dict,
    target: str,
    *,
    intent: str,
    label: str,
    no_target_message: str | None = None,
    enforce_department_auth: bool = True,
    xbrl_type: str | None = None,
) -> tuple[dict | None, dict | None]:
    """Resolve a user-typed return name/id to exactly one return.

    Returns (ret, None) on a clean single match — caller proceeds normally.
    Returns (None, result_dict) when the caller should return result_dict
    immediately as-is: no name given, no match, ambiguous (multiple
    matches -> disambiguation prompt), or (when enforce_department_auth)
    access denied.

    This is the single place that owns: find_return_candidates() (compact-
    normalised matching, so "cims ror"/"CIMS_ROR"/"cims-ror" all resolve
    identically), department-authorization filtering, and the "found N
    returns, which one did you mean?" disambiguation shape (meta
    disambiguation=True + options=[...], consumed by db_qa_router.py and
    agent/__init__.py's STAGE_RETURN_QA session-state handoff) — so every
    return-scoped handler gets the same behavior for free instead of each
    reimplementing (or omitting) it.

    enforce_department_auth=False: skip both the candidate-list filtering
    AND the final access-denied check. Use this ONLY for handlers whose
    whole purpose is truthfully answering an access question itself (e.g.
    "does MY department have access to return X" / "does department Y have
    access to return X") — for those, a return outside the caller's allowed
    set is a valid "No" answer, not something to deny asking about. Every
    other handler (profile/validation-config/next-reporting-date/...) that
    would otherwise LEAK the return's content should leave this True.

    xbrl_type ("xbrl"/"non_xbrl", None = both): restricts matching to that
    return type, so a type-specific handler can never resolve a name to a
    return of the other type. Pass it from any handler that only ever
    answers about one type (e.g. nonxbrl_return_profile) or whose question
    named the type explicitly — the restriction is applied while searching,
    so the "did you mean" suggestions stay type-correct too.
    """
    target = (target or "").strip()
    if not target:
        return None, _not_found(
            intent, label,
            no_target_message or "Please specify a return name.",
        )

    all_candidates = store.find_return_candidates(target, limit=None, xbrl_type=xbrl_type)

    allowed = scope.get("allowed_form_ids")
    if enforce_department_auth and allowed is not None:
        all_candidates = [r for r in all_candidates if return_form_ids(r) & allowed]

    if not all_candidates:
        # "I couldn't find a return matching 'does my department'" — the
        # quoted text is parser output, not anything the user typed. Same
        # rule as the department/role not-found paths.
        if looks_like_extraction_garbage(target):
            return None, _not_found(intent, label, UNDERSTAND_FAILURE_MSG)
        fuzzy = _fuzzy_name_suggestions(store, target, xbrl_type=xbrl_type)
        msg = f"I couldn't find a return matching '{target}'."
        if fuzzy:
            msg += " Did you mean: " + ", ".join(fuzzy) + "?"
        else:
            msg += " Please check the return name and try again."
        return None, _not_found(intent, label, msg)

    if len(all_candidates) > 1:
        names = list(dict.fromkeys(c.get("Name", "") for c in all_candidates if c.get("Name")))
        total = len(names)
        shown = names[:_MAX_DISAMBIGUATION_OPTIONS]
        if total > len(shown):
            summary = (
                f"Found {total} returns matching '{target}' — showing the first {len(shown)}. "
                "Please use a more specific name, or pick one below."
            )
        else:
            summary = f"Found {total} returns matching '{target}'. Which one did you mean?"
        # records is a list of clean {"ReturnName": ...} rows, NOT the raw
        # XML dicts — the generic frontend table renderer shows every key
        # in a record verbatim, so passing full return rows here would dump
        # XSDPath/namespaces/validation flags/etc. alongside the picker.
        return None, _result(
            intent, f"{label} — Multiple Matches", [{"ReturnName": n} for n in shown],
            summary, disambiguation=True, options=shown,
        )

    ret = all_candidates[0]
    if enforce_department_auth:
        denied = check_return_auth(ret, scope)
        if denied:
            return None, denied
    return ret, None
