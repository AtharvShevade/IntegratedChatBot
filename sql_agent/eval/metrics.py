import re

from src.sql_generator import _load_all_columns


def table_hit(gold_table, matched_tables):
    """Was the gold table among the retriever's matched tables, and at what rank (1-indexed)?"""
    names = [t.upper() for t in matched_tables]
    gold = gold_table.upper()
    if gold in names:
        return True, names.index(gold) + 1
    return False, None


def column_recall(gold_table, gold_sql, matched_columns):
    """
    Fraction of the gold table's real columns that are (a) referenced in the
    gold SQL and (b) also present in the retriever's matched columns for that
    table. Measures whether column-level retrieval surfaced what the correct
    query actually needed.
    """
    real_cols = {c["column"].upper() for c in _load_all_columns([gold_table])}
    if not real_cols:
        return None  # table itself unknown to schema — not a column-retrieval problem

    sql_upper = gold_sql.upper()
    referenced = {
        c for c in real_cols
        if re.search(rf'\b{re.escape(c)}\b', sql_upper)
    }
    if not referenced:
        return None  # gold SQL uses no named columns (e.g. SELECT *) — recall undefined

    matched = {
        c["column"].upper() for c in matched_columns
        if c["table"].upper() == gold_table.upper()
    }
    hit = referenced & matched
    return len(hit) / len(referenced)


def rows_equal(cols_a, rows_a, cols_b, rows_b):
    """
    Order/column-position independent comparison of two result sets.
    Returns True only if both queries returned the same multiset of rows
    (compared as sorted tuples of stringified values) — this is the
    "execution accuracy" check used in text-to-SQL benchmarks.
    """
    if cols_a is None or cols_b is None:
        return None
    norm_a = sorted(tuple(str(v) for v in row) for row in rows_a)
    norm_b = sorted(tuple(str(v) for v in row) for row in rows_b)
    return norm_a == norm_b
