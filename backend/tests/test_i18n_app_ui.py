"""Application-wide static UI localization (frontend/src/i18n.ui.js).

Static UI text is a dictionary lookup, never a model call. These tests defend
the three things that makes safe:

  1. COVERAGE   -- every key resolves in EN/FR/AR/HI, with the right script,
                   and English is the fallback for anything missing.
  2. SEPARATION -- data, technical identifiers and wire values are NOT in the
                   dictionary, so they can never be localized by accident.
  3. WIRING     -- the components actually call t(); no hardcoded English is
                   left behind, and every `t` used is in scope.

The dictionary is read by executing the real module through node, so the tests
see exactly what the browser will.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / "frontend"
DUMP = FRONTEND / "scripts" / "dump-i18n.mjs"
SRC = FRONTEND / "src"

LANGS = ("en", "fr", "ar", "hi")
TARGETS = ("fr", "ar", "hi")

COMPONENTS = [
    SRC / "App.jsx",
    SRC / "components" / "MessageBubble.jsx",
    SRC / "components" / "VarianceChartModal.jsx",
    SRC / "components" / "ChatWindow.jsx",
    SRC / "components" / "VoiceInput.jsx",
]


@pytest.fixture(scope="module")
def bundle() -> dict:
    node = shutil.which("node")
    if node is None or not DUMP.exists():
        pytest.skip("node / dump-i18n.mjs not available")
    out = subprocess.run([node, str(DUMP)], cwd=FRONTEND, capture_output=True, timeout=60)
    if out.returncode != 0:
        pytest.fail(out.stderr.decode("utf-8", "replace"))
    return json.loads(out.stdout.decode("utf-8"))


@pytest.fixture(scope="module")
def ui(bundle) -> dict:
    return bundle["UI"]


def _strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"(?<![:'\"])//[^\n]*", "", source)


# ---------------------------------------------------------------------------
# 1. Coverage
# ---------------------------------------------------------------------------

def test_dictionary_is_populated(ui):
    assert len(ui) >= 100, f"only {len(ui)} UI keys - the dictionary looks truncated"


@pytest.mark.parametrize("lang", LANGS)
def test_every_key_has_every_language(ui, lang):
    missing = sorted(k for k, v in ui.items() if not str(v.get(lang, "")).strip())
    assert not missing, f"{lang} missing for: {missing}"


def test_no_unexpected_languages(ui):
    for key, entry in ui.items():
        extra = set(entry) - set(LANGS)
        assert not extra, f"{key} has unknown languages {extra}"


@pytest.mark.parametrize("lang", TARGETS)
def test_translations_differ_from_english(ui, lang):
    """Catches an entry copy-pasted and never translated. A handful of terms
    are genuinely identical across languages and are listed explicitly rather
    than silently tolerated."""
    SAME_BY_DESIGN = {
        "common.date",        # "Date" is French for Date
        "common.actions",     # "Actions" likewise
        "comparativeAnalysis.columns.concept",   # "Concept" likewise
        "comparativeAnalysis.concepts",
        "comparativeAnalysis.importance",        # "Importance" likewise
        "comparativeAnalysis.instance1",
        "comparativeAnalysis.instance2",
        "comparativeAnalysis.sortConcept",   # "concept" in French too
    }
    same = sorted(
        k for k, v in ui.items()
        if v[lang] == v["en"] and k not in SAME_BY_DESIGN
    )
    assert not same, f"{lang} still English for: {same}"


@pytest.mark.parametrize("lang,lo,hi", [("ar", 0x0600, 0x06FF), ("hi", 0x0900, 0x097F)])
def test_target_script_is_used(ui, lang, lo, hi):
    """A French string pasted into the Arabic slot passes the differs-from-
    English check but not this one."""
    for key, entry in ui.items():
        text = entry[lang]
        # Entries that are only punctuation/latin by design (e.g. "% Var.")
        if not re.search(r"[^\W\d_]", text, re.UNICODE):
            continue
        if key in {"comparativeAnalysis.columns.pctChange"}:
            continue
        assert any(lo <= ord(ch) <= hi for ch in text), (
            f"{key}.{lang} contains no {lang} script: {text!r}"
        )


def test_keys_are_feature_namespaced(ui):
    """Organized by feature, not one flat list."""
    namespaces = {k.split(".")[0] for k in ui}
    assert {"common", "status", "comparativeAnalysis", "errors", "sql"} <= namespaces
    for key in ui:
        assert "." in key, f"{key} has no feature namespace"


def test_shared_words_are_defined_once(ui):
    """No common.cancel / dialog.cancel / modal.cancel duplication."""
    for word in ("cancel", "close", "save", "search", "filter", "export",
                 "download", "refresh", "status", "actions"):
        owners = [k for k in ui if k.rsplit(".", 1)[-1].lower() == word]
        assert owners == [f"common.{word}"] or len(owners) <= 1, (
            f"'{word}' is defined in several namespaces: {owners}"
        )


def test_english_fallback(bundle):
    """A missing language must fall back to English, not render undefined."""
    node = shutil.which("node")
    script = (
        "import {makeT} from './src/i18n.js';"
        "const t=makeT('fr');"
        "console.log(JSON.stringify({known:t('common.cancel'),unknown:t('nope.nope')}));"
    )
    path = FRONTEND / "_fallback_probe.mjs"
    path.write_text(script, encoding="utf-8")
    try:
        out = subprocess.run([node, str(path)], cwd=FRONTEND,
                             capture_output=True, timeout=60)
        data = json.loads(out.stdout.decode("utf-8"))
    finally:
        path.unlink(missing_ok=True)
    assert data["known"] == "Annuler"
    assert data["unknown"] == "nope.nope", "unknown key must degrade to the key"


# ---------------------------------------------------------------------------
# 2. Separation -- data and wire values are NOT localizable
# ---------------------------------------------------------------------------

FORBIDDEN_IN_DICTIONARY = [
    "CIMS_ROR", "CIMS_FormGPB", "CIMS_FormA_R013_F", "CIMS_RAQ",
    "R009", "R149", "DBR01", "RAQ(Quarterly)",
    "31-Mar-2026", "30-Sep-2025", "2026-12-12T17:00:00", "17:00",
]


@pytest.mark.parametrize("value", FORBIDDEN_IN_DICTIONARY)
def test_no_business_data_in_the_dictionary(ui, value):
    """Report names, IDs, dates and times are DATA. If one ever appears here
    it could be swapped per language, which would corrupt it."""
    for key, entry in ui.items():
        for lang in LANGS:
            assert value not in entry[lang], f"{key}.{lang} contains data {value!r}"


def test_protocol_tokens_are_not_in_the_ui_dictionary(bundle):
    """Guided action tokens live in ACTIONS (key = wire value). They must not
    be duplicated here, where nothing guarantees the key/value contract."""
    from backend.guided import GUIDED_ACTIONS
    for token in GUIDED_ACTIONS:
        assert token not in bundle["UI"]


def test_option_labels_still_keyed_by_wire_value(bundle):
    """The Schedule / Change Data contract: display localized, send English."""
    for value, entry in bundle["OPTION_LABELS"].items():
        assert entry["en"] == value
        for lang in TARGETS:
            assert entry[lang] != value or value in {"Instance 1"}


# ---------------------------------------------------------------------------
# 3. Wiring -- components use t(), no English left behind
# ---------------------------------------------------------------------------

# Strings that were hardcoded before this work and must now come from t().
FORMERLY_HARDCODED = [
    "AI Analysis", "Variance Visualisation", "Comparable Facts", "Facts compared",
    "No rows to display.", "Download always exports the full set.",
    "Search concept…", "Search concept name…", "Close chart", "Variance Chart",
    "Schema Match", "Generated SQL", "Query Results", "No rows returned.",
    "Need more detail:", "How to fix", "Dimensional Validation Errors",
    "DB Table Name", "Row Label", "Cell Code", "Explanation",
    "Clear filters", "No facts match this filter.", "Compare Instances",
    "Instance 1", "Instance 2", "High variance", "Open chart visualisation",
]


# Contexts where a string is genuinely RENDERED: JSX text, an attribute
# value, or a display label in an array. A bare occurrence is not enough --
# "Explanation" appears inside the identifier _parseFormulaExplanationBlocks,
# and "How to fix" inside a REGEX that parses the backend's English output.
# Neither is UI text, and neither may be translated.
def _rendered_occurrences(code: str, literal: str) -> list[str]:
    hits: list[str] = []
    escaped = re.escape(literal)
    for line in code.splitlines():
        if literal not in line:
            continue
        # A regex that PARSES the backend's English output is not UI text and
        # must never be localized - translating it would break the parser.
        if ".match(" in line or "RegExp" in line or "replace(/" in line:
            continue
        # Part of a longer identifier (_parseFormulaExplanationBlocks) rather
        # than a rendered word.
        if re.search(r"[A-Za-z0-9_]" + escaped + r"|" + escaped + r"[A-Za-z0-9_]", line):
            continue
        rendered = (
            re.search(r">\s*" + escaped, line)
            or re.search(r'=\s*"' + escaped + r'"', line)
            or re.search(r"'" + escaped + r"'", line)
            or re.search(r"`[^`]*" + escaped, line)
        )
        if rendered:
            hits.append(line.strip()[:100])
    return hits


@pytest.mark.parametrize("literal", FORMERLY_HARDCODED)
def test_no_hardcoded_english_remains(literal):
    """Only RENDERED occurrences count. Comments, identifiers and the regexes
    that parse the backend's English output legitimately contain these words
    and must NOT be localized."""
    for path in COMPONENTS:
        code = _strip_comments(path.read_text(encoding="utf-8"))
        hits = _rendered_occurrences(code, literal)
        assert not hits, f"{path.name} still renders {literal!r}: {hits}"


def test_every_t_call_uses_a_known_key(ui, bundle):
    """A typo'd key renders the key itself at the user. Catch it here."""
    known = set(ui) | set(bundle["STRINGS"])
    unknown = []
    for path in COMPONENTS:
        code = _strip_comments(path.read_text(encoding="utf-8"))
        for key in re.findall(r"\bt\('([A-Za-z][\w.]*)'\)", code):
            if key not in known:
                unknown.append(f"{path.name}: {key}")
    assert not unknown, f"t() called with unknown keys: {unknown}"


def test_t_is_in_scope_wherever_it_is_used():
    """A missing `t` is a runtime ReferenceError that the Vite build does NOT
    catch -- it blanks the app the moment the module loads or the component
    renders.

    This delegates to frontend/scripts/check-t-scope.py, which walks the real
    bracket structure. An earlier regex version split the file at top-level
    declarations and MISSED a module-level `const X = { ... t(...) ... }`,
    which shipped and produced exactly that white screen.
    """
    script = FRONTEND / "scripts" / "check-t-scope.py"
    if not script.exists():
        pytest.skip("check-t-scope.py not present")
    out = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT), capture_output=True, timeout=120,
        env={**os.environ, "PROJECT_ROOT": str(PROJECT_ROOT)},
    )
    report = out.stdout.decode("utf-8", "replace")
    assert "WITHOUT a binding in any enclosing scope: 0" in report, report


def test_every_module_body_executes():
    """Bundle the app with esbuild and RUN it.

    A build only proves the syntax parses. Calling t() at module level parses
    fine and throws at import time; only executing the module bodies catches
    it. This is the check that would have caught the white screen.
    """
    node = shutil.which("node")
    probe = FRONTEND / "scripts" / "smoke-execute.mjs"
    if node is None or not probe.exists() or not (FRONTEND / "node_modules").exists():
        pytest.skip("node / esbuild / smoke-execute.mjs not available")
    out = subprocess.run([node, str(probe)], cwd=FRONTEND,
                         capture_output=True, timeout=180)
    report = out.stdout.decode("utf-8", "replace") + out.stderr.decode("utf-8", "replace")
    assert "MODULE EXECUTION: OK" in report, report


def test_column_keys_are_unchanged():
    """Only the LABEL is localized; the sort/API key stays English."""
    code = (SRC / "components" / "MessageBubble.jsx").read_text(encoding="utf-8")
    for key in ("'concept'", "'val_a'", "'val_b'", "'diff'", "'pct'"):
        assert f"handleSort({key})" in code, f"sort key {key} was altered"


def test_ui_dictionary_makes_no_network_call():
    code = _strip_comments((SRC / "i18n.ui.js").read_text(encoding="utf-8"))
    for forbidden in ("fetch(", "XMLHttpRequest", "axios", "services/api",
                      "TRANSLATION_MODEL", "await "):
        assert forbidden not in code, f"i18n.ui.js references {forbidden!r}"
    assert not re.search(r"^\s*import\s", code, re.M), "the dictionary must have no dependencies"


def test_rtl_is_still_only_arabic(bundle):
    assert bundle["RTL"] == ["ar"]


def test_language_switch_is_pure_lookup():
    """Switching language must not trigger a request -- App.jsx changes state
    and re-renders; nothing in that path fetches."""
    code = _strip_comments((SRC / "App.jsx").read_text(encoding="utf-8"))
    match = re.search(r"const \[lang, setLang\][^\n]*\n(?:.*\n){0,12}", code)
    assert match, "language state not found in App.jsx"
    assert "fetch" not in match.group(0)
    assert "localStorage" in match.group(0), "selection must persist"


# ---------------------------------------------------------------------------
# 4. STRICT LANGUAGE PURITY
# ---------------------------------------------------------------------------
#
# The scanner that found the reported leakage ("Download", "Bar", "Line",
# "Increase", "Absolute Diff", "comparable facts", ...) is kept as a test, so
# the next hardcoded string fails the build instead of reaching a user.
#
# It looks for RENDERED English that is not a dictionary value. Deliberately
# NOT a substring check on translated output -- English substrings occur
# naturally inside valid French words ("date", "instance", "importance"), and
# that approach produces false failures rather than real ones.

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"^\s*//[^\n]*$", re.M)

# Prose = letters, digits and ordinary punctuation only.
_PROSE = re.compile(r"^[A-Za-z0-9%·—–…'’\"()\[\],.:;!?/&+\- ]+$")
# Anything with these is code, not a sentence.
_CODEISH = re.compile(r"===|=>|\?\?|\|\||&&|\$\{|\n|/>|</|className|px\b")

# Values that are legitimately NOT translated. Each is DATA, a CSS class, a
# technical token, or a parsing key matched against the backend's English.
PURITY_ALLOWLIST = {
    # CSS class strings assembled in code
    "avatar assistant-avatar", "bubble-row assistant",
    "bubble assistant-bubble typing-indicator",
    "welcome-suggestions option-chips",
    "welcome-suggestions option-chips sched-confirm-actions",
    "feedback-btn feedback-yes", "feedback-btn feedback-no",
    "formula-error-body error-card-body",
    "formula-error-section error-card-locator",
    "formula-error-section error-card-rule",
    "formula-error-section formula-error-fix",
    "variance-summary-text variance-summary-empty",
    "variance-summary-text variance-summary-loading",
    "vt-concept-col vt-sortable", "vt-num-col vt-sortable",
    "vt-pct vt-pct-zerobase", "vc-chip vc-chip-sm",
    "vc-controls vc-controls-rank", "mic-btn mic-btn--",
    "var(--text-muted)",
    # Font stack for the exported HTML - a technical value
    "Segoe UI",
    # Parsing keys matched against the BACKEND's English output. Translating
    # any of these would break the parser, not localize anything.
    "Dimension Error", "What is wrong", "What should be checked",
    "Reported value", "Context", "Failure Reason(s):",
    "Generating error explanations…",
    # Regulatory tier values that come from the return's taxonomy JSON (data)
    "Critical", "High", "Medium", "Low", "All",
}


def _rendered_english(path) -> set[str]:
    source = _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", path.read_text(encoding="utf-8")))
    found: set[str] = set()

    def consider(value: str) -> None:
        v = value.strip()
        if len(v) < 3 or v in PURITY_ALLOWLIST:
            return
        if not _PROSE.match(v) or _CODEISH.search(v):
            return
        if re.fullmatch(r"[\w.\-/#:]+", v):
            return
        # A CSS class LIST: every token lower-case, hyphen/underscore-joined,
        # no sentence punctuation. These are assembled in code, never shown.
        if re.fullmatch(r"[a-z][a-z0-9_-]*(?: [a-z][a-z0-9_-]*)*", v):
            return
        # A fragment of an expression the regex sliced out of source, not a
        # sentence: method calls, comparisons, index arithmetic.
        if re.search(r"\.\w+\(|\)\s*\?|\?\s*$|^\W*\)", v):
            return
        words = re.findall(r"[A-Za-z]{2,}", v)
        if words and (len(words) >= 2 or v[:1].isupper()):
            found.add(v)

    for m in re.finditer(r">([^<>{}]*[A-Za-z]{2}[^<>{}]*)<", source):
        consider(m.group(1))
    for m in re.finditer(r'\b(?:title|aria-label|placeholder|alt)=["\']([^"\']+)["\']', source):
        consider(m.group(1))
    for m in re.finditer(r"(?<![\w.$])['\"]([^'\"\n]{3,150})['\"]", source):
        consider(m.group(1))
    for m in re.finditer(r"`([^`]{3,400})`", source, re.DOTALL):
        for part in re.split(r"\$\{[^{}]*(?:\{[^{}]*\})?[^{}]*\}", m.group(1)):
            consider(part)
    return found


@pytest.mark.parametrize("component", [p.name for p in COMPONENTS])
def test_no_rendered_english_outside_the_dictionary(bundle, component):
    """THE leakage guard. Any user-visible English that is not a dictionary
    value (or an explicitly allowlisted technical value) fails here."""
    known = {
        entry["en"].strip()
        for table in ("UI", "STRINGS", "ACTIONS", "ACTION_DESCRIPTIONS", "OPTION_LABELS")
        for entry in bundle[table].values()
    }
    path = next(p for p in COMPONENTS if p.name == component)
    leaked = sorted(_rendered_english(path) - known)
    assert not leaked, (
        f"{component} renders English that is not in the dictionary "
        f"({len(leaked)}): {leaked}"
    )


@pytest.mark.parametrize("lang", TARGETS)
def test_every_ui_key_is_translated_not_english_fallback(ui, lang):
    """A KNOWN UI key must never silently fall back to English. Only the terms
    that are genuinely identical across languages are exempted, by name."""
    IDENTICAL_BY_LANGUAGE = {
        "common.date", "common.actions",
        "comparativeAnalysis.columns.concept", "comparativeAnalysis.concepts",
        "comparativeAnalysis.importance",
        "comparativeAnalysis.instance1", "comparativeAnalysis.instance2",
        "comparativeAnalysis.sortConcept",
    }
    untranslated = sorted(
        key for key, entry in ui.items()
        if entry[lang].strip() == entry["en"].strip()
        and key not in IDENTICAL_BY_LANGUAGE
    )
    assert not untranslated, f"{lang} falls back to English for: {untranslated}"


@pytest.mark.parametrize("lang", TARGETS)
def test_placeholder_slots_survive_translation(ui, lang):
    """A template that loses its {0} would drop a count or a report name."""
    for key, entry in ui.items():
        want = sorted(re.findall(r"\{(\d+)\}", entry["en"]))
        got = sorted(re.findall(r"\{(\d+)\}", entry[lang]))
        assert want == got, f"{key}.{lang} slots {got} != English {want}"


def test_lang_reaches_the_wire_for_every_endpoint():
    """The frontend must actually PUT `lang` in the request body.

    This is the gap that shipped: the backend handled `lang` correctly and
    every unit test passed, while api.js never sent the field -- so the AI
    Analysis came back English. Testing translate_outbound() cannot catch a
    break on the wire; this stubs fetch and inspects the real request body.
    """
    node = shutil.which("node")
    probe = FRONTEND / "scripts" / "check-lang-propagation.mjs"
    if node is None or not probe.exists() or not (FRONTEND / "node_modules").exists():
        pytest.skip("node / esbuild / check-lang-propagation.mjs not available")
    out = subprocess.run([node, str(probe)], cwd=FRONTEND,
                         capture_output=True, timeout=180)
    report = out.stdout.decode("utf-8", "replace") + out.stderr.decode("utf-8", "replace")
    assert "LANG PROPAGATION: OK" in report, report
    # Every endpoint that can carry user-visible prose must appear.
    for endpoint in ("/chat", "/guided", "/compare-execute",
                     "/compare-summary", "/explain-category"):
        assert endpoint in report, f"{endpoint} not covered by the probe"
