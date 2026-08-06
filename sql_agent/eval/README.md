# Accuracy Evaluation

Benchmarks the NL -> SQL pipeline against the hand-written ground truth in
`table_qa.json` (question + correct SQL, per table).

## Run it

```
python -m eval.run_eval                     # full run: retrieval + SQL validity + DB execution match
python -m eval.run_eval --no-exec           # skip DB execution (no Oracle connection needed)
python -m eval.run_eval --table CIMS_RAQ_M_SEC1_PART_A_DOM
python -m eval.run_eval --limit 20          # quick smoke run
```

## Metrics

| Metric | What it measures | Where a regression points |
|---|---|---|
| Table retrieval accuracy | Was the correct table among `get_relevant_schema`'s matched tables? | `src/retriever.py` (embeddings, RRF weights, score cutoffs) |
| Avg. column recall | Of the columns the gold SQL actually needs, how many did retrieval surface? | `src/retriever.py` column search / `embedding_building` |
| SQL validity rate | Did `validate_sql` accept the generated SQL? | `src/sql_generator.py` prompt/model, or schema.json data errors |
| Execution success rate | Of valid SQL, how much actually ran against Oracle without error? | schema.json vs real DB drift (see below) |
| Execution match accuracy | Did the generated SQL return the *same rows* as the gold SQL? | The real end-to-end correctness number — everything upstream can pass and this can still fail if the query is valid but wrong |

Execution success/match require a live Oracle connection (`src/config.py`
DB_* settings). Use `--no-exec` when no DB is reachable — you still get
retrieval accuracy and SQL validity.

## Output

Each run writes to `eval/results/`:
- `run_<timestamp>.json` — every question's full detail (matched tables/columns, generated SQL, validation reason, execution result) for debugging a specific failure.
- `latest_summary.md` — the aggregate numbers plus a per-table breakdown, overwritten each run so you can diff between runs.

## Extending the ground truth

`table_qa.json` (repo root) is the source of truth: a list of table entries,
each with a `qa_pairs: [{question, sql}, ...]` array. Add more question/SQL
pairs there — especially for tables that show up with low scores in
`latest_summary.md` — to widen coverage.

## A validity/exec-success gap without a validity/model regression usually means schema drift

If `sql_validity_rate` is high but `execution_success_rate` is low, the
generated SQL is well-formed against `schema.json` but `schema.json` itself
doesn't match the real Oracle table (see the `test/schema.json` PARTA/PARTB
column mixup fixed in this repo's history) — check schema.json against the
live DB (`embedding_building/extract_schema.py`) before touching the model
or prompts.
