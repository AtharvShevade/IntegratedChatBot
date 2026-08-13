# Unified Error Card (v2)

One generic view for **both** formula and dimension validation errors, replacing
two different 7–8 section layouts with a single card.

- **Baseline commit (revert point):** `107355a` — the tree was clean here.
- **Feature flag:** `ERROR_CARD_V2` (default **on**)
- **Status:** additive. The v1 builders are untouched and still reachable.

---

## Why

Both error types are the same statement underneath — *here is what was expected,
here is what you gave, here is the gap* — but each had its own vocabulary for
saying it:

| Formula (v1) | Dimension (v1) |
|---|---|
| Validation Rule | What Was Reported |
| Reported Values | Details This Figure Must Carry |
| Comparison | What Each Detail Must Contain |
| Why It Failed | Details Actually Provided |
| Where to Check | What Is Wrong |
| How to Fix | How to Fix |
| | Context Id |

The dimension layout stated *"Type of criminal and Date/Time are missing"* four
separate times, and still made the reader **diff two lists by eye** to find out
which details were absent. The longest, most prominent line in the message was
the 9-option allowed-value list for a field whose problem was that it was
*missing* — information that is not actionable for that diagnosis.

## The card

    headline   What broke — names the actual fields/amount, not the category
    locator    Where in my data do I go
    rule       What was supposed to be true, in one plain sentence
    matrix     Expected vs. what I gave, row by row, with a per-row status
    fix        What to do now
    details    Everything else, collapsed  ← nothing is deleted, only re-tiered

Seven sections become four visible blocks plus a drawer, and the same skeleton
serves both error types.

### Where each v1 section went

| v1 | v2 |
|---|---|
| Headline (generic) | **headline** — now names the specific fields/amount |
| Validation Rule | **rule** |
| Reported Values + Comparison | **matrix** (they were two halves of one table) |
| Details Must Carry + Must Contain + Actually Provided | **matrix** (three views of the same rows) |
| Why It Failed / What Is Wrong | absorbed by the headline + row statuses; full prose → drawer |
| Where to Check / Context Id | **locator** (context id decoded to a period) |
| How to Fix | **fix** |
| Full allowed-value lists, validator message, taxonomy source | **drawer** |

Nothing is dropped. `test_error_card_v2.py::TestNothingIsLost` asserts the full
member lists, the v1 diagnosis prose and the raw context id are all still
reachable.

---

## How to revert

### 1. Behaviour only (no code change) — preferred

```
ERROR_CARD_V2=0
```

in `.env`, then restart the backend. Both error types immediately return to
their original sections. The frontend needs no change: the v1 section kinds
were never removed from the renderer.

**This path is test-verified.** `backend/tests/test_error_explanation_v2.py`
pins `ERROR_CARD_V2=0` for its whole run and all 152 of its tests pass — that
suite *is* the specification of the legacy layout, so its passing proves the
old path still builds correctly and is still reachable.

### 2. Full code removal

```
git diff 107355a --stat        # exactly what this change touched
git checkout 107355a -- backend/tools/dimension_error.py \
                         backend/tools/formula_error.py \
                         backend/tests/test_error_explanation_v2.py \
                         frontend/src/components/MessageBubble.jsx \
                         frontend/src/App.5.5.css frontend/src/App.6.0.css
rm backend/tools/error_card.py backend/tests/test_error_card_v2.py
```

The CSS additions are a single clearly-marked block at the end of each
stylesheet (`UNIFIED ERROR CARD (v2)`) using only new class names, so deleting
those two blocks is also safe on its own.

---

## Files

| File | Change |
|---|---|
| `backend/tools/error_card.py` | **new** — schema, flag, context-id period decoding, shared text serialiser |
| `backend/tools/dimension_error.py` | **added** section 3b (`build_card_sections`, `render_card`) + flag branch in `explain_dimension_errors`. v1 `build_sections` untouched |
| `backend/tools/formula_error.py` | **added** section 4b (`build_card_sections`, `render_card`) + flag branch in `explain_one_rule`. v1 `build_sections` untouched |
| `frontend/src/components/MessageBubble.jsx` | `FormulaErrorSections` gains `locator` / `matrix` / `fix` / `details` cases; v1 cases unchanged |
| `frontend/src/App.5.5.css`, `App.6.0.css` | appended `.error-card-*` block (new class names only) |
| `backend/tests/test_error_explanation_v2.py` | pinned to `ERROR_CARD_V2=0` (it specifies the v1 layout) |
| `backend/tests/test_error_card_v2.py` | **new** — 28 tests, no corpus/LLM/filesystem needed |

---

## Known scope limits

1. **`formula_error_generic.py` is not covered.** That parser never emitted
   `explanation_sections` at all, so it already rendered through the older
   string-parsing path and is unaffected either way. `report_lookup.py` still
   routes some non-4000-series files to it. Bringing it onto the card is a
   separate piece of work.

2. **`invalid_combination` has no per-row verdict.** When every detail is
   individually valid and only the *set* is rejected, the matrix shows all rows
   neutral and the rule sentence carries the finding. This is correct — marking
   an arbitrary row ❌ would be a claim the evidence does not support.

3. **`_axis_requirement()` can still print a raw taxonomy type** (`"Any value of
   type xbrli:stringItemType"`) when the taxonomy supplies no description. This
   is pre-existing v1 behaviour, now confined to the drawer. The matrix's
   Expected column already maps these to everyday words ("text", "date & time")
   via `_short_base_type()`; extending that to the drawer would change v1 output
   and was left out of this change deliberately.

## Test status

| Suite | Result |
|---|---|
| `test_error_card_v2.py` | 28 passed |
| `test_error_explanation_v2.py` (v1 pinned) | 152 passed |
| `backend/tests` + `backend/db_qa` full run | 1219 passed, 11 failed |

The 11 failures were confirmed **pre-existing** — the same 11 fail at `107355a`
with this work stashed. They are in compare-disambiguation, instance-id status,
report-lookup conversational replies and intent-classifier phrasing; none touch
error explanation.
