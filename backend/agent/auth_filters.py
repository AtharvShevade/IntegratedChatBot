"""backend/agent/auth_filters.py — user-id sanity checks and department/role
FormId-based authorization filtering for report-name results.

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.tools.report_lookup import get_form_id_by_name
from backend.agent.state import _build, _SESSION_GUID_RE

logger = logging.getLogger(__name__)


def _is_real_user_id(uid: str | None) -> bool:
    """Return True when *uid* looks like a genuine user/login identifier.

    Returns False for:
    * None / empty string
    * "0"  (sentinel from older .NET pages)
    * 32-char hex GUID (ASP.NET session UID forwarded by the iframe)
    * Standard UUID format  (same reason)
    """
    if not uid or uid == "0":
        return False
    return not _SESSION_GUID_RE.match(uid)


def _filter_names_by_auth(names: list[str], allowed: set[str] | None) -> list[str]:
    """Return only the report names whose FormId is in *allowed*.

    If *allowed* is ``None`` (no auth configured) all names pass through.
    """
    if allowed is None:
        return names
    result = []
    for name in names:
        fid = get_form_id_by_name(name) or ""
        if fid in allowed:
            result.append(name)
    return result


def _check_name_auth(report_name: str, allowed: set[str] | None, intent: str) -> dict[str, Any] | None:
    """Return an auth-error response dict if *report_name*'s FormId is not in *allowed*.

    Returns ``None`` when access is granted (either no auth configured, or
    the FormId is explicitly in the allowed set).
    """
    if allowed is None:
        return None
    fid = get_form_id_by_name(report_name)
    if not fid:
        logger.warning(
            "[AUTH_MISS] report=%r could not be resolved to a FormId before auth", report_name,
        )
        return _build(
            intent=intent,
            report_name=report_name,
            response_text=(
                f"I couldn't find any report matching '{report_name}'.\n"
                "Please check the report name and try again."
            ),
            result_type="error",
        )
    in_allowed = fid in allowed
    logger.info(
        "[AUTH_CHECK] Requested Return: %r | Resolved FormId: %r | "
        "Allowed Forms Contains %r: %s | Authorization: %s",
        report_name, fid, fid, str(in_allowed).upper(),
        "Allowed" if in_allowed else "DENIED",
    )
    if not in_allowed:
        logger.warning(
            "[AUTH_DENY] report=%r form_id=%r not in allowed set (allowed has %d entries)",
            report_name, fid, len(allowed),
        )
        return _build(
            intent=intent,
            report_name=report_name,
            response_text="You are not authorised to access this report.",
            result_type="error",
        )
    return None


def _apply_auth_to_status_result(result: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """Post-filter a ``get_report_status`` result dict through the auth set.

    Handles all result types returned by ``get_report_status``:
    - ``disambiguation``  — filter options list; error if none remain
    - ``date_selection``  — check form_id directly
    - ``run_selection``   — check form_id directly
    - ``final``           — look up FormId by report name and check
    - ``error``           — pass through unchanged
    """
    rtype = result.get("type", "")

    if rtype == "disambiguation":
        filtered = _filter_names_by_auth(result.get("options", []), allowed)
        if not filtered:
            return {
                "type":    "error",
                "message": "You are not authorised to access any of the matching reports.",
            }
        if len(filtered) < len(result.get("options", [])):
            opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(filtered))
            return {
                **result,
                "options": filtered,
                "message": (
                    "Found multiple matching reports. Which one do you mean?\n\n"
                    f"{opts_text}"
                ),
            }
        return result

    if rtype in ("date_selection", "run_selection"):
        fid = result.get("form_id", "")
        if fid not in allowed:
            logger.warning("[AUTH_DENY] form_id=%r not in allowed set (status result)", fid)
            return {"type": "error", "message": "You are not authorised to access this report."}
        return result

    if rtype == "final":
        fid = get_form_id_by_name(result.get("report_name", "")) or ""
        if fid not in allowed:
            logger.warning(
                "[AUTH_DENY] report=%r form_id=%r not in allowed set (final result)",
                result.get("report_name"), fid,
            )
            return {"type": "error", "message": "You are not authorised to access this report."}
        return result

    if rtype == "latest_with_ask":
        # Result returned when report has multiple instances and user is shown the latest.
        # form_id is always present in this result type (set by _build_status_result).
        fid = result.get("form_id", "")
        if fid not in allowed:
            logger.warning(
                "[AUTH_DENY] form_id=%r not in allowed set (latest_with_ask result)", fid
            )
            return {"type": "error", "message": "You are not authorised to access this report."}
        return result

    # "error" type: check _form_id if present — avoids leaking that a report
    # exists (e.g. "Report X exists but no instances") to unauthorised users.
    fid = result.get("_form_id", "")
    if fid and fid not in allowed:
        logger.warning(
            "[AUTH_DENY] form_id=%r not in allowed set (error result with _form_id)", fid
        )
        return {"type": "error", "message": "You are not authorised to access this report."}
    return result  # generic error / unknown — pass through


__all__ = [
    "_is_real_user_id",
    "_filter_names_by_auth",
    "_check_name_auth",
    "_apply_auth_to_status_result",
]
