"""backend/agent/report_resolution.py — shared multi-candidate report-name
resolution used by status and generate flows alike.

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import logging

from backend.llm_extractor import _extract_search_terms as extract_search_terms
from backend.tools.report_lookup import find_matching_reports

logger = logging.getLogger(__name__)


def _resolve_report_name(
    user_query: str,
    llm_hint: str | None = None,
) -> tuple[str, list[dict]]:
    """Shared multi-candidate report name resolver used by ALL intents.

    Both status and generate flows call this so they get identical matching
    behaviour regardless of LLM extraction quality.

    Candidates are tried in priority order:
      1. LLM-extracted hint  (most precise when the model is correct)
      2. Intent/filler-stripped version  (_extract_search_terms)
         Strips words like "generate", "instance", "for" so that
         "generate instance for cims" → "cims" → matches CIMS_RAQ reports.
      3. Raw user query  (last resort — handles bare identifiers like "r091")

    Returns:
        (winning_candidate, matching_report_dicts)
        If no candidate produces a match, winning_candidate is the best
        non-empty candidate available (for use in error messages).
    """
    candidates: list[str] = []
    if llm_hint and llm_hint.strip():
        candidates.append(llm_hint.strip())
    stripped = extract_search_terms(user_query)
    if stripped and stripped not in candidates:
        candidates.append(stripped)
    raw = user_query.strip()
    if raw and raw not in candidates:
        candidates.append(raw)

    for candidate in candidates:
        matches = find_matching_reports(candidate)
        if matches:
            logger.debug(
                "[RESOLVE_REPORT] winner=%r matches=%d (llm_hint=%r)",
                candidate, len(matches), llm_hint,
            )
            return candidate, matches

    best = next((c for c in candidates if c), user_query.strip())
    return best, []


__all__ = ["_resolve_report_name"]
