"""backend/agent/comparison.py — instance-vs-instance XBRL variance
comparison: disambiguation, execution, and generic status-result formatting.

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import asyncio
import re
import logging
from typing import Any

from backend.tools.report_lookup import find_matching_reports, fuzzy_report_suggestions, get_form_id_by_name
from backend.agent.state import (
    _build, _session_context,
    STAGE_CMP_REPORT, STAGE_CMP_FILE, STAGE_REPORT, STAGE_DATE, STAGE_RUN, STAGE_PREV_DATES,
)
from backend.agent.auth_filters import _filter_names_by_auth

logger = logging.getLogger(__name__)


async def _handle_compare(report_ident: str, session_id: str | None, allowed_form_ids: set[str] | None = None) -> dict[str, Any]:
    """Entry point for compare_reports intent — handles disambiguation."""
    matches = find_matching_reports(report_ident)
    all_matches = matches
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        suggestions = fuzzy_report_suggestions(report_ident)
        if allowed_form_ids is not None:
            suggestions = _filter_names_by_auth(suggestions, allowed_form_ids)
        if suggestions:
            opts_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(suggestions))
            if session_id:
                _session_context[session_id] = {
                    "awaiting": STAGE_CMP_REPORT, "pending_options": suggestions,
                }
            return _build(
                intent="compare_reports", report_name=None,
                response_text=(
                    f"No exact match for '{report_ident}'. Did you mean:\n\n"
                    f"{opts_text}\n\nReply with the number."
                ),
                result_type="disambiguation", options=suggestions,
            )
        if allowed_form_ids is not None and all_matches:
            return _build(
                intent="compare_reports", report_name=None,
                response_text="You are not authorised to access this report.",
                result_type="error",
            )
        return _build(
            intent="compare_reports", report_name=None,
            response_text=f"No matching reports found for '{report_ident}'.",
            result_type="error",
        )

    if len(matches) > 1:
        names = list(dict.fromkeys(m.get("Name", "") for m in matches if m.get("Name")))
        opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(names))
        if session_id:
            _session_context[session_id] = {
                "awaiting": STAGE_CMP_REPORT, "pending_options": names,
            }
        return _build(
            intent="compare_reports", report_name=None,
            response_text=(
                f"I found {len(names)} matching reports. Which one to compare?\n\n"
                f"{opts_text}\n\nReply with the name."
            ),
            result_type="disambiguation", options=names,
        )

    return await _compare_with_name(matches[0].get("Name", report_ident), session_id)



_VARIANCE_TABLE_ROWS = 30


def _serialize_variance_rows(rows: list[dict], label_a: str, label_b: str) -> list[dict]:
    """One variance row → the JSON shape the frontend consumes.

    This used to be an inline six-key dict duplicated at both comparison call
    sites, and it DROPPED five fields compute_variance had already computed:
    context_key, unit, anomaly_flags, sign_change and severity. Both the
    variance table and the chart modal are written to read all five — the
    sign-reversal highlight, the anomaly badge, the unit in the tooltip and
    the severity chip are all coded and styled — so every one of those
    features was silently inert, reading undefined. Nothing new is computed
    here; the data was being thrown away one line before it was needed.
    """
    return [
        {
            "concept":       r["concept"],          # display label, incl. [member]
            "concept_base":  r.get("concept_base", r["concept"]),
            "val_a":         r[label_a],
            "val_b":         r[label_b],
            "diff":          r["diff"],
            "pct_change":    r["pct_change"],
            "significant":   r["significant"],
            "context_key":   r.get("context_key", ""),
            "unit":          r.get("unit", ""),
            "anomaly_flags": r.get("anomaly_flags", []),
            "sign_change":   r.get("sign_change", False),
            "severity":      r.get("severity", ""),
            # Regulatory-importance fields — populated only when the return's
            # taxonomy yielded an ImportanceIndex. Defaults keep the shape
            # stable so the frontend never has to test for their existence.
            "section":         r.get("section", ""),
            "section_code":    r.get("section_code", ""),
            "importance":      r.get("importance", None),
            "importance_tier": r.get("importance_tier", ""),
            # Whether the return's JSON actually classified this concept.
            # False means "importance unavailable", which is NOT the same as
            # tier Low — the UI must never filter an unclassified concept into
            # a tier bucket or present it as low priority.
            "importance_matched": bool(r.get("importance_matched", False)),
            # Taxonomy labels for the concept and each dimension member, used
            # to build a business name without CamelCase guessing.
            "concept_label": r.get("concept_label", ""),
            "member_labels": r.get("member_labels", []),
            "mandated_by":     r.get("mandated_by", []),
            "importance_why":  r.get("importance_why", []),
            "priority":        r.get("priority", None),
        }
        for r in rows
    ]


# Kept for backward-compat import only — no longer the fixed filter; see
# _headline_rows below, which selects dynamically via
# variance_explain._select_eligible_tiers (the same logic the frontend's
# selectHeadlineTiers mirrors). Everything outside the selected window stays
# in the dataset and remains reachable from the chart's tier filter — this
# bounds what is DISPLAYED/explained, never what was compared.
_HEADLINE_TIERS = ("Critical", "High")


def _headline_rows(rows: list[dict]) -> list[dict]:
    """The highest-available-tier(s) slice, in the order the rows were
    already ranked -- never hardcoded to Critical/High. If a comparison has
    zero Critical or High changes the window slides to High+Medium, then
    Medium+Low, down to just Low, so the narrative/table never treat "no
    Critical/High" as "nothing important" when a lower tier genuinely
    changed.

    Returns [] when the return has no importance data at all, OR when
    nothing in any tier changed, which the caller must treat as "fall back
    to the ranked top slice"/"nothing to analyse" respectively — the two
    look identical in the result and are not the same. Rows the JSON did
    not classify are never included: unclassified is not a tier, and
    promoting one here would assert an importance the data lacks.
    """
    from backend.tools.variance_explain import _select_eligible_tiers
    tiers = _select_eligible_tiers(rows)
    return [
        r for r in rows
        if r.get("importance_matched") and r.get("importance_tier") in tiers
    ]


def _summary_rows(rows: list[dict]) -> list[dict]:
    """Rows offered to the narrative generator.

    The full Critical/High set — NOT a slice. Selection (top 20, max 3
    dimensional variants per concept) happens inside variance_explain, which
    needs the whole eligible set to apply the per-concept cap; pre-trimming
    here would let one concept exhaust the list before the cap could spread it.

    Falls back to the ranked top slice when the return has no importance data,
    which is the behaviour that existed before tiers.
    """
    headline = _headline_rows(rows)
    return headline or rows[:_VARIANCE_TABLE_ROWS]


async def _generate_variance_explanations(
    eligible: list[dict], all_rows: list[dict],
    label_a: str, label_b: str, name: str,
) -> str:
    """One business sentence per selected high-priority fact.

    *all_rows* is passed separately because share-of-total needs the parent
    and sibling rows, which are not in the eligible subset.
    """
    from backend.tools.variance_explain import generate_explanations
    # The inline path deliberately returns NOTHING. The explanations are the
    # model's work, and the model cannot answer inside a comparison request —
    # it needs 30-90s. Returning Python's template here would put the fallback
    # on screen as the normal result, which is exactly what it must not be.
    #
    # The frontend sees an empty summary, shows its "Analysing…" state, and
    # fetches the real explanations from /compare-summary. Templates appear
    # only inside that call, per fact, when a model line fails validation.
    _ = (eligible, all_rows, label_a, label_b, name)
    return ""


def _build_variance_payload(
    facts_a: list[dict], label_a: str,
    facts_b: list[dict], label_b: str,
    form_id: str | None = None,
) -> tuple[list[dict], list[dict], list[dict], dict, str]:
    """Compare EVERYTHING once, then derive every view from that one result.

    Returns (all_rows_raw, all_serialized, table_serialized, meta, text_table).

    The ordering matters and is the whole point: compute_variance is called
    with top_n=None so alignment and scoring cover every comparable pair, and
    the 30-row table is a slice taken AFTERWARDS. The chart therefore receives
    the complete set while the table keeps its existing size — and there is no
    second, hidden cap anywhere on the chart path.

    *form_id* enables the regulatory-importance view: the return's own taxonomy
    is read for the section, circular mandate and validation weight behind each
    concept, rows are ranked by that as well as by movement, and the rows are
    additionally grouped into business sections. It is optional and fails soft
    — no taxonomy folder means the payload is exactly what it was before, with
    empty groups and an empty importance report.
    """
    # Function-local, matching how the comparison call sites already import
    # this module (Arelle pulls in a heavy dependency tree at import time).
    from backend.tools.xbrl_comparator import (
        compute_variance, format_variance_table, variance_meta,
    )

    # Importance is READ from the return's generated taxonomy JSON
    # (<repo>/JSON/<form_id>.json), never recalculated from the taxonomy here.
    # The JSON is the single source of truth: it was scored once at generation
    # time, so a comparison cannot disagree with it, and no taxonomy folder
    # needs to be present on the serving machine.
    index = None
    if form_id:
        try:
            from backend.tools.importance_json import get_importance_from_json
            index = get_importance_from_json(form_id)
        except Exception as exc:
            logger.warning(
                "[VARIANCE] importance JSON unavailable for form_id=%s: %s",
                form_id, exc,
            )

    # `stats` collects the intersection bookkeeping compute_variance already
    # does internally, so the UI can state how many facts were excluded for
    # existing in only one period rather than leaving it to a debug log.
    stats: dict = {}
    all_rows = compute_variance(
        facts_a, label_a, facts_b, label_b, top_n=None, stats=stats,
        importance=index,
    )
    table_rows = all_rows[:_VARIANCE_TABLE_ROWS]
    meta = {**variance_meta(all_rows, facts_a, facts_b, len(table_rows)), **stats}

    logger.info(
        "[VARIANCE] compared=%d concepts=%d dimensional=%d significant=%d "
        "table=%d facts_a=%d facts_b=%d one_sided_excluded=%d",
        meta["compared"], meta["concepts"], meta["dimensional"],
        meta["significant"], meta["table_rows"], meta["facts_a"], meta["facts_b"],
        meta.get("one_sided", 0),
    )
    return (
        all_rows,
        _serialize_variance_rows(all_rows, label_a, label_b),
        _serialize_variance_rows(table_rows, label_a, label_b),
        meta,
        # The plain-text chat table stays the top-30 view it has always been.
        format_variance_table(table_rows, label_a, label_b),
    )


def _variance_response_text(
    name: str, label_a: str, label_b: str, table: str,
) -> str:
    """The chat body for a comparison: heading plus the concept table."""
    head = f"Variance Analysis — {name}\nComparing: {label_a}  vs  {label_b}\n\n"
    return head + table


async def _compare_with_name(name: str, session_id: str | None) -> dict[str, Any]:
    """Resolve Report ID → scan instance folder → present selection.

    Only path: Returns.xml → Report ID → {INSTANCE_BASE_DIR}/{id}/ → *.xml
    No fallbacks to XML_InstanceLog or logs/ prefix scan.
    """
    from backend.services.instance_service import get_instances_for_report

    # ── Step 1: resolve report name to FormId via Returns.xml ─────────────────
    form_id = get_form_id_by_name(name)
    if not form_id:
        if session_id:
            _session_context.pop(session_id, None)
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"Report '{name}' was not found in Returns.xml. "
                "Please check the report name and try again."
            ),
            result_type="error",
        )

    # ── Step 2: scan Instance/{FormId}/ — no fallbacks ────────────────────────
    instances = get_instances_for_report(form_id)

    # ── Error guards ──────────────────────────────────────────────────────────
    # Always clear session on error so stale STAGE_CMP_REPORT / STAGE_CMP_FILE
    # cannot interfere with the user's next request.
    if not instances:
        if session_id:
            _session_context.pop(session_id, None)
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"No instance files found for '{name}' (FormId: {form_id}). "
                # f"The folder Instance/{form_id}/ does not exist or contains no XML files."
            ),
            result_type="error",
        )

    if len(instances) < 2:
        if session_id:
            _session_context.pop(session_id, None)
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"'{name}' has only {len(instances)} instance file — "
                "at least 2 are needed for comparison."
            ),
            result_type="error",
        )

    # ── Build rich metadata for the interactive frontend selector ─────────────
    instances_meta = [
        {
            "index":          i,
            "filename":       inst["instance_path"],
            "reporting_date": inst["reporting_date"],
            "run_at":         inst["dtc"],
            "label":          inst.get("label") or f"{inst['reporting_date']} | Generated: {inst['dtc']}",
            "status":         inst.get("status", ""),
        }
        for i, inst in enumerate(instances)
    ]

    msg = (
        f"'{name}' — {len(instances)} instance file(s) found.\n"
        "Select exactly 2 instances to compare."
    )
    if session_id:
        _session_context[session_id] = {
            "awaiting":        STAGE_CMP_FILE,
            "cmp_instances":   instances,
            "cmp_return_name": name,
            # Carried so the comparison can find the return's taxonomy folder
            # for the regulatory-importance view without a second lookup.
            "cmp_form_id":     form_id,
            "auto_a":          0,
            "auto_b":          1,
        }
    return _build(
        intent="compare_reports", report_name=name,
        response_text=msg, result_type="instance_selection",
        options=[f"{inst['reporting_date']} (run: {inst['dtc']})" for inst in instances],
        instances_data=instances_meta,
    )


async def _run_comparison(
    session:    dict[str, Any],
    user_query: str,
    session_id: str | None,
) -> dict[str, Any]:
    """Execute the actual XBRL variance analysis once files are confirmed."""
    from backend.tools.xbrl_comparator import (
        load_xbrl_facts, compute_variance, format_variance_table, generate_llm_summary,
    )

    instances = session.get("cmp_instances", [])
    name      = session.get("cmp_return_name", "")
    idx_a     = session.get("auto_a", 0)
    idx_b     = session.get("auto_b", 1)
    # Sessions created before cmp_form_id existed (and any caller that builds
    # one by hand) still resolve, so the importance view is never lost to a
    # stale session shape.
    form_id   = session.get("cmp_form_id") or (get_form_id_by_name(name) if name else None)

    raw = user_query.strip().lower()

    # Match by option label text — user may click an option button in the UI
    # e.g. "30-Sep-2021 (run: 11-Jun-2025 05:43:52 PM)" selects that instance.
    label_match = next(
        (i for i, inst in enumerate(instances)
         if inst["reporting_date"] in user_query or user_query.strip() in inst.get("dtc", "")
         or user_query.strip() == f"{inst['reporting_date']} (run: {inst['dtc']})"),
        None,
    )
    if label_match is not None:
        idx_a = label_match
        idx_b = (label_match + 1) % len(instances)
        # Produce final comparison directly
        inst_a  = instances[idx_a]
        inst_b  = instances[idx_b]
        label_a = inst_a["reporting_date"]
        label_b = inst_b["reporting_date"]
        if label_a == label_b:
            def _run_time(inst: dict) -> str:
                dtc = inst.get("dtc", "")
                parts = dtc.split(" ")
                return parts[1] if len(parts) >= 2 else "?"
            label_a = f"{label_a} (run {_run_time(inst_a)})"
            label_b = f"{label_b} (run {_run_time(inst_b)})"
        if session_id:
            _session_context.pop(session_id, None)
        try:
            # Arelle parsing is blocking CPU/IO work — run both loads in
            # worker threads (not inline on the event loop) so a slow
            # taxonomy load doesn't stall every other concurrent request.
            # The two are independent, so load them concurrently rather
            # than one after the other.
            facts_a, facts_b = await asyncio.gather(
                asyncio.to_thread(load_xbrl_facts, inst_a["full_path"]),
                asyncio.to_thread(load_xbrl_facts, inst_b["full_path"]),
            )
        except ImportError as exc:
            return _build(intent="compare_reports", report_name=name,
                          response_text="Unable to perform the comparison right now. Please try again.", result_type="error")
        except Exception as exc:
            logger.error("XBRL load error: %s", exc, exc_info=True)
            return _build(intent="compare_reports", report_name=name,
                          response_text="Unable to perform the comparison right now. Please try again.",
                          result_type="error")
        (variance_rows, all_serialized, table_serialized, v_meta, table) = (
            _build_variance_payload(facts_a, label_a, facts_b, label_b, form_id)
        )
        # The narrative describes the ranked TOP slice, not all N rows — a
        # full set would not fit a prompt. variance_meta is what tells the
        # user how much was actually compared.
        llm_summary = await _generate_variance_explanations(
            _summary_rows(variance_rows), variance_rows, label_a, label_b, name,
        )
        return _build(intent="compare_reports", report_name=name,
                      response_text=_variance_response_text(
                          name, label_a, label_b, table,
                      ),
                      result_type="variance_table",
                      variance_data=table_serialized,
                      variance_all=all_serialized,
                      variance_meta=v_meta,
                      variance_label_a=label_a,
                      variance_label_b=label_b,
                      llm_summary=llm_summary)

    # Parse "1 vs 3", "2 and 1", "1, 2", etc.
    nums = re.findall(r"\d+", user_query)
    if len(nums) >= 2:
        a, b = int(nums[0]) - 1, int(nums[1]) - 1
        if 0 <= a < len(instances) and 0 <= b < len(instances) and a != b:
            idx_a, idx_b = a, b
        else:
            return _build(
                intent="compare_reports", report_name=name,
                response_text=(
                    f"Invalid selection. Pick two different numbers between 1 and {len(instances)}."
                ),
                result_type="error",
            )
    elif raw not in ("confirm", "yes", "ok", "proceed", "y"):
        opts_text = "\n".join(
            f"{i + 1}. {inst['reporting_date']} (run: {inst['dtc']})"
            for i, inst in enumerate(instances)
        )
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"Type 'confirm' to compare "
                f"{instances[idx_a]['reporting_date']} vs {instances[idx_b]['reporting_date']}, "
                f"or pick two numbers (e.g. '1 vs 3').\n\n{opts_text}"
            ),
            result_type="instance_selection",
            options=[f"{inst['reporting_date']} (run: {inst['dtc']})" for inst in instances],
        )

    inst_a  = instances[idx_a]
    inst_b  = instances[idx_b]
    label_a = inst_a["reporting_date"]
    label_b = inst_b["reporting_date"]
    if label_a == label_b:
        def _run_time(inst: dict) -> str:
            dtc = inst.get("dtc", "")
            parts = dtc.split(" ")
            return parts[1] if len(parts) >= 2 else "?"
        label_a = f"{label_a} (run {_run_time(inst_a)})"
        label_b = f"{label_b} (run {_run_time(inst_b)})"

    if session_id:
        _session_context.pop(session_id, None)

    try:
        # See the identical block above: keep Arelle's blocking parse off
        # the event loop, and load both instances concurrently.
        facts_a, facts_b = await asyncio.gather(
            asyncio.to_thread(load_xbrl_facts, inst_a["full_path"]),
            asyncio.to_thread(load_xbrl_facts, inst_b["full_path"]),
        )
    except ImportError as exc:
        return _build(
            intent="compare_reports", report_name=name,
            response_text="Unable to perform the comparison right now. Please try again.", result_type="error",
        )
    except Exception as exc:
        logger.error("XBRL load error: %s", exc, exc_info=True)
        return _build(
            intent="compare_reports", report_name=name,
            response_text="Unable to perform the comparison right now. Please try again.",
            result_type="error",
        )

    (variance_rows, all_serialized, table_serialized, v_meta, table) = (
        _build_variance_payload(facts_a, label_a, facts_b, label_b, form_id)
    )
    llm_summary = await _generate_variance_explanations(
        _summary_rows(variance_rows), variance_rows, label_a, label_b, name,
    )

    return _build(
        intent="compare_reports", report_name=name,
        response_text=_variance_response_text(
            name, label_a, label_b, table,
        ),
        result_type="variance_table",
        variance_data=table_serialized,
        variance_all=all_serialized,
        variance_meta=v_meta,
        variance_label_a=label_a,
        variance_label_b=label_b,
        llm_summary=llm_summary,
    )


async def execute_comparison(
    session_id: str,
    idx_a: int,
    idx_b: int,
) -> dict[str, Any]:
    """Execute XBRL variance analysis for the two selected instances.

    Reads instance file paths from the server-side session that was set when
    the instance-selection UI was presented.  If the session has expired (e.g.
    the dev server restarted between showing the dropdowns and clicking
    Compare), returns a clear error so the user can restart the flow.
    """
    session = _session_context.get(session_id, {})

    if session.get("awaiting") != STAGE_CMP_FILE:
        return _build(
            intent="compare_reports",
            report_name=None,
            response_text=(
                "Comparison session not found or expired. "
                "Please start the comparison again by entering the report name."
            ),
            result_type="error",
        )

    instances = session.get("cmp_instances", [])
    if idx_a < 0 or idx_a >= len(instances) or idx_b < 0 or idx_b >= len(instances):
        return _build(
            intent="compare_reports",
            report_name=session.get("cmp_return_name"),
            response_text=(
                f"Invalid instance indices ({idx_a + 1}, {idx_b + 1}). "
                f"Valid range: 1–{len(instances)}."
            ),
            result_type="error",
        )

    if idx_a == idx_b:
        return _build(
            intent="compare_reports",
            report_name=session.get("cmp_return_name"),
            response_text="Please select two different instances to compare.",
            result_type="error",
        )

    # Delegate to _run_comparison; pass a synthetic "X vs Y" string so the
    # existing regex parser selects the correct indices cleanly.
    session_copy = dict(session)
    session_copy["auto_a"] = idx_a
    session_copy["auto_b"] = idx_b
    return await _run_comparison(
        session_copy,
        f"{idx_a + 1} vs {idx_b + 1}",
        session_id,
    )


def _from_result(
    result: dict[str, Any],
    intent: str = "get_status",
    session_id: str | None = None,
    keep_date_ctx: bool = False,
) -> dict[str, Any]:
    rtype = result["type"]

    if rtype == "latest_with_ask":
        ret_name        = result.get("return_name", result.get("report_name", ""))
        rep_date        = result.get("reporting_date", "")
        status          = result.get("status", "")
        run_time        = result.get("run_time", "")
        other_instances = result.get("other_instances", [])
        status_note     = result.get("status_note", "")
        job_id          = result.get("job_id")
        status_code     = result.get("status_code")
        error_category_counts = result.get("error_category_counts") or None
        is_4000_series = result.get("is_4000_series", False)   # ADD THIS

        text = (
            f"{ret_name}\n"
            f"Latest Reporting Date : {rep_date}\n"
            f"Status                : {status}"
        )
        if run_time:
            text += f"\nInitiated On          : {run_time}"
        if job_id:
            error_count = result.get("error_count", 0)
            if error_count > 0:
                text += f"\n\nErrors Found : {error_count}\n\nGenerating error explanations…"
        else:
            error_messages = result.get("error_messages", [])
            if error_messages:
                text += "\n\nFailure Reason(s):\n"
                text += "\n".join(f"• {m}" for m in error_messages)
        if status_note:
            text += f"\n{status_note}"

        response_data: dict[str, Any] = {}
        if status_code is not None:
            response_data["status_code"] = status_code
        if error_category_counts:
            response_data["error_category_counts"] = error_category_counts
        response_data["is_4000_series"] = is_4000_series   # ADD THIS
        response_data["form_id"] = result.get("form_id", "")   # ← ADD THIS LINE


        if other_instances:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":                STAGE_PREV_DATES,
                    "pending_form_id":         result["form_id"],
                    "pending_return_name":      ret_name,
                    "pending_other_instances": other_instances,
                }
            return _build(
                intent=intent, report_name=ret_name,
                response_text=text,
                result_type="ask_previous",
                options=["Yes", "No"],
                download_url=result.get("download_url", ""),
                download_label=result.get("download_label", ""),
                error_details=result.get("error_details") or None,
                job_id=job_id,
                data=response_data,
            )
        # No other instances — just show final status
        return _build(intent=intent, report_name=ret_name,
                      response_text=text, result_type="final",
                      download_url=result.get("download_url", ""),
                      download_label=result.get("download_label", ""),
                      error_details=result.get("error_details") or None,
                      job_id=job_id,
                      data=response_data)

    if rtype == "final":
        dtc    = result.get("dtc", "")
        job_id = result.get("job_id")
        status_code = result.get("status_code")
        error_category_counts = result.get("error_category_counts") or None
        is_4000_series = result.get("is_4000_series", False)   # ADD THIS

        text = (
            f"{result['report_name']}\n"
            f"Reporting Date : {result['reporting_date']}\n"
        )
        if dtc:
            text += f"Initiated On   : {dtc}\n"
        text += f"Status         : {result['status']}"
        if job_id:
            error_count = result.get("error_count", 0)
            if error_count > 0:
                text += f"\n\nErrors Found : {error_count}\n\nGenerating error explanations…"
        else:
            error_messages = result.get("error_messages", [])
            if error_messages:
                text += "\n\nFailure Reason(s):\n"
                text += "\n".join(f"• {m}" for m in error_messages)
        status_note = result.get("status_note", "")
        if status_note:
            text += f"\n{status_note}"
        if keep_date_ctx:
            text += '\n\nYou can select another reporting date, or say "new report" to switch reports.'

        response_data: dict[str, Any] = {}
        if status_code is not None:
            response_data["status_code"] = status_code
        if error_category_counts:
            response_data["error_category_counts"] = error_category_counts
        response_data["is_4000_series"] = is_4000_series   # ADD THIS
        response_data["form_id"] = result.get("form_id", "")   # ← ADD THIS LINE

        return _build(intent=intent, report_name=result["report_name"],
                      response_text=text, result_type="final",
                      download_url=result.get("download_url", ""),
                      download_label=result.get("download_label", ""),
                      error_details=result.get("error_details") or None,
                      job_id=job_id,
                      data=response_data)

    if rtype == "disambiguation":
        opts = result.get("options", [])
        opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(opts))
        msg = (
            f"I found {len(opts)} matching reports. Which one are you looking for?\n\n"
            f"{opts_text}\n\n"
            "Reply with the number or part of the name."
        )
        if session_id:
            _session_context[session_id] = {
                "awaiting":        STAGE_REPORT,
                "pending_options": opts,
            }
        return _build(intent=intent, report_name=None,
                      response_text=msg,
                      result_type="disambiguation",
                      options=opts)

    if rtype == "date_selection":
        ret_name = result.get("return_name", "this report")
        opts     = result.get("options", [])
        msg = f"Select a reporting date for '{ret_name}':"
        if session_id:
            _session_context[session_id] = {
                "awaiting":            STAGE_DATE,
                "pending_form_id":     result["form_id"],
                "pending_return_name": ret_name,
            }
        return _build(intent=intent, report_name=ret_name,
                      response_text=msg,
                      result_type="date_selection",
                      options=opts)

    if rtype == "run_selection":
        ret_name = result.get("return_name", "this report")
        rep_date = result.get("reporting_date", "")
        opts     = result.get("options", [])  # list of {"id", "label", "status", "dtc"}
        opts_text = "\n".join(f"{i + 1}. {o['label']}" for i, o in enumerate(opts))
        msg = (
            f"'{ret_name}' has {len(opts)} runs for {rep_date}. "
            f"Which run would you like to view?\n\n{opts_text}\n\n"
            "Reply with the number to select."
        )
        if session_id:
            _session_context[session_id] = {
                "awaiting":               STAGE_RUN,
                "pending_form_id":        result.get("form_id"),
                "pending_return_name":    ret_name,
                "pending_reporting_date": rep_date,
                "pending_runs":           opts,
            }
        return _build(
            intent=intent,
            report_name=ret_name,
            response_text=msg,
            result_type="run_selection",
            options=[o["label"] for o in opts],
        )

    # error — make message more conversational
    raw = result.get("message", "Something went wrong. Please try again.")
    msg = re.sub(
        r"No exact match found for '(.+?)'. Did you mean",
        r"I couldn't find '\1' exactly. Did you mean",
        raw,
    )
    msg = re.sub(
        r"No matching reports found for '(.+?)'",
        r"I couldn't find any report called '\1'",
        msg,
    )
    msg = re.sub(
        r"Found multiple matching reports\. Which one do you mean\?",
        "I found multiple matching reports. Which one are you looking for?",
        msg,
    )
    return _build(intent=intent, report_name=None, response_text=msg, result_type="error")


__all__ = [
    "_handle_compare",
    "_VARIANCE_TABLE_ROWS", "_serialize_variance_rows",
    "_HEADLINE_TIERS", "_headline_rows", "_summary_rows",
    "_generate_variance_explanations", "_build_variance_payload", "_variance_response_text",
    "_compare_with_name", "_run_comparison", "execute_comparison", "_from_result",
]
