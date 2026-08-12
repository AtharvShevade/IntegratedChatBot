"""
Table selection: turn a retrieval shortlist into exactly ONE table (or an
explicitly declared join pair) before the SQL model ever sees the schema.

Why this exists
---------------
Retrieval used to hand its top-3 tables straight to SQLCoder-7B. Every logged
failure in eval/results/hallucination_log.jsonl that involved multiple candidate
tables shows the same behaviour: the model JOINed all of them and fabricated a
join key to make it work (`cims_raq_q_sec7_exp_cr.cims_raq_q_sec1_part_a_dom_fk`,
`cims_raq_q_sec2_part_a.id`). A prose instruction telling it not to ("Allowed
tables is listed in relevance order... use ONLY that table") did not work at 7B.

So the fix is structural: retrieval widens for recall, this module narrows for
precision, and the SQL model receives one table (or two, only when a join is
explicitly declared in the semantic layer — never invented).

This used to make an LLM call (an instruct model on the same Ollama proxy as
the SQL model) to arbitrate ambiguous shortlists. Measured in production, that
single call cost 75-135s+ — often MORE than SQL generation itself — almost
certainly because the selector model and SQLCoder together didn't fit in the
Ollama host's memory, forcing a reload on every alternating call. It was
replaced with the deterministic heuristic below: retrieval's own fused RRF
score already ranks candidates, and the one case that genuinely needs a
second table (a declared join) is fully determined by the semantic layer, so
no model call was ever required to make this decision safely.

Every failure/ambiguous path falls back to the top-1 retrieved table, never to
top-3 or an invented join.
"""

import logging

log = logging.getLogger("selector")

# Below this many candidates there is nothing to choose, so there is no
# decision to make at all.
MIN_CANDIDATES_FOR_LLM = 2

# When the best candidate's fused RRF score dominates the runner-up by this
# factor, retrieval is already confident.
DOMINANCE_RATIO = 2.0


def _declared_join_selection(tables, join_graph=None):
    """
    The only case where more than one table is ever selected: the top-2
    candidates form a pair the semantic layer explicitly declares a join for.

    Returns {"tables": [...], "join_hint": str} or None. Never invents a
    join — an undeclared or absent join_graph simply means "no second table".
    """
    if not join_graph or len(tables) < 2:
        return None

    top_two = tables[:2]
    pair = tuple(sorted(t["table"].lower() for t in top_two))
    declared = join_graph.get(pair)
    if not declared:
        return None

    return {
        "tables": [{"table": t["table"], "why": "", "columns": []} for t in top_two],
        "join_hint": f"Join the two tables above ON {declared}.",
    }


def select_tables(question, tables, matched_labels=None, join_graph=None):
    """
    Narrow a retrieval shortlist to the table(s) that actually go in the prompt.

    Returns (selected_tables, selection) where selected_tables is the list to
    pass on to generate_sql (in place of the shortlist) and selection carries
    the join hint for prompt rendering, or None when the plain top-1 fallback
    was used (the common case).

    Purely deterministic — makes no network call.
    """
    if not tables:
        return [], None

    # ── Short-circuits, cheapest first ───────────────────────────────────────
    if tables[0].get("strong_match"):
        log.info("Selector skipped: near-duplicate prior question identifies %s", tables[0]["table"])
        return tables[:1], None

    if len(tables) < MIN_CANDIDATES_FOR_LLM:
        return tables[:1], None

    top_score = tables[0].get("score") or 0.0
    runner_up = tables[1].get("score") or 0.0
    if runner_up and top_score >= runner_up * DOMINANCE_RATIO:
        log.info(
            "Selector skipped: %s dominates on retrieval score (%.3f vs %.3f)",
            tables[0]["table"], top_score, runner_up,
        )
        return tables[:1], None

    # ── Ambiguous shortlist: only a DECLARED join can justify a second table ──
    selection = _declared_join_selection(tables, join_graph)
    if selection:
        chosen_names = {t["table"].lower() for t in selection["tables"]}
        selected_tables = [t for t in tables if t["table"].lower() in chosen_names]
        log.info("Selector chose declared join %s (from %d candidates)",
                 [t["table"] for t in selected_tables], len(tables))
        return selected_tables, selection

    log.info("Selector fell back to top-1 %s (from %d ambiguous candidates, no declared join)",
             tables[0]["table"], len(tables))
    return tables[:1], None
