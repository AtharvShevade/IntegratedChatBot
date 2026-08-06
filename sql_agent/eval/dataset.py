import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "table_qa.json")


def load_qa_pairs(path=None):
    """
    Flatten table_qa.json into one row per question:
      {table, question, gold_sql}
    table_qa.json is the ground-truth set: each table entry carries a list of
    qa_pairs (question -> hand-written correct SQL) used as the accuracy
    benchmark for retrieval + SQL generation.

    SCOPE WARNING: all 144 questions here target CIMS_RAQ_M_* (MONTHLY) tables,
    and NONE of their 35 gold tables exists in the default quarterly
    EMBEDDING_DIR — so scored against that build every metric is 0 by
    construction, because the gold tables are not in the index at all. Use
    load_quarterly_qa_pairs() for the quarterly scope. This is the same trap
    scripts/eval_retrieval.py documents in its load_dataset().
    """
    path = path or _DEFAULT_PATH
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for entry in data:
        table = entry.get("table_name")
        for qa in entry.get("qa_pairs", []):
            rows.append({
                "table": table,
                "question": qa["question"],
                "gold_sql": qa["sql"],
            })
    return rows


def load_quarterly_qa_pairs(path=None):
    """
    The 100 question/table/SQL triples in <EMBEDDING_DIR>/qa_pairs.json, in the
    same {table, question, gold_sql} shape as load_qa_pairs.

    This IS the quarterly ground truth, but it is also the SOURCE of
    qa_index.faiss, so scoring it with the qa signal enabled measures
    memorisation rather than retrieval — every question retrieves itself as an
    exact match. Run it with QA_SIGNAL_WEIGHT=0, which disables the qa search,
    its score bonus and its strong-match tier together:

        QA_SIGNAL_WEIGHT=0 python -m eval.run_eval --dataset qa_pairs

    (eval/raq_user_queries.json is the genuinely leak-free quarterly set, but it
    carries expected TABLES only — no gold SQL — so it cannot score execution
    match. Adding gold SQL there is what removes this compromise.)
    """
    import src.config as config
    path = path or os.path.join(config.EMBEDDING_DIR, "qa_pairs.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [
        {"table": e["table"], "question": e["question"], "gold_sql": e["sql"]}
        for e in data
    ]


def load_dataset(name="table_qa"):
    """Ground truth by name. See each loader for why they are not
    interchangeable."""
    if name == "qa_pairs":
        return load_quarterly_qa_pairs()
    if name == "table_qa":
        return load_qa_pairs()
    raise ValueError(f"unknown dataset {name!r} (expected 'table_qa' or 'qa_pairs')")
