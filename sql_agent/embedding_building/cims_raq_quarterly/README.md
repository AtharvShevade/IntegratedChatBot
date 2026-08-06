# CIMS_RAQ(Quarterly) — scoped embedding build

A self-contained embedding set for exactly one return, `CIMS_RAQ(Quarterly)`
(26 tables), built independently of the production `embedding_building/output/`
indexes — for isolated accuracy testing before scaling to all returns.

## Why this return, not "CIMS_RAQ(Annual)"

`data/.json-formatted` (the Excel-sourced description source of truth) has no
`"CIMS_RAQ(Annual)"` return at all. The 14 real return names it contains are
listed in `build_schema.py`'s output when you run it. `CIMS_RAQ(Quarterly)`
(26 described tables, all live in Oracle) was picked as the real, well-covered
return to validate the pipeline against.

## Files

| File | What it is |
|---|---|
| `check_db_connection.py` | Standalone check that `src/config.py`'s `DB_*` credentials are correct and reachable; also lists live `CIMS_RAQ_Q_*` tables. |
| `build_schema.py` | Parses `data/schema.sql`, filters to tables tagged `CIMS_RAQ(Quarterly)` in `data/.json-formatted`, cross-checks against live Oracle, writes `schema.json`. Flags tables whose columns disagree on return_name, and live tables with no Excel description at all. |
| `build_embeddings.py` | Reads `schema.json`, builds table/column embeddings + FAISS indexes, samples real row-label values from Oracle, builds the row-label index. Everything lands in this folder only. |
| `schema.json` | The scoped, enriched schema (26 tables) — table/column descriptions sourced from the real Excel data. |
| `table_index.faiss` / `table_meta.pkl` | Table-level embeddings. |
| `column_index.faiss` / `column_meta.pkl` | Column-level embeddings. |
| `description_samples.json` | Real distinct row-label values sampled live from Oracle (23 of the 26 tables have a label column). |
| `row_label_index.faiss` / `row_label_meta.pkl` | Embeddings over every sampled row-label value. |
| `qa_pairs.json` | 15 hand-written business-logic questions + verified gold SQL (see below). |

## qa_pairs.json

15 questions grounded in real row-label values (not "show me table X" —
each asks a business question that requires filtering to a specific,
real category/label, e.g. "3. Doubtful", "SMA-2", "Coal industry", pulled
from `description_samples.json`). **All 15 were executed against the live
DB and verified to return real rows with no errors.**

One real bug this surfaced: row-label sampling (`src/description_fetcher.py`)
`.strip()`s values before storing them, but several tables' actual DB values
have leading whitespace (e.g. `'     C2. Slipped to NPAs'`). An exact `=`
filter using the stripped sample would silently return zero rows — 3 of the
15 questions initially failed for exactly this reason, and were fixed to use
`WHERE TRIM(col) = '...'` instead. Any SQL generator prompt drawing on
sampled row-labels should either always use `TRIM()` for label-column
filters, or the sampler should stop stripping and store raw values.

## Regenerating

```
python embedding_building/cims_raq_quarterly/check_db_connection.py
python embedding_building/cims_raq_quarterly/build_schema.py
python embedding_building/cims_raq_quarterly/build_embeddings.py
```

## Bug fixed upstream while building this

`embedding_building/formatter.py::load_descriptions()` was reading
`item.get("db_name")` / `item.get("excel_name")` — fields that don't exist
in the real `data/.json-formatted` (the actual fields are `column_name` /
`column_Description`). This meant the function silently returned `{}` on
every real run, so **no Excel-sourced description had ever actually been
merged into any schema.json build, including production**. Fixed at the
source in `formatter.py`, so this benefits the full-schema build too.
