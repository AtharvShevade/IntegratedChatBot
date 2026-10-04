# backend/agent/__init__.py -- package init only.
#
# Pipeline: intent → entity resolution → lookup → response.
# Session tracks last_search_terms and multi-turn stage state.
#
# The implementation used to live entirely in this file (~4200 lines). It is
# now split by responsibility into sibling modules, each re-exported below so
# every existing import path — `from backend.agent import decide`,
# `from backend.agent import _session_context`, etc. — keeps working exactly
# as before:
#
#   state.py             shared session/job store, stage constants, regexes, _build
#   background_jobs.py   fast status lookups + background LLM error-enrichment
#   auth_filters.py      user-id checks + FormId-based authorization filtering
#   conversational.py    fuzzy workflow-keyword detection, small talk
#   report_resolution.py shared multi-candidate report-name resolution
#   router.py            decide() — the central intent dispatcher
#   comparison.py        instance-vs-instance XBRL variance comparison
#   scheduling.py        report scheduling
#   generation.py        instance generation
#   error_explanation.py on-demand error category explanation
#   db_qa_router.py      unchanged — Application Q&A routing (own file already)

from __future__ import annotations

# Re-exported directly (not via a sibling module's __all__) because tests and
# other callers patch these as `backend.agent.<name>`, matching this file's
# original top-level import block.
from backend.llm_extractor import extract_intent_and_entities
from backend.services.llm_service import classify_conversational_intent

from backend.agent.state import *  # noqa: F401,F403
from backend.agent.background_jobs import *  # noqa: F401,F403
from backend.agent.auth_filters import *  # noqa: F401,F403
from backend.agent.conversational import *  # noqa: F401,F403
from backend.agent.report_resolution import *  # noqa: F401,F403
from backend.agent.comparison import *  # noqa: F401,F403
from backend.agent.scheduling import *  # noqa: F401,F403
from backend.agent.generation import *  # noqa: F401,F403
from backend.agent.error_explanation import *  # noqa: F401,F403
from backend.agent.router import decide

__all__ = [
    "decide",
    # background_jobs
    "_get_instance_by_dtc_fast_with_bg_job",
    "_get_instance_by_date_fast_with_bg_job", "_run_error_enrichment_async",
    "_start_error_enrichment_thread", "_get_status_fast_with_bg_job",
    "_get_status_by_id_fast_with_bg_job", "_ask_another_date",
    "_get_status_exact_fast_with_bg_job",
    # auth_filters
    "_is_real_user_id", "_filter_names_by_auth", "_check_name_auth",
    "_apply_auth_to_status_result",
    # conversational
    "_fuzzy_has_status", "_fuzzy_has_generate", "_fuzzy_has_schedule", "_fuzzy_has_compare",
    "_normalise_conversational", "_get_conversational_response",
    "_extract_status_search_terms", "_is_generic_status_terms", "_is_meaningful_report_terms",
    "_extract_schedule_search_terms", "_is_staged_session", "_parse_dtc_from_label",
    "_is_plausible_date", "_looks_like_new_query", "_get_conversational_response_for_category",
    "_classify_conversational",
    # report_resolution
    "_resolve_report_name",
    # comparison
    "_handle_compare", "_serialize_variance_rows", "_headline_rows", "_summary_rows",
    "_generate_variance_explanations", "_build_variance_payload", "_variance_response_text",
    "_compare_with_name", "_run_comparison", "execute_comparison", "_from_result",
    # scheduling
    "_validate_future_schedule_date", "_finalize_schedule", "_handle_schedule",
    # generation
    "_matching_instance_log_rows", "_parse_dtc", "_find_new_instance_log_id",
    "_finalize_generation", "_handle_gen_date", "_date_ask_prompt", "_handle_generate",
    # error_explanation
    "explain_category_for_report",
    # state (session/job stores + stage constants callers reach directly)
    "_session_context", "_error_jobs",
    "STAGE_DATE", "STAGE_REPORT", "STAGE_GEN_REPORT", "STAGE_GEN_DATE", "STAGE_RUN",
    "STAGE_SCHED_REPORT", "STAGE_SCHED_RPT_DATE", "STAGE_SCHED_DT", "STAGE_SCHED_CONFIRM",
    "STAGE_SCHED_NAME", "STAGE_CMP_REPORT", "STAGE_CMP_FILE", "STAGE_PREV_DATES", "STAGE_RETURN_QA",
]
