"""
Warn when generated SQL filters a label column to a string literal that isn't
among its known stored values.

The model IS given the real allowed values for these columns (see
build_prompt() in src/sql_generator.py, sourced from description_samples.json)
but a 7B model can still hallucinate a plausible-sounding literal instead of
copying one verbatim. That SQL validates and executes cleanly — it just
silently returns 0 rows or the wrong rows. This check catches that class of
error the same way check_stock_aggregation() catches stock/flow misuse:
advisory only, never a hard failure.
"""
import difflib
import re

from src.description_fetcher import load_needs_trim, load_samples

# Matches COLUMN = 'value' and TRIM(COLUMN) = 'value' equality filters.
# Deliberately does not touch date literals ('2024-01-01') — validate_sql()
# already governs those separately, and MAX_SAMPLES-fetched label columns
# never legitimately hold date-shaped strings.
_LITERAL_EQ_RE = re.compile(
    r"\bTRIM\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*=\s*'([^']*)'"
    r"|\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*'([^']*)'",
    re.IGNORECASE,
)

MAX_SUGGESTIONS = 3


def check_literal_validity(sql: str, tables) -> list:
    """
    Returns a list of human-readable warnings; empty means nothing suspicious.

    Only checks columns tracked in description_samples.json for one of the
    passed tables — columns outside that tracked set are skipped silently
    rather than risking a false alarm on data this check has no visibility
    into.
    """
    if not sql:
        return []

    samples = load_samples()
    if not samples:
        return []
    needs_trim = load_needs_trim()

    table_names = [
        (t.get("table") if isinstance(t, dict) else t) for t in (tables or [])
    ]
    table_names = [t for t in table_names if t]

    # Build a per-column lookup across the tables actually in play. A column
    # name is unambiguous enough within one query's table set that we don't
    # need to track which literal came from which table.
    column_values = {}
    for t in table_names:
        table_samples = samples.get(t) or samples.get(t.lower()) or samples.get(t.upper())
        if not table_samples:
            continue
        trim_cols = {c.lower() for c in (needs_trim.get(t) or needs_trim.get(t.lower())
                                          or needs_trim.get(t.upper()) or [])}
        for col, values in table_samples.items():
            col_lower = col.lower()
            normalized = {
                (v.strip() if col_lower in trim_cols else v).lower(): v
                for v in values
            }
            column_values.setdefault(col_lower, normalized)

    if not column_values:
        return []

    warnings = []
    for m in _LITERAL_EQ_RE.finditer(sql):
        col = (m.group(1) or m.group(3) or "").lower()
        val = m.group(2) if m.group(1) else m.group(4)
        if col not in column_values:
            continue
        normalized_val = val.strip().lower()
        if normalized_val in column_values[col]:
            continue

        real_values = list(column_values[col].values())
        suggestions = difflib.get_close_matches(
            val, real_values, n=MAX_SUGGESTIONS, cutoff=0.4
        )
        hint = (
            f" Closest known values: {', '.join(repr(s) for s in suggestions)}."
            if suggestions else " No close match found among known values."
        )
        warnings.append(
            f"{col.upper()} = '{val}' is not a known stored value for this "
            f"column.{hint}"
        )
    return warnings
