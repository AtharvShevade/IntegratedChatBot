"""backend/agent/error_explanation.py — on-demand error category explanation,
triggered by the frontend's ErrorSummaryPanel ("Explain Next Errors").

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.agent.state import _build

logger = logging.getLogger(__name__)

_CATEGORY_DISPLAY = {
    "formula_error": "Formula Errors",
    "xbrl_schema":    "XBRL Schema Errors",
    "dimensional":    "Dimension Errors",
}


async def explain_category_for_report(
    error_file_path: str,
    category: str,
    form_id: str | None = None,
    report_name: str | None = None,
    offset: int = 0,
    lang: str = "en",
) -> dict[str, Any]:
    """Explain one batch (size = report_lookup._MAX_EXPLAIN, currently 3) of
    errors for the given category from error_file_path, starting at *offset*.

    Runs the existing on-demand explanation pipeline
    (explain_errors_by_category_for_form, unchanged) in a background thread
    since it performs blocking LLM calls, then formats the result as a
    chat-style response so the frontend can append it as a new bubble.

    *offset* (how many errors in this category were already explained in
    earlier batches of the same conversation) is supplied by the caller —
    this function is otherwise stateless; it never stores or tracks offsets
    itself. Response carries has_more/next_offset/total_count in `data` so
    the frontend can decide whether to show an "Explain Next Errors" button
    and, if so, what offset to request next. Never regenerates errors
    already covered by [0, offset) — that range is simply not re-parsed
    into this batch.
    """
    from backend.tools.report_lookup import explain_errors_by_category_for_form, count_errors_by_category

    category_label = _CATEGORY_DISPLAY.get(category, category)
    offset = max(0, int(offset or 0))

    if category not in ("formula_error", "xbrl_schema", "dimensional"):
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text=f"Unsupported error category: {category}",
            result_type="error",
        )

    if not error_file_path:
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text="No error file is available for this report.",
            result_type="error",
        )

    loop = asyncio.get_event_loop()
    try:
        explained = await loop.run_in_executor(
            None,
            explain_errors_by_category_for_form,
            error_file_path,
            category,
            form_id or "",
            offset,
            lang or "en",
        )
    except Exception as exc:
        logger.error(
            "[EXPLAIN_CATEGORY] category=%s path=%s failed: %s",
            category, error_file_path, exc,
        )
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text=(
                f"Sorry, I couldn't generate explanations for {category_label} right now. "
                "Please try again."
            ),
            result_type="error",
        )

    if not explained:
        response_text = (
            f"No {category_label.lower()} could be parsed from the error file."
            if offset == 0 else
            f"No further {category_label.lower()} remain to explain."
        )
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text=response_text,
            result_type="error",
        )

    n = len(explained)
    next_offset = offset + n

    # total_count reuses count_errors_by_category (now unique-rule-based for
    # formula_error/xbrl_schema) rather than re-deriving it here — same
    # numbers the summary panel already showed the user.
    total_count = next_offset
    try:
        counts = count_errors_by_category(error_file_path, form_id=form_id or "")
        total_count = counts.get(category, next_offset)
    except Exception as exc:
        logger.warning("[EXPLAIN_CATEGORY] count lookup failed, falling back: %s", exc)

    has_more = next_offset < total_count
    text = (
        f"⚙ {category_label} — showing {offset + 1}-{next_offset} of {total_count}"
        if total_count else
        f"⚙ {category_label} — showing {n}"
    )

    return _build(
        intent="explain_errors",
        report_name=report_name,
        response_text=text,
        result_type="final",
        error_details=explained,
        data={
            "has_more":    has_more,
            "next_offset": next_offset,
            "total_count": total_count,
        },
    )


__all__ = ["explain_category_for_report", "_CATEGORY_DISPLAY"]
