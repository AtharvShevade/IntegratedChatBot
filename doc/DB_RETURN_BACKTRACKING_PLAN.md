# Error resolution for DB (data-prep) returns: analysis and plan

Status: plan only, nothing implemented. Source of truth for the engine is `D:\Error_improvement`; `backend/error_improvement/` is a synced copy.

## 1. How Excel backtracking works today

Fact (concept + context + value, read from the validator's `*_Instance.html`)
1. `Mapping_N.xml`: row whose `PriEle` = concept and whose `DimDom/Dim` members are inside the context -> cell code and `Cell="r~c"`.
2. `PreLnkBases.xml`: layout id -> layout name (a layout is a sheet range).
3. `XML_Query.xml`: layout (`TemplateId`) -> `From [Sheet$A1:B2]` -> sheet and range.
4. `Staging.xml`: row label -> row. Then confirmed when the uploaded workbook holds the value (value x template multiplier).
5. Fallbacks: learned row/column shift per layout; numbered sheet copies (`QCCPTwo` -> `X (2)`); value search in the sheet family; entry-row labels.
6. Rules: evaluate the formula, classify (DATA / RULE / COVER), solve the amount, pick the culprit cell by cross-rule evidence.
7. If the culprit is a formula cell in the template, evaluate the template formula and say why it shows its value (never "type into it").
8. Honesty tags: verified / inferred / likely; a cell is not named when two facts collide or an operand is unlocated.

Measured: 748 named, 747 correct against the validator's own `*_BTDetails.html` (the answer key, `score_bt.py`).

## 2. What is the same for a DB return and what changes

| Step | Excel return | DB return |
|---|---|---|
| fact -> mapping row -> layout | same | same (`Mapping_N`, `PreLnkBases`) |
| layout -> location | `XML_Query` `From [Sheet$range]` | `XML_Query` `From <TABLE>` plus `TabelMapping.xml` (`PriID` = TemplateId, may be `3|9`; `TableName`, `PrimaryColumn`, `FilterColumn`) |
| cell column -> | column letter | SELECT alias in `XML_Query` (`SR_NO as SrNo`) -> DB column |
| cell row -> | `Staging` label / workbook value | key columns (`SR_NO`, `RDATE`) from the instance contexts / `Staging` |
| confirmation | workbook value | extracted data (see risks); otherwise "mapped / inferred" only |
| ground truth | `*_BTDetails.html` | the same file has `DB TableName`, `Cell Index "Row: r, Col: c"`, `Cell Code` columns (4000 has one) |
| fix wording | "change cell G12 in sheet X" | "correct column C in table T where SR_NO = n, then re-extract" |

Two query shapes exist: code-value (2008: `CODE`, `DESCRIPTION`, `VAL`; row = the `CODE`) and columnar (2009: one record per `SR_NO`).
Expressions in the SELECT (`CODE+2`, `Union all`, 2008) map to an expression plus its underlying column, not to one plain column.

## 3. Implementation phases (in `D:\Error_improvement`, then re-sync)

1. **Reader** `db_locator.py`: layout -> table -> column. Read `TabelMapping.xml` (split `PriID` on `|`) and parse the SELECT of the matching `XML_Query` row (aliases, expressions, FROM table, union branches). Output: table, column or expression, key columns.
2. **Row key**: key value from the typed dimension / context (`SrNo`) or the `Staging` row; code-value layouts use the `CODE`.
3. **Answer key**: extend `score_bt.py` to read `DB TableName` / `Cell Index` / `Cell Code` and score the DB locator against it (same gate as the Excel one: named vs correct).
4. **Card**: `rule_cards.py` "Cell details" gets `Table | Column | Row key | Current value`; Fix text says "correct in the source table, then re-extract". Chatbot side: only the `table` section columns change (already generic in `MessageBubble.jsx`).
5. **Calculated values**: find out where DB-return totals are computed (template formula in `RLCBase.xls`, or SQL). Reuse `excel_eval` if the template formula applies; otherwise explain the rule alone.
6. **Switch**: `ERROR_IMPROVEMENT_DB=0` to turn the DB path off; falls back to the existing explanation like the Excel path.
7. **Tests**: unit tests with 2008/2009 metadata; the BT-key score as a regression gate.

## 4. Risks to settle first

- No DB access in the chatbot: a table row cannot be confirmed from a database. Check whether the data-prep step leaves an extract (2009 has `XML_Query_Excel.xml` and `XML_Query_Excel_DuckDB.xml`, which suggest an Excel/DuckDB staging) that can serve as the value check. Without it, results are tagged "mapped / inferred".
- Only 1 DB BTDetails file exists (4000, a decimal-format error, not a formula error). More are needed to measure accuracy.
- 2009 is missing from `inventory_RepoCore_5.5.csv` as data_prep; refresh the inventory.
- English only and 5.5 layout, as the engine today; 6.0 uses `TableMapping.xml` / `Return.xml`.

## 5. Test returns

Excel (5.5): 4046, then 4049, 4047, 4044 (see the chat answer for why).
DB (5.5): 2009 first; 4000 for the answer-key shape; 2008, 1038, 2037, 2052 as metadata-only tests.
