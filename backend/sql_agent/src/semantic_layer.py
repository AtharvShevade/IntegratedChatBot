"""
The declared semantic layer: what Oracle cannot tell us about this schema.

Modelled on WrenAI's MDL. The principle that matters is the allow-list: a join
that is not declared here does not exist, and is rejected rather than merely
discouraged in a prompt. Nothing in eval/results/hallucination_log.jsonl was a
join the model got *slightly* wrong — the joins were invented outright
(`..._sec1_part_a_dom_fk`, `.id`), because nothing declared how tables relate.

The file lives beside the indexes it describes:
    {config.EMBEDDING_DIR}/semantic_layer.yaml

Every section is optional; an absent file simply means no declared joins, in
which case the selector falls back to allowing only CODE+RDATE conditions.

Shape:

    join_graph:
      - tables: [cims_raq_q_sec1_part_a_dom, cims_raq_q_sec1_part_b_dom]
        condition: "a.CODE = b.CODE AND a.RDATE = b.RDATE"
        note: "same section, domestic parts A and B"

    vertical:
      cims_raq_q_sec1_part_a_dom:
        label_column: period_delinquency
        total_row: "C. Total ( A + B)"
        needs_trim: false

    dom_ove:
      cims_raq_q_sec9_sensec_partb:
        - [tot_expo_dom, tot_expo_ove]

    multipart:
      - [cims_raq_q_sec1_part_a_dom, cims_raq_q_sec1_part_b_dom]

    metrics:
      gross npa ratio:
        table: cims_raq_q_sec2_part_a_npa
        expression: "..."
        note: "..."

    synonyms:
      npa: "non performing assets"
"""

import logging
import os

from src import config

log = logging.getLogger("semantic_layer")

_cache: dict = {}


def _layer_path() -> str:
    return os.path.join(config.EMBEDDING_DIR, "semantic_layer.yaml")


def load_semantic_layer(path: str | None = None) -> dict:
    """
    Load and cache the semantic layer for the active embedding dir.

    Returns {} when the file is absent — every consumer must treat an empty
    layer as "nothing declared", not as an error, so the pipeline keeps working
    before the layer is authored.
    """
    path = path or _layer_path()
    if path in _cache:
        return _cache[path]

    layer: dict = {}
    if os.path.exists(path):
        try:
            import yaml
            with open(path, encoding="utf-8") as fh:
                layer = yaml.safe_load(fh) or {}
        except Exception as e:                       # malformed YAML, missing pyyaml
            log.error("Could not load semantic layer %s: %s", path, e)
            layer = {}
    else:
        log.info("No semantic layer at %s — joins restricted to CODE+RDATE", path)

    _cache[path] = layer
    return layer


def clear_cache():
    """Drop the cached layer (call after editing the YAML in a live process)."""
    _cache.clear()


def load_join_graph(path: str | None = None) -> dict:
    """
    {(table_a_lower, table_b_lower): condition} for every declared join, keyed
    on the sorted table pair so lookup is order-independent.

    Returns {} when nothing is declared, which callers treat as "no join graph
    authored yet" rather than "no joins allowed".
    """
    layer = load_semantic_layer(path)
    graph = {}
    for edge in layer.get("join_graph") or []:
        tables = [str(t).lower() for t in (edge.get("tables") or [])]
        condition = str(edge.get("condition") or "").strip()
        if len(tables) == 2 and condition:
            graph[tuple(sorted(tables))] = condition
    return graph


def is_join_declared(table_a: str, table_b: str, path: str | None = None) -> bool:
    """
    True when this pair may be joined. An empty join graph means the layer has
    not been authored yet, so pairs are permitted — the validator still checks
    the join columns themselves. Once any edge is declared, the graph becomes
    authoritative and undeclared pairs are rejected.
    """
    graph = load_join_graph(path)
    if not graph:
        return True
    return tuple(sorted((table_a.lower(), table_b.lower()))) in graph


def vertical_spec(table: str, path: str | None = None) -> dict:
    """
    {"label_column", "total_row", "needs_trim"} for a vertical table, or {}.

    needs_trim exists because description_fetcher strips sampled label values,
    so a value stored as '     C2. Slipped to NPAs' is offered to the model
    without its leading whitespace and an exact `=` filter then matches nothing
    — a silent empty result, not an error.
    """
    layer = load_semantic_layer(path)
    spec = (layer.get("vertical") or {}).get(table.lower())
    return dict(spec) if isinstance(spec, dict) else {}


def dom_ove_pairs(table: str, path: str | None = None) -> list:
    """[(dom_column, ove_column), ...] that compose a total for this table."""
    layer = load_semantic_layer(path)
    pairs = (layer.get("dom_ove") or {}).get(table.lower()) or []
    return [tuple(str(c).lower() for c in pair) for pair in pairs if len(pair) == 2]


def multipart_group(table: str, path: str | None = None) -> list:
    """Sibling tables (_part_a/_part_b) that a total may span, including `table`."""
    layer = load_semantic_layer(path)
    lowered = table.lower()
    for group in layer.get("multipart") or []:
        names = [str(t).lower() for t in group]
        if lowered in names:
            return names
    return []


def metric_definition(question: str, path: str | None = None) -> dict:
    """
    Longest declared metric name appearing in the question, or {}.

    Longest-first so "gross npa ratio" wins over a bare "npa" when both are
    declared.
    """
    layer = load_semantic_layer(path)
    metrics = layer.get("metrics") or {}
    lowered = question.lower()
    best_name = None
    for name in metrics:
        if str(name).lower() in lowered:
            if best_name is None or len(str(name)) > len(best_name):
                best_name = str(name)
    if best_name is None:
        return {}
    spec = metrics[best_name]
    return {"name": best_name, **(spec if isinstance(spec, dict) else {"expression": spec})}
