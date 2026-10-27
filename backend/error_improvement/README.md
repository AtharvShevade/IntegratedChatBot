# error_improvement (inside the chatbot)

This folder is a **generated copy** of the standalone error-improvement engine (developed and tested in `D:\Error_improvement`).
Do not edit the copied modules here: change them in the standalone project and re-run its `integration/sync_to_chatbot.py`.

## What it does in the chatbot
For a failing formula rule, `adapter.explain_batch()` returns an explanation card in this shape, which the UI shows as sections:

    N. <rule name>
    Checks / Problem / Cause / Fix / Related impact
    Cell details   (Item | Sheet | Cell | Row label | Current value)
    Calculation details   (Description | Amount)
    Explanation note (how it was produced, and how sure the cell locations are)

It finds the exact Excel cell from the user's uploaded workbook, the return's mapping, the template (formulas), the rule
definitions and the instance XML, and tells apart a cell it verified from one it inferred. If a calculated (formula) cell is the
cause, it explains why the formula shows its value instead of telling the user to type into it.

## How it is wired
- `backend/tools/formula_error.py::explain_formula_error_file` asks `adapter.explain_batch()` first; every rule it cannot explain
  goes through the existing explanation unchanged. Any error inside the engine is logged and means "use the existing explanation".
- `backend/tools/error_card.py` knows the new `table` section (text rendering); `frontend/src/components/MessageBubble.jsx` renders it.
- The engine imports the chatbot's own `backend.tools.formula_expression` and `formula_kind`.

## Switches (environment)
| Variable | Default | Meaning |
|---|---|---|
| `ERROR_IMPROVEMENT` | `1` | `0` turns the engine off; the chatbot behaves as before |
| `ERROR_IMPROVEMENT_REPO` | the chatbot's repo root (`BASE_REPO_PATH`) | repo root the engine reads (5.5 layout: `DataBase/<id>`, `Instance/<id>`) |
| `TEMPLATE_CACHE_DIR` | `backend/error_improvement/.template_cache` | where converted binary templates are cached |

## Limits
- English only: other languages keep the existing translated explanation. 6.0 repos are not read yet (the engine uses the 5.5 layout).
- The first explanation of an error file reads the workbook and takes a few seconds (up to ~25 s for large files); later pages of the same file come from a small in-memory cache.
- Binary `.xls` templates are converted to `.xlsx` once with Microsoft Excel or LibreOffice when one is installed; without either, calculated-cell reasons are skipped.
- Needs `xlrd` (see `requirements.txt`) to read old `.xls` workbooks.

## Rollback
Set `ERROR_IMPROVEMENT=0`, or switch back to `11-final_chatbot`.
