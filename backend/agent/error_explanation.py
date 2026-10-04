"""backend/agent/error_explanation.py — on-demand error category explanation,
triggered by the frontend's ErrorSummaryPanel ("Explain Next Errors").

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from backend.agent.state import _build
from backend.config import instance_base_dir

logger = logging.getLogger(__name__)

_ALLOWED_ERROR_FILE_EXTENSIONS = (".xml", ".html")


def _is_contained_error_file(error_file_path: str) -> bool:
    """True only if error_file_path resolves to a real path inside this
    request's instance_base_dir() and has an allowed extension.

    error_file_path is client-supplied (round-tripped from an earlier
    response) with no server-side rebuild, so it must be validated the same
    way /download-file validates form_id/filename before opening — otherwise
    a client could point it at an arbitrary file on the host (or a UNC share)
    and have its contents read back through the error-explanation pipeline.
    """
    if os.path.splitext(error_file_path)[1].lower() not in _ALLOWED_ERROR_FILE_EXTENSIONS:
        return False
    try:
        resolved = Path(error_file_path).resolve()
        base = Path(instance_base_dir()).resolve()
        resolved.relative_to(base)
    except (ValueError, OSError):
        return False
    return True

_CATEGORY_DISPLAY = {
    "formula_error": "Formula Errors",
    "xbrl_schema":    "XBRL Schema Errors",
    "dimensional":    "Dimension Errors",
}


async def explain_category_for_report(
    filename: str,
    category: str,
    form_id: str,
    report_name: str | None = None,
    offset: int = 0,
    lang: str = "en",
) -> dict[str, Any]:
    """Explain one batch (size = report_lookup._MAX_EXPLAIN, currently 3) of
    errors for the given category from the error file, starting at *offset*.

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

    L-17 / C-04 follow-up: the caller supplies only *filename* (a bare
    basename, previously round-tripped as a full absolute error_file_path —
    see git history) and *form_id*; the actual server path is rebuilt here
    via build_error_file_path(), the same helper /download-file already
    uses, instead of trusting any path from the client. This also stops the
    absolute server path (drive letter, tenant folder layout) from ever
    being returned to a caller in the first place.
    """
    from backend.tools.report_lookup import (
        explain_errors_by_category_for_form, count_errors_by_category, build_error_file_path,
    )

    category_label = _CATEGORY_DISPLAY.get(category, category)
    offset = max(0, int(offset or 0))

    if category not in ("formula_error", "xbrl_schema", "dimensional"):
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text=f"Unsupported error category: {category}",
            result_type="error",
        )

    if not filename or not form_id:
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text="No error file is available for this report.",
            result_type="error",
        )

    error_file_path = build_error_file_path(form_id, os.path.basename(filename))

    if not _is_contained_error_file(error_file_path):
        logger.warning(
            "[EXPLAIN_CATEGORY_DENIED] rebuilt path outside instance_base_dir() or "
            "disallowed extension: form_id=%r filename=%r", form_id, filename,
        )
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text="No error file is available for this report.",
            result_type="error",
        )

    try:
        # H-06: loop.run_in_executor(None, ...) does NOT copy contextvars into
        # the worker thread (unlike asyncio.to_thread), so config._active_root()
        # would silently read the default/unset root instead of this request's
        # actual tenant repo root under APP_VERSION=6.0 -- background_jobs.py
        # already documents and fixes this exact bug for its own threads;
        # this call site had the same bug and is fixed the same way here.
        explained = await asyncio.to_thread(
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
