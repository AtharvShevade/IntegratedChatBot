# Formula & Dimension Error Explanation — Analysis and Implementation Plan

Status: **proposal, awaiting approval. No code changed yet.**

Everything below is derived from the real files under `D:\Repo(new)\` (`Instance\`,
`DataBase\<form_id>\Taxonomy\`, `JSON\<form_id>\`) and from running the current
parsers against those files. Every claimed defect in section G was reproduced,
not inferred.

---

## A. Current architecture

```
frontend ErrorSummaryPanel
   └── POST /explain-category            (backend/main.py)
        └── agent.explain_category_for_report          (backend/agent/__init__.py:3864)
             ├── report_lookup.count_errors_by_category(path, form_id)   → totals for "showing x-y of N"
             └── report_lookup.explain_errors_by_category_for_form(path, category, form_id, offset)
                  └── report_lookup.explain_errors_by_category           (report_lookup.py:3646)
                       ├── category == "formula_error"
                       │     ├── _is_4000_series(form_id) → parse_formula_errors
                       │     │        → enrich_formula_errors (sum/ratio discrepancy)
                       │     │        → explain_formula_errors  (taxonomy_lookup + Ollama)
                       │     └── else                 → formula_error_generic.explain_generic_formula_error_file
                       ├── category == "dimensional"  → parse_dimensional_html_errors
                       │                                → dimension_taxonomy.explain_dimensional_errors_taxonomy_aware
                       └── category == "xbrl_schema"  → parse_backtrack_html_errors → explain_validation_errors
```

Supporting modules:

| Module | Role |
|---|---|
| `backend/tools/report_lookup.py` (4.4k lines) | error-file discovery, all three parsers, 4000-series formula flow, counting, batching |
| `backend/tools/formula_error_generic.py` | the non-4000 formula flow (7-column table shape) |
| `backend/tools/dimension_taxonomy.py` | dimension-error explanation from definition linkbases + JSON |
| `backend/tools/taxonomy_lookup.py` | loads + indexes `JSON/<form_id>/*.json` by `assertion_id` / `concept_id` |
| `backend/config.py` | `instance_base_dir()`, `json_metadata_base_dir()`, `app_db_base_path()`, `_active_root()` |

**The single most important structural problem:** the fork between the two
formula flows is `_is_4000_series(form_id)` — a numeric range check on the
form id (`4000 <= int(form_id) <= 4999`). It is a proxy for "does this error
file have backtracking columns", and the proxy is **wrong in both directions**
against the real corpus (see section C).

---

## B. Findings from the Instance folder

I profiled all 43 files under `D:\Repo(new)\Instance\` (23 return folders).

### B.1 Two physically different error-file products

| Product | Filename pattern | Example folders | Formula table shape |
|---|---|---|---|
| **Validation output** | `*_Instance.html` | 2014, 2029, 2036, 2040, 2041, 2042, 2047, 2065, 4005, 4012, 4020, 4038, 4044, R162, R376, R380 | 7 columns: `Variable, Name, Value, Context, Unit, Decimal, Precision` |
| **Backtracking details** | `*_BTDetails.html` | 4038, 4040, 4046, 4080 | 11 or 12 columns: `DB TableName, [Cell Index,] Table Header, Column Label(s), Variable Id, Row Label(s), Instance Data(s), Entered Data(s), Unit, Decimal, Context, Cell Code` |

Both products share the same outer skeleton — three Bootstrap tabs
(`FORMULA_ERROR` id=1, `QUALITY-CHECK_ERROR` id=2, `SPECIFICATION_ERROR` id=3) —
but differ in every detail that matters:

* **Panel ids differ:** `errorPanelN` (validation output) vs `formulaErrorPanelN`
  (BTDetails). `formula_error_generic._split_error_panels` splits on
  `id="errorPanel` only, so it returns **zero panels** for any BTDetails file.
* **Accordion id differs when empty:** `id="accordionFormula"` when formula errors
  exist, `id="accordion"` when none do. This is a reliable emptiness signal.
* **Header row count is not fixed** even within BTDetails: 4040/4046 CREDITHAB
  files add a `Cell Index` column that 4038/4046/4080 IDIB files do not have.
  Any positional column mapping is unsafe; header-driven mapping is mandatory.
* **XML-only error files exist** (2001, 2027, 2033 — `XBRLError_*.xml`,
  `<ErrorMessage>` elements). No formula/dimension structure at all.

### B.2 SPECIFICATION_ERROR tab panels

The spec tab contains up to 21 sibling panels, each with its own badge:
`XBRL_SCHEMA, XBRL, IXBRL_SCHEMA, GENERIC_SCHEMA, IXBRL, dimention, formula,
table, ext_enumeration, usgaap, fris, frta, utr, esef, xpkg, rpkg, xbrlcsv,
xbrljson, xbrlxml, calculation, CUSTOM_RULE`.

Note the id casing/spelling inconsistency that any parser must tolerate:
panel div is `id="dimentionPanel"` (sic) in validation output but
`id="DIMENSIONPanel"` in BTDetails; the badge is `id="DIMENSIONErrorNum"` in
both; the body is `id="DIMENSIONErrorContent"`.

**All spec panels use the same `<td class="directMsg">` markup.** They are only
distinguishable by panel boundary. A regex that grabs `directMsg` cells without
first bounding the DIMENSION panel silently returns TABLE-panel warnings as
"dimension errors" — I reproduced exactly that while surveying (2036 reported
42 "dimension messages" when its DIMENSION badge is 0 and its TABLE badge is 42).
`report_lookup` gets this right today via the badge gate; the replacement must
keep the gate and additionally bound by panel.

### B.3 Formula error inventory

| Folder | Rules | Notable shapes |
|---|---|---|
| 2065 | 8 | `$V1 >= $V2`, `$V1 > $V2`, `$V1 = $V2`, `$V1 <= $V2 + $V3` |
| 2041 | 9–11 | comparisons with label text containing `-`, `(`, `,` |
| 2042 | 11 | |
| 4044 | 7 | `$V1 = sum ( $V2 )`, `$V1 = $V2 + $V3 - $V4` |
| 4012 | 2 | |
| R162 | 11–12 | `round($V1 * 10) div 10 = round(($V2 + $V3 - $V4) * 10) div 10` |
| R376 | 4 | |
| 4038 BTDetails | 3 | `round($V1 div 1000) * 1000 = round((sum ($V2)) div 1000) * 1000`, `not(empty($V1))` |
| 2036, 2040, 4005, 4020, R376/DOHB | 0 | `id="accordion"` — empty formula tab |

Operator/expression features actually present in the corpus:
`=`, `>`, `>=`, `<`, `<=`, `+`, `-`, `*`, `div`, `sum(...)`, `round(...)`,
`not(empty(...))`, nested parentheses, and **multiple facts bound to the same
variable id** (three `V2` rows under one `sum($V2)`).

### B.4 Business-message conventions (there are three, not one)

```
"en:Identity "<lhs> <op> <rhs>" do not tally."                     ← 2065, 2041, R162
"en:Validation not satisfied: <lhs> = <rhs>"                        ← 4044
"en:Identity " Value of X (X = Sum of all its child elements )" do not tally."  ← 4038 BT
"en:Reporting of " 'Dates for Half Month" is mandatory."            ← 4038 BT presence check
```

Messages contain **nested and unbalanced quotes**, HTML entities (`&lt;=`,
`&gt;=`, `&amp;`), and free text containing `(`, `)`, `+`, `-`, `=`, `/`.
This is the direct cause of the corruption in section G.

### B.5 Dimension error inventory

Only two `xbrldie` classes appear in the whole corpus, but the parser must not
assume that is the closed set (the xbrldie family also defines
`TypedMemberNotTypedDimensionError`, `ExplicitMemberNotExplicitDimensionError`,
`DefaultValueUsedInInstanceError`, `RepeatedDimensionInInstanceError`).

| Class | Count | Files |
|---|---|---|
| `xbrldie:PrimaryItemDimensionallyInvalidError` | 96 | 2047 (23), 4012 (12), R376 ×3, 4038/4046/4080 BTDetails |
| `xbrldie:IllegalTypedDimensionContentError` | 96 | 2047/SURY (2), 4012 (1), R376/DOHB, R376/SHBK |

Two message layouts for the attribute tail:

```
… as per the dimensional relationship defined in the taxonomy.
   name = X value = Y context = Z unit = decimal = precision =         ← validation output
… as per the dimensional relationship defined in the taxonomy.|
   @name = X @value = Y @context = Z @unit = INR @decimal = -5 @precision =   ← BTDetails
```

Always available: `error_class`, `section_ref`, `concept` (primary-item class only),
`context`, `Error Code`, `LineNo`, `ColumnNo`.
Optional: `value` (may contain spaces — `2. In ATM`), `unit`, `decimal`,
`dimension` + quoted invalid value (typed class only), `FileName`.
Never present: allowed members, dimension type, hypercube membership — those
only exist in the taxonomy.

**No dimension error anywhere in the corpus has a backtracking table.** Even
inside BTDetails files, the DIMENSION panel is plain `directMsg` rows. Dimension
backtracking simply does not exist in this product today; the design must not
pretend otherwise, but must detect it structurally in case it appears later.

---

## C. 4000-series backtracking findings

**Backtracking is a property of the individual error file, never of the return.**
Evidence from the corpus:

| form_id | file | 4000-series? | backtracking columns present? |
|---|---|---|---|
| 4038 | `IDIB…_BTDetails.html` | yes | **yes** (11 cols) |
| 4040 | `CREDITHAB…_BTDetails.html` | yes | **yes** (12 cols, XBRL_SCHEMA panel) |
| 4046 | `CREDITHAB…_BTDetails.html` | yes | **yes** (12 cols) |
| 4080 | `IDIB…_BTDetails.html` | yes | **yes** (11 cols) |
| 4044 | `SMCB…_Instance.html` | yes | **no** — plain 7-column table |
| 4012 | `ABPL…_Instance.html` | yes | **no** |
| 4005, 4020 | `_Instance.html` | yes | **no** (no formula errors at all) |
| 4038 | `ABPL…_Instance.html` | yes | **no** |
| 2065, 2041, R162, R376 … | `_Instance.html` | no | **no** |

So `_is_4000_series(form_id)` mis-routes **4044, 4012, 4005, 4020 and 4038's
`_Instance.html`** into the backtracking flow. Reproduced consequence on 4044:

```
var: '"V2'   ← leading quote left in place by the 4000-series parser
             (the generic parser strips it) → every downstream $V2 lookup misses
```

### Dynamic detection

Detect per-file, per-panel, from the header row — no id and no form-id range:

```python
_BT_HEADER_TOKENS = {"db tablename", "cell code", "variable id",
                     "instance data(s)", "entered data(s)", "row label(s)"}

def _table_has_backtracking(header_cells: list[str]) -> bool:
    """>=2 of the DB-backtracking header labels present in this table's own
    <th> row. Structural — no return id, no filename, no panel id."""
    seen = {h.strip().lower() for h in header_cells}
    return len(seen & _BT_HEADER_TOKENS) >= 2
```

This decides *per table block*, which is what the data actually supports:
one file can in principle mix panels (4040 already has backtracking on an
`XBRL_SCHEMA` panel and none anywhere else). The flag then drives *enrichment*,
not *routing*: one parser, one explainer, with `db_table` / `row_label` /
`cell_code` / `entered_value` populated when available and absent when not.

Also worth recording: `Entered Data(s)` vs `Instance Data(s)` is a genuinely
new fact backtracking adds — 4038 shows `13459.2420` entered vs
`134592420000` in the instance (a ×10⁷ scale factor). That belongs in the
explanation ("you typed 13,459.2420 in cell Y250_X030") and is the strongest
user-facing benefit of backtracking. It is currently parsed and then dropped.

---

## D. Formula error architecture (HTML + Taxonomy + JSON + Backtracking + LLM)

Six deterministic stages, then one LLM stage that can only rephrase.

```
1. LOCATE      error file → detect product/shape
2. EXTRACT     panels → rules → instances → variable FACTS (list, not dict)
3. PARSE       formula expression → expression AST (operator, side ASTs, rounding)
4. RESOLVE     variable id → business label, via a ranked source cascade
5. EVALUATE    AST + facts → lhs, rhs, difference, relationship, passes
6. LOCATE-DATA backtracking row / JSON db_mapping → "where to check"
7. PHRASE      LLM, given only stages 3–6 output; grounding-checked; else template
```

### Stage 2 — one parser, shape-tolerant

Replace the two divergent parsers with one:

* panel split on `id="errorPanel\d+"` **or** `id="formulaErrorPanel\d+"`, plus a
  class-based fallback (`panel panel-default` containing `assertionLabel`);
* per-table `<th>` header capture → column-name mapping (union of both header
  maps, since header names are unambiguous across shapes);
* `.strip().lstrip('"')` on every cell, uniformly;
* **facts as a list, not a dict.** Today `{v["var"]: v for v in variables}`
  collapses the three `V2` rows of `$V1 = sum($V2)` to the last one — 4044's
  `sum($V2)` over `[177, 14, 3]` currently evaluates as `3`. Model as
  `facts: list[Fact]` and `facts_by_var: dict[str, list[Fact]]`.

### Stage 3 — a tiny expression parser, not keyword classification

`_classify_formula_type` (keyword sniffing: contains `+` → sum_check, contains
`round` → ratio) cannot represent `round($V1 * 10) div 10 = round(($V2 + $V3 -
$V4) * 10) div 10`. Build a recursive-descent parser over the actual grammar
present in the corpus:

```
expr    := cmp
cmp     := add ( ('='|'!='|'<>'|'>='|'<='|'>'|'<') add )?
add     := mul ( ('+'|'-') mul )*
mul     := unary ( ('*'|'div'|'idiv'|'mod') unary )*
unary   := '-'? primary
primary := NUMBER | '$'VAR | FUNC '(' args ')' | '(' expr ')'
FUNC    := sum | round | abs | min | max | not | empty | count | number
```

Evaluate with `Decimal`. `sum($V)` folds over **all** facts bound to `$V`;
a bare `$V` with several facts also folds (that is what the validator does) but
records `fact_count` so the renderer can say "3 daily values". Unsupported node
→ return `None` and fall through to the evidence-only rendering; never guess.

This one change makes `>`, `<`, `>=`, `<=`, `=`, `!=`, `+`, `-`, `*`, `div`,
rounding, nesting and multi-variable formulas work by construction, with no
per-formula code.

### Stage 4 — label resolution cascade (this is where the corruption dies)

Ranked, first hit wins, each source independently verifiable:

1. **JSON** `validation_rules[assertion_id].variables[].concept_id` →
   `concepts[].label`. Exact, authored, per-variable. Available for 2065, 4046,
   4080 today.
2. **Label linkbase** — `DataBase/<…>/Taxonomy/**/*label*.xml`, keyed by the
   variable's own `Name` cell from the HTML. Verified working for 2047
   (`PlaceOfOccurence` → "Place of occurence"). **This source exists for every
   return in the repo and is currently unused.** It is the reason the JSON's
   absence does not have to hurt.
3. **Backtracking row labels** — `Row Label(s)` + `Table Header` + `Cell Code`
   from the BT table (e.g. `Y250` / "Table 2 - Cash Reserves with RBI").
4. **Message-derived operand split** — kept, but only as a *fallback* and only
   after being made safe (below).
5. **CamelCase-humanised `Name` cell** — last resort.

Message parsing is rewritten to be quote-aware rather than prefix-stripping:

* unescape entities **first** (`&lt;=` → `<=`) — today `_clean_text` unescapes
  but the operator split then runs on text that may still contain `&gt;`;
* strip a *known set* of leading wrappers structurally:
  `▼`, `en:`, `Identity`, `Validation not satisfied:`, `Reporting of`;
* strip the trailing `do not tally.` / `is mandatory.` clause **before** any
  operand split, including when it is preceded by a stray `"` or `)`;
* extract the innermost balanced-quote span when the message is
  `Identity "…"` — quote-balance scanning, not `strip('"')`;
* **only accept a split when the operand count matches the AST's variable
  count on that side.** `Provisions (excluding Floating Provisions) ( = Sub-standard
  + Doubtful + Loss for the previous year.)` has 3 RHS variables and splits into
  3 parts → accept. `Closing balance … ( = Opening + Fresh - Excess …)` splits
  into 2 `+`-parts for 3 variables → **reject the whole split** and fall back to
  the taxonomy label, instead of today's behaviour of assigning the entire
  remaining string (including `" do not tally.`) to V4.
* delete `_disambiguate_labels`' member-suffix heuristic in its current form —
  it produced `… (BeginningBalance)` glued onto a sentence. Disambiguate only
  when the two labels came from the *same* source and the context tokens differ,
  and render the hint as a separate parenthetical column, not inside the label.

### Stage 6 — "where to check"

* backtracking present → `DB TableName` + `Cell Code` + `Row Label` + entered value;
* else JSON `db_mapping.status == "confirmed_by_internal_metadata"` →
  `table.column (code N)` via existing `taxonomy_lookup.format_db_location`;
* else omit the section. Never synthesise a location.

### Output shape

Matches the format requested in the brief:

```
⚙ Formula Error — <assertion label>

❌ <one-line failure>

**Validation rule:** <plain-English restatement built from the AST + labels>

**Reported values:**
- <label>: ₹…            (+ "entered as 13,459.2420 in cell Y250_X030" when BT)
- <label>: ₹…

**Calculated/combined value:** ₹…
**Difference:** ₹…
**Why it failed:** …
**Where to check:** …            (omitted when unresolvable)
**How to fix:** …
```

---

## E. Dimension error architecture (HTML + Taxonomy + Instance + LLM)

```
1. EXTRACT   DIMENSION panel (badge-gated AND panel-bounded) → per-error facts
2. IDENTIFY  error_class → strategy
3. LOCATE    the taxonomy that this filing actually used
4. RESOLVE   dimension identity + type + allowed values, from the taxonomy
5. OBSERVE   what the filing actually reported (instance XML when co-located)
6. DIFF      expected vs reported
7. PHRASE    LLM over the structured diff only
```

### Stage 1 — fix the attribute tail parser

The current `\b(name|value|context|…)\s*=\s*(\S+)` is wrong twice, both reproduced:

* `value = 2. In ATM context = …` → captures `2.` (value truncated at the space);
* `unit = decimal = precision =` (empty unit) → captures `unit = "decimal"`,
  and loses `decimal` entirely. 2047's parsed errors literally carry `unit: 'decimal'`.

Replace with a **key-boundary scan**: tokenise on the known key set
(`@?(name|value|context|unit|decimal|precision|dimension|typeDomainRefSchema|
typeDomainRefInstance)\s*=`) and take each value as *everything up to the next
key or end of string*, trimmed, possibly empty. This handles values with spaces
and empty values correctly, and is identical for the `@`-prefixed BTDetails form.

### Stage 3 — taxonomy location (the current blocker)

`dimension_taxonomy._find_definition_linkbases` searches for
`*<stem>*-definition.xml`. 2047's definition linkbase is
`DataBase/2047/Taxonomy/fmr4cfmc/in-rbi-rep-fmr4_def1.xml` — it does not match,
so **every one of 2047's 23 dimension errors currently falls through to the
"Cannot be determined" template** (reproduced). Meanwhile 4038's own
`DataBase/4038/Taxonomy` holds `mpd07`, while its BTDetails file is an `mpd03`
filing — so form_id → taxonomy folder is not reliable either.

Replace with a ranked, evidence-based resolver:

1. **schemaRef from the co-located instance XML.** `Instance/<form_id>/<base>.xml`
   sits next to `<base>.html` for 2047 and 2033. `<link:schemaRef xlink:href='in-rbi-rep-fmr4.xsd'>`
   names the entry point exactly. Strongest signal when present.
2. **JSON `return_metadata.entry_point_path`** when `JSON/<form_id>/` exists.
3. **Filenames referenced inside the error file** (`<code>-table.xml`,
   `<code>-formula*.xml` in TABLE/FORMULA panel messages) — keep the existing heuristic.
4. **Content-based discovery** under `DataBase/<form_id>/Taxonomy/**` and then
   repo-wide: any `.xml` whose content contains `hypercube-dimension` or
   `dimension-domain` arcroles is a definition linkbase regardless of filename.
   Index once per taxonomy folder (concept local name → files declaring it) and
   cache by folder mtime.

Rank candidates by: declares the concept in question > co-located with the
resolved entry point > under `DataBase/<form_id>/` > alphabetical. Record the
chosen path in `_dimension_evidence` so a wrong pick is diagnosable.

### Stage 4 — typed vs explicit, done properly

This is the concrete win for `IllegalTypedDimensionContentError`. Chain, verified
by hand on 4012 and 2047:

```
axis local name from the message      DateAxis
  → <xsd:element name="DateAxis" … xbrldt:typedDomainRef="in-rbi-rep-par.xsd#in-rbi-rep-par_DateDomain">
  → in-rbi-rep-par.xsd  element DateDomain → <xsd:restriction base="xsd:date"/>
  ⇒ the axis requires an xs:date, e.g. 2018-11-12
```

```
DateAndTimeOfOccurrenceTypeAxis → DateAndTimeOfOccurrenceTypeDomain
                                → <xsd:restriction base="xsd:dateTime"/>
  ⇒ requires 2023-10-23T12:51:00
```

Presence of `xbrldt:typedDomainRef` on the axis element *is* the typed/explicit
test — authoritative, and better than today's inference from "the JSON says
is_typed" or "the hypercube entry has no members". For explicit axes, walk
`dimension-domain` → `domain-member` for the allowed member list, and read the
member labels from the label linkbase.

So the typed-dimension explanation becomes:

> **Dimension:** Date [axis] — typed dimension
> **Required value:** a date (`xs:date`, e.g. `2018-11-12`)
> **Reported:** `12112018`
> **Why invalid:** `12112018` is not a valid `xs:date`; it looks like a
> DDMMYYYY value that was not converted to ISO format.

instead of today's "does not match the value pattern used by other facts in this
same filing".

### Stage 5 — what was actually reported

Today `typed_dim_value` is set to the **context id**, because the validator's
message quotes the context id in the `Value '…' provided` slot. That is why 4012
reports the reported value as
`asof_20220331_12112018_AABCW3241P_WELSPUNENTERPRISESLIMITED_FluctuationOfPriceAndFreightRiskMember`.

When the co-located instance XML exists, read the real answer directly:

```xml
<xbrli:context id='fromto_20231001_20231231_0510003_20231023T125100_OOOOOOOO9'>
  <xbrldi:typedMember dimension='in-rbi-rep:DateAndTimeOfOccurrenceTypeAxis'>
    <in-rbi-rep-par:DateAndTimeOfOccurrenceTypeDomain>2023-10-23T12:51:00</…>
```

Verified: the failing context ids from 2047's error file (including
`…_OOOOOOOO9`) are all present in `2047/…_Instance.xml`, and give the exact
axis→value map for both typed and explicit members. When there is no instance
XML, fall back to the context-id suffix as a *labelled guess*
("the context's trailing segment is `12112018`"), never as a stated fact.

### Stage 6 — the diff, per class

| class | expected (taxonomy) | reported (instance/context) | verdict |
|---|---|---|---|
| `PrimaryItemDimensionallyInvalidError` | axes required by the concept's hypercube + allowed members, `closed` flag | axes actually on the context | missing axis / extra axis / member not in domain |
| `IllegalTypedDimensionContentError` | typed domain's XSD base type (+ pattern/enumeration facets when present) | typed member's text | value fails the type |
| unknown `xbrldie:*` | whatever resolved | whatever resolved | generic, honestly labelled |

Only the diff — never the raw taxonomy — is handed to the LLM.

### Backtracking for dimension errors

Detected the same structural way as for formula errors (does this panel's table
carry BT header tokens?). Today the answer is always "no" for DIMENSION panels
in every file in the corpus, so the code path stays dormant, but it costs
nothing and is not a special case.

---

## F. JSON 2065 analysis, and generalisation

`JSON/` currently holds **three** files, not one: `2065/in-rbi-raq_2012-08-31 (1).json`
(3.7 MB), `4046/mpd03-entry-n_1.0.0.json` and `4080/mpd03-entry-n_1.0.0.json`
(89 KB, identical). All three share one schema:

```
return_metadata   return_code, taxonomy_version, title, entry_point_path,
                  namespace, extraction_timestamp, arelle_version,
                  linkbase_generation_detected{presentation,calculation,definition,…}
structure.tables  [{table_id, label, classification, classification_reasons, concept_count}]
structure.axes    [{axis_id, label, is_typed, domain_id, members[{member_id,label}], tables[]}]
concepts          [{concept_id, label, documentation, data_type, period_type, balance_type,
                    abstract, substitution_group,
                    importance{is_core,score,reasons},
                    presentation{tables,depth}, calculation,
                    formula_participation[{assertion_id, role, variable_name}],
                    dimensional_context_required[{axis_id, db_mapping}]}]
validation_rules  [{assertion_id, source_file, assertion_type, test_expression,
                    message, message_lang, severity,
                    variables[{name, concept_id, dimensional_qualification[], db_mapping}]}]
unmapped_summary  {concepts_without_presentation, concepts_without_labels, orphan_axes, …}
semantic_description / semantic_tables   ← null in all three files
```

What it gives that nothing else does, cheaply:

* `validation_rules[].test_expression` — the formula **as authored**, independent
  of the HTML's rendering, so the AST can be built from a clean source and
  cross-checked against the HTML's.
* `validation_rules[].variables[].name → concept_id` — the exact V-id → concept
  binding. The HTML's `Name` column gives a concept too, but the JSON also gives
  `dimensional_qualification` (e.g. `AssetClassificationAxis=PerformingAssetsMember`),
  which is what distinguishes V2 from V3 when both are the same concept.
* `concepts[].formula_participation[].role` — `lhs_total` / `rhs_variable` /
  `variable`. Directly answers "which side is the total".
* `db_mapping` — DB location without a backtracking file.
* `structure.axes[].is_typed` + `members` — a second opinion on dimension type.

Quality caveats measured, not assumed:

| | 2065 | 4046/4080 |
|---|---|---|
| rules | 346 (330 value, 16 existence) | 29 (24 value, 5 existence) |
| variables | 1075 | 57 |
| with `concept_id` | 539 (50.1 %) | 57 (100 %) |
| `db_mapping` confirmed | 539 | 57 |
| `db_mapping` unmapped | 536, reasons: `no_concept_id_on_variable`, `ambiguous_mapping_row_for_dim_dom_id`, `axis_not_in_winning_prelnkbase` | 0 |
| `semantic_description` | null | null |

So **2065's JSON is half-unmapped**, and the unmapped half is exactly the
dimensionally-qualified variables (`concept_id: null`, but
`dimensional_qualification` present). Consequences for the design:

* JSON is a **preferred enrichment, never a precondition**. Per-variable, not
  per-rule: use the JSON label for V1 and the label linkbase for V2 in the same
  rule if that's what the data supports.
* When `concept_id` is null but `dimensional_qualification` is not, we can still
  produce a good label: humanise the member (`PerformingAssetsMember` →
  "Performing Assets") and combine with the HTML's own `Name` cell. This is
  strictly better than what either source alone gives.
* Match rules by `assertion_id == rule_name`, with a normalised fallback
  (case-insensitive, `-`/`_`/`.` collapsed) because HTML assertion labels and
  JSON assertion ids drift.
* Version-guard: compare `return_metadata.taxonomy_version` / `namespace`
  against the taxonomy actually resolved in section E stage 3; on mismatch,
  demote the JSON to "labels only" and log it.

Generalisation path (out of scope for the code change, but the plan should say
it): the JSON is an Arelle extraction (`arelle_version: 2.42.1`) driven by the
entry-point `.xsd`. Producing it for another return is running the same
extractor against `DataBase/<form_id>/Taxonomy/**/<entry>.xsd`. The runtime must
therefore treat `JSON/<form_id>/` as an optional, growing cache — which
`taxonomy_lookup` already does correctly (mtime-checked, fails soft). No change
needed there beyond adding the by-`variable_name` and by-`axis_id` indexes.

---

## G. Why the current parsing corrupts text — reproduced

All of the following were produced by running the shipped code against the real
files, not by reading it.

**G.1 `do not tally.` leaking into concept names** — R162, rule
`DSIM01-AssetQuality-TotalNPA-ProvisionHeld-PreviousYear`:

```
labels = {'V1': 'Provisions (excluding Floating Provisions) (',
          'V2': 'Sub-standard',
          'V3': 'Doubtful',
          'V4': 'Loss for the previous year.)" do not tally.'}
```

Cause: `_clean_business_message` strips a *trailing* `do not tally.` only when
it is the last thing in the string. Here the message is
`… Loss for the previous year.)" do not tally. "` — trailing space + quote, so
the anchor fails; then `extract_operand_labels_from_message` splits on `=` and
hands the remainder to `_split_summed_labels`, which splits on ` + ` into 3
parts for 3 RHS vars and accepts.

**G.2 `Identity ""…` / truncated LHS** — R162, `TotalNPA-ClosingBalance_PY`:

```
'V1': 'Total NPA - Closing Balance" or "Total - Closing Balance" ('
```

Cause: the message contains internal quoted phrases; `strip('"')` only removes
outer quotes, and the split on `=` lands inside the parenthetical.

**G.3 The `(BeginningBalance)` suffix** — `_disambiguate_labels` appends
`_CONTEXT_MEMBER_RE` tokens from the context id to a label that is already a
full sentence:

```
'V2': 'Opening balance … do not tally. (BeginningBalance)'
```

**G.4 `Validation not satisfied:` never stripped** — 4044:

```
'V1': 'Validation not satisfied: Complaints pending at the end of the period for 1. Ground alleging…'
```

`_clean_business_message` only knows the `Identity` convention.

**G.5 Wrong arithmetic — subtraction treated as addition.** `evaluate_comparison`
does `sum(rhs_raw)` for `rhs_vars`, so `$V1 = $V2 + $V3 - $V4` computes
`V2+V3+V4`. Every reported "Difference" for such a rule is wrong.

**G.6 Wrong arithmetic — duplicate facts collapsed.** `var_by_id = {v["var"]: v …}`
keeps the last row only, so 4044's `$V1 = sum($V2)` over `[177, 14, 3]` compares
`0` against `3` instead of `194`.

**G.7 Rounding silently ignored.** `_ROUND_DIVISOR_RE` matches `round(x div N)`
only, so R162's `round($V1 * 10) div 10` yields `rounding_divisor: None` and the
comparison runs unrounded — producing spurious failures/passes on values that
differ below the rounding threshold.

**G.8 Stray `"` on variable ids in the 4000-series parser** — 4044 yields
`var: '"V2'`, so no `$V2` in the formula ever matches a fact.

**G.9 Dimension attribute truncation and shifting** — 2047 yields
`value: '2.'` (should be `2. In ATM`) and `unit: 'decimal'` (should be empty).

**G.10 Panel bleed.** `_extract_dimension_panel_html` closes on the first
`</div>`; combined with `directMsg` being shared markup, an unbounded scan
attributes TABLE-panel warnings to DIMENSION. Currently masked by the badge
gate, but the gate is the only thing preventing it.

**G.11 Count/explain parser mismatch.** `count_errors_by_category` picks its
formula parser by `form_id`, but `form_id` is optional; when absent it counts
with `parse_formula_errors` and explains with the same, while a caller that does
pass a non-4000 form_id counts with the generic parser. On 2065 the two parsers
disagree (9 vs 8 rules), so "showing 1-3 of 9" can be off by one rule.

---

## H. LLM strategy

**Deterministic, never the LLM:** parsing, arithmetic, the pass/fail verdict, the
relationship (`lhs_greater`/`equal`/`less`), rounding, label resolution, DB
locations, allowed-member lists, typed base types, error counts.

**LLM, always:** the prose in `Why it failed` and `How to fix`, and nothing else.

The existing `explain_generic_context_via_llm` + `_llm_output_is_grounded` pair is
the right pattern and should be generalised rather than rewritten. Payload shape:

```jsonc
// formula
{ "operator": "=", "operator_meaning": "equal to",
  "relationship": "lhs_less", "relationship_meaning": "… is actually LESS than …",
  "lhs": {"label": "…", "value": "4", "fact_count": 1},
  "rhs_terms": [{"label":"…","value":"177","sign":"+"}, …],
  "rhs_total": "194", "difference": "-190",
  "rounding": {"mode":"nearest","divisor":1000},
  "unit": "INR", "instance_count": 3,
  "where": {"table":"CIMS_MPD03_CRR_LAYOUT3_HM","cell":"Y250_X030","entered":"13459.2420"} }

// dimension
{ "error_class": "xbrldie:IllegalTypedDimensionContentError",
  "concept": {"id":"…","label":"…"},
  "dimension": {"id":"in-rbi-rep:DateAxis","label":"Date [axis]","kind":"typed",
                "expected": {"base_type":"xs:date","example":"2018-11-12","facets":[]}},
  "reported": {"source":"context_id_suffix","value":"12112018"},
  "mismatch": "not_a_valid_xs_date",
  "evidence": {"taxonomy_file":"…in-rbi-rep.xsd","instance_xml_used":false} }
```

Grounding gate, extended from the existing one and applied to both categories:
every label must appear verbatim; no `V\d+` tokens; no number not present in the
payload (regex-scan all numerics in the output against a whitelist built from
the payload); no directional wording contradicting `relationship`; for dimension,
no member name not in the payload's allowed list. Failure → deterministic
template. Concurrency and timeouts reuse the existing
`OLLAMA_MAX_CONCURRENCY`-bounded `ThreadPoolExecutor`.

---

## I. File / code changes

New:

| File | Purpose |
|---|---|
| `backend/tools/error_file_shape.py` | detect product/shape/panels/backtracking from an error file; single source of truth for "does this file/table have backtracking" |
| `backend/tools/formula_expression.py` | the expression grammar parser + `Decimal` evaluator (pure, no I/O) |
| `backend/tools/message_cleaner.py` | quote-balanced business-message normalisation + operand splitting with arity validation |
| `backend/tools/taxonomy_index.py` | filesystem-level taxonomy resolution + caches: entry point → schema set, concept → label, axis → typed/explicit + domain + members + XSD base type, concept → hypercube |
| `backend/tools/instance_context.py` | optional: co-located instance XML → `{context_id: {axis: value, kind}}` |

Modified:

| File | Change |
|---|---|
| `backend/tools/formula_error_generic.py` | becomes **the** formula flow: shape-tolerant parsing, list-of-facts model, AST evaluation, cascade label resolution, BT enrichment. Likely renamed `formula_error.py` with the old name kept as a shim. |
| `backend/tools/report_lookup.py` | `explain_errors_by_category`: drop the `_is_4000_series` fork, call the unified flow. `count_errors_by_category`: use the same parser as the explainer, unconditionally. `_parse_dimension_panel_direct_msg`: key-boundary attribute scan. `_extract_dimension_panel_html`: balanced-div panel bounding. `parse_formula_errors` / `_parse_formula_errors_regex_fallback` / `_classify_formula_type` / `_compute_*_discrepancy` / `_render_*_detailed`: retired once the unified flow is at parity (they are ~900 lines). |
| `backend/tools/dimension_taxonomy.py` | keeps its role and its evidence-dict discipline; swaps `_find_definition_linkbases` for `taxonomy_index`, adds the typed-domain XSD chain, adds the instance-XML observation stage, adds the LLM phrasing stage behind the same grounding gate. |
| `backend/tools/taxonomy_lookup.py` | add `by_variable_name(assertion_id)`, `by_axis_id`, normalised assertion matching, version guard. Existing API unchanged. |
| `backend/agent/__init__.py` | no logic change; `_CATEGORY_DISPLAY` and the batching contract stay. |

Explicitly **not** changed: `main.py` routes, `models.py` schemas, the
frontend's `**Label:** value` section renderer, batch size, offset semantics.

Rollout: build the unified flow behind `ERROR_EXPLAIN_V2` (default off), run the
golden-file comparison in section J against both flows, then flip the default and
delete the legacy path in a follow-up.

---

## J. Testing strategy

A golden-file harness over the real corpus, `backend/tests/test_error_explanation_corpus.py`,
parameterised over every file in `Instance/`. Fixtures are the files themselves;
no synthetic HTML except for the malformed cases.

**Structural / no-hardcoding tests**

1. Shape detector: BT expected for the four `*_BTDetails.html`; not expected for
   every `*_Instance.html`, including 4038/4044/4012/4005/4020 — asserts the
   4000-series proxy is gone.
2. Assert no return id, assertion name, concept name or dimension name appears
   as a literal in `backend/tools/*.py` (grep test over the corpus vocabulary).
3. Header-driven mapping: 11-col and 12-col BT headers both map correctly;
   shuffled header order still maps correctly.

**Formula**

4. 4038 BT: `TotalOfAverageCashReserves` — 14 `V2` facts summed, rounding to
   nearest 1000 applied, `Entered Data(s)` surfaced, DB table + cell code present.
5. 4038 BT: `DatesForFortnightToBeReported` — `not(empty($V1))`, no variables,
   renders a presence-check explanation and does not crash.
6. 4044: `$V1 = sum($V2)` over `[177,14,3]` ⇒ rhs 194, difference −194 (regression
   for G.6); `var` ids have no stray quote (G.8).
7. 4044: `$V1 = $V2 + $V3 - $V4` ⇒ signed evaluation (regression for G.5).
8. R162: `round($V1*10) div 10 = round(($V2+$V3-$V4)*10) div 10` ⇒ rounding applied
   (G.7), and no label contains `do not tally`, `Identity`, `"` or a trailing `(` (G.1–G.3).
9. 2065: all 8 rules; the 149-instance rule reports 149 and explains the first.
10. Operator matrix: `= ≠ > >= < <=` × {lhs greater, equal, less} — every cell
    produces a sentence consistent with the computed relationship (property test).
11. Missing/zero/non-numeric values (`"6,032"` as seen in 4044's FORMULA panel,
    `#DIV/0!`, `NA`, `3.3E-05` as seen in R162/4020) ⇒ evaluation returns `None`
    and the evidence-only rendering is used; never a fabricated number.
12. Empty formula tab (2036, 2040, 4005, 4020, R376/DOHB) ⇒ 0 rules, no exception.
13. Count/explain agreement: `count_errors_by_category(path, form_id)` equals
    `len(parse(path))` for every file and for `form_id=""` (regression for G.11).

**Dimension**

14. 2047 (23 primary-item): dimension resolved for ≥1 error — i.e. the taxonomy
    at `fmr4cfmc/in-rbi-rep-fmr4_def1.xml` is found (regression for the current
    100 % "Cannot be determined").
15. 2047: `value == "2. In ATM"` and `unit == ""` (regression for G.9).
16. 2047/SURY + 4012 + R376 (typed): dimension type is `typed`, expected base type
    resolved (`xs:dateTime` / `xs:date`), reported value is **not** the context id.
17. 4012 (multi-axis primary item): all three axes named, allowed members listed
    for the explicit ones, typed one described as typed.
18. 2036 / 2040 / 2041 / 2042 / 2065 (DIMENSION badge 0, TABLE badge > 0):
    parser returns `[]` — panel-bleed regression (G.10).
19. 4038/4046/4080 BTDetails: identical file in three folders ⇒ identical
    explanation regardless of form_id, proving form_id isn't load-bearing.
20. Instance-XML enrichment: with `2047/…_Instance.xml` present the axis→value map
    is used; with the file hidden the explanation degrades to the labelled
    context-suffix guess and never asserts a value.

**JSON**

21. 2065 (JSON present, 50 % unmapped): per-variable fallback — mapped variables
    get the JSON label, unmapped ones get the label linkbase/message label.
22. 4046/4080 (JSON present, 100 % mapped): DB location rendered from `db_mapping`.
23. 2047, 4012, R162, R376 (no JSON): full explanation still produced; assert the
    "Where to check" section is absent rather than invented.
24. Corrupt/truncated JSON, and a JSON whose `taxonomy_version` disagrees with the
    resolved taxonomy ⇒ demoted to labels-only, logged, no exception.

**Malformed / adversarial**

25. Truncated HTML mid-`<table>`; a panel with a header row and no `fv` rows; a
    badge with non-numeric text; `<td>` count ≠ header count; duplicated
    `errorPanel` ids; XML-only error file (2001, 2027, 2033); zero-byte file;
    missing file. All ⇒ graceful degradation, never a traceback.

**LLM**

26. Grounding gate unit tests: outputs that invent a number, drop a label, use
    `V2`, or contradict `relationship` are rejected and the deterministic template
    is used. Run with the LLM stubbed — the corpus suite must pass with Ollama
    unavailable.

---

## K. Risks and edge cases

1. **Retiring the 4000-series path is the main risk.** ~900 lines of
   `report_lookup.py` currently serve real users. Mitigation: feature flag +
   golden-file diff of every explanation before/after on all 43 files, reviewed
   by hand for the ~30 rules that change.
2. **Wrong taxonomy chosen.** Taxonomy folders are reused across returns (4038
   holds mpd07 while its error file is mpd03) and several returns share
   `core/in-rbi-rep.xsd`. A wrong pick yields a confidently wrong member list.
   Mitigation: rank by "declares this concept", record the chosen file in the
   evidence dict, and suppress the allowed-values section when two equally-ranked
   candidates disagree.
3. **Assertion id ↔ HTML label drift.** JSON `assertion_id` and the HTML
   `assertionLabel` are authored separately. A fuzzy match that is too loose will
   attach the wrong rule's variables. Mitigation: exact match first, one
   normalised match second, and require the variable *set* to agree with the
   HTML's before accepting.
4. **Multi-instance rules.** 2065 has a rule failing 149 times with different
   values each time. Explaining only the first can mislead ("difference ₹1,000"
   when other instances differ by millions). Mitigation: state the count, and
   report min/max difference across instances when they differ materially.
5. **Scale/units.** BT shows `Entered 13459.2420` vs `Instance 134592420000`
   (×10⁷); `decimal` is `-3`/`-5`/`INF`; unit is `INR`/`EUR`/`PURE`. Presenting an
   entered value with a ₹ symbol and instance-scale magnitude would be badly
   wrong. Mitigation: never mix the two scales in one line; label them explicitly.
6. **Rounding semantics.** `round()` in XPath is half-up-toward-positive-infinity,
   not banker's rounding, and `div` on `Decimal` needs an explicit context.
   Getting this wrong flips pass/fail on boundary cases. Mitigation: `ROUND_HALF_UP`
   with an explicit high-precision context, plus boundary unit tests.
7. **A formula that actually passes.** Backtracking rows are a snapshot; a
   re-evaluated comparison can come out satisfied. The existing code already
   handles this (`passes` is computed, not assumed) and must keep saying
   "the recomputed values now satisfy this rule" rather than asserting a failure.
8. **Typed-domain facets beyond `base`.** Some typed domains may carry `pattern`,
   `enumeration`, `minLength`. Reading only `base` would under-describe them.
   Mitigation: extract all facets; describe only what was found.
9. **Performance.** Content-based taxonomy discovery over 315 `DataBase/<id>/`
   folders is expensive; R376's `RABO` error file is 1.9 MB and 2065's is 756 KB.
   Mitigation: per-folder index built once and cached by directory mtime; scope to
   `DataBase/<form_id>/Taxonomy` first and only widen on miss; keep the existing
   `lru_cache`.
10. **Encoding.** BTDetails carry French text with `’`, `≤`, `→`; messages carry
    `▼` (U+25BC) and NBSP. Every read must be explicit UTF-8 with
    `errors="replace"` (already the convention — keep it).
11. **LLM regression risk.** Looser prompts produce more natural but less
    grounded text. Mitigation: the gate is the contract; extend the gate before
    loosening the prompt, and keep the deterministic template always renderable.
12. **Unknown `xbrldie` classes.** Only two of six appear in the corpus. The
    router must fall back honestly for the rest rather than mis-describing them as
    primary-item errors — which is what the current `else` branch does.
