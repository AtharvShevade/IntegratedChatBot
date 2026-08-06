"""
All deployment/environment-specific values are read from environment variables,
loaded from a local `.env` file if one is present (see `.env.example` for the
full list and `MIGRATION_NOTES` at the bottom of this docstring).

Every setting keeps its EXACT previous default, so an existing deployment with
no `.env` file behaves identically to before — with one deliberate exception:
DB_HOST / DB_USER / DB_PASSWORD no longer have a hardcoded fallback (see the
"Oracle DB connection" section below for why).

Precedence: real environment variables (as set by the OS/shell/container) always
win over `.env` — `.env` only fills in values nothing else has already set.
"""

import os

from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=False)


def _env_int(name: str, default: int) -> int:
    """int(os.environ[name]) with a safe fallback to `default` on missing/bad values."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"[config] WARNING: {name}={raw!r} is not a valid int — using default {default}")
        return default


def _env_float(name: str, default: float) -> float:
    """float(os.environ[name]) with a safe fallback to `default` on missing/bad values."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"[config] WARNING: {name}={raw!r} is not a valid float — using default {default}")
        return default


EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-large-en")

# Which folder retrieval reads its FAISS indexes / schema.json from.
# Defaults to the CIMS_RAQ(Quarterly) scoped build — that's what's actually
# under active development/testing (qa_pairs.json, direct-match tiers, the
# validation fixes). Production (embedding_building/output, no qa_index)
# used to be the default and repeatedly caused silent regressions whenever a
# server restart lost the EMBEDDING_DIR env var — every fix this session
# stopped applying with no error, just worse answers. Override with the
# EMBEDDING_DIR env var to point elsewhere, e.g.:
#   EMBEDDING_DIR=embedding_building/output python -m api.main
# Every module that needs this MUST read `config.EMBEDDING_DIR` at call time
# (not `from src.config import EMBEDDING_DIR`, which freezes a stale copy at
# import time and silently ignores any later reassignment or env override).
EMBEDDING_DIR = os.environ.get("EMBEDDING_DIR", "embedding_building/cims_raq_quarterly")

# Tied to EMBED_MODEL: this is BGE's required "asymmetric" query-side instruction
# prefix (documents are embedded with no prefix at all). Changing EMBED_MODEL to
# a non-BGE model without also changing/clearing this will silently degrade
# retrieval — the prefix text would just become noise prepended to every query.
QUERY_PREFIX = os.environ.get(
    "QUERY_PREFIX", "Represent this sentence for searching relevant passages: "
)

TOP_K_TABLES = _env_int("TOP_K_TABLES", 3)
TOP_K_COLUMNS = _env_int("TOP_K_COLUMNS", 5)

# How many candidate tables retrieval returns for the selector to choose from.
# This is a RECALL setting, not a precision one: the selector (src/selector.py)
# narrows it to one table before the SQL model sees anything. Do not feed this
# many tables to the SQL model directly — that is what caused it to JOIN every
# candidate and invent the foreign key (eval/results/hallucination_log.jsonl).
SHORTLIST_K = _env_int("SHORTLIST_K", 8)

# Token budget for the multi-part UNION ALL case, which is the longest SQL the
# model ever has to emit. Was 300, which truncated mid-identifier and produced
# fabricated table names (see hallucination_log.jsonl: "... FROM cims_raq").
MINIMAL_MULTIPART_NUM_PREDICT = _env_int("MINIMAL_MULTIPART_NUM_PREDICT", 1024)

# Ollama settings.
# Current effective default is the remote proxy (this was the active line before
# this refactor — the local-daemon line below it was commented out). Switch
# between them with the OLLAMA_URL env var / .env entry instead of editing this
# file:
#   local daemon : OLLAMA_URL=http://localhost:11434/api/generate
#   remote proxy : OLLAMA_URL=http://3.109.51.228/OllamaProxy/api/generate
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://3.109.51.228/OllamaProxy/api/generate")

# Set the active Ollama-served model here. Change only this value to swap models
# without modifying src/sql_generator.py.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "hf.co/defog/sqlcoder-7b-2:Q5_K_M")
# Context window sent to Ollama; the retry path resends schema + bad SQL + reason,
# so this needs headroom beyond the model's low default (often 2048) or retries return empty.
OLLAMA_NUM_CTX = _env_int("OLLAMA_NUM_CTX", 8192)

# How long Ollama keeps the model resident after a request. The default is 5
# minutes, so the first query after an idle spell pays a full model load (seconds
# for a 7B Q5), and alternating between the selector model and the SQL model can
# reload BOTH on every request if they do not fit in memory together. This is
# usually the single largest latency win available.
OLLAMA_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")

# "compact" (default) or "json" for the selector's reply. JSON is measurably
# slower: constrained decoding costs per-token time, and the braces/keys/reasons
# roughly triple the output length for the same decision. Use "json" only if the
# selector model follows schemas better than it follows instructions.
SELECTOR_OUTPUT_FORMAT = os.environ.get("SELECTOR_OUTPUT_FORMAT", "compact")

# Kept as a plain in-code dict (not env-driven): it is keyed by exact Ollama
# model name, several keys have long inline rationale comments, and env vars
# cannot represent nested per-model structure cleanly. Only the ACTIVE model's
# temperature/num_predict are environment-overridable — see the block below.
MODEL_PROFILES = {
    "gpt-oss:120b-cloud": {
        "prompt_style": "rules",
        "dialect_hint": "Oracle",
        "temperature": 0.0,
        "num_predict": 512,
    },

    "qwen2.5:7b": {
        "prompt_style": "rules",
        "dialect_hint": "Oracle",
        "temperature": 0.0,
        "num_predict": 512,
    },
    "llama3.1:latest": {
        "prompt_style": "minimal",
        "dialect_hint": "Oracle",
        "temperature": 0.0,
        "num_predict": 128,
    },
    "hf.co/defog/sqlcoder-7b-2:Q5_K_M": {
        # "ddl": a real CREATE TABLE block with types, NOT NULL, PRIMARY KEY and
        # row-label values as column comments, in SQLCoder's own training prompt
        # format. The previous "minimal" style listed columns in prose and relied
        # on bullet-point instructions the model demonstrably ignored (it JOINed
        # every candidate table and invented the FK to do it).
        "prompt_style": "ddl",
        "dialect_hint": "Oracle",
        "temperature": 0.0,
        # 128 was starving generation: every one of the 36 records in
        # eval/results/hallucination_log.jsonl has first_attempt_sql == "" with
        # reason "Empty SQL", so the pipeline was always running on its retry
        # path. A vertical-table query with an exact label literal in the WHERE
        # clause alone exceeds 128 tokens.
        "num_predict": 512,
    },
    "hf.co/mradermacher/Arctic-Text2SQL-R1-7B-GGUF:Q5_K_M": {
        "prompt_style": "minimal",
        "dialect_hint": "Oracle",
        "temperature": 0.0,
        "num_predict": 512,
    },
}

# Optional overrides for the two numeric generation knobs, applied ONLY to
# whichever profile OLLAMA_MODEL selects. Unset by default, so behavior is
# identical to before unless these are explicitly set — this exists so
# "generation configuration" (num_predict / temperature) can be tuned per
# deployment without editing MODEL_PROFILES.
if OLLAMA_MODEL in MODEL_PROFILES:
    if os.environ.get("OLLAMA_NUM_PREDICT", "").strip() != "":
        MODEL_PROFILES[OLLAMA_MODEL]["num_predict"] = _env_int(
            "OLLAMA_NUM_PREDICT", MODEL_PROFILES[OLLAMA_MODEL]["num_predict"]
        )
    if os.environ.get("OLLAMA_TEMPERATURE", "").strip() != "":
        MODEL_PROFILES[OLLAMA_MODEL]["temperature"] = _env_float(
            "OLLAMA_TEMPERATURE", MODEL_PROFILES[OLLAMA_MODEL]["temperature"]
        )

# Model used for the non-SQL reasoning calls — table/column selection
# (src/selector.py) and, when enabled, the reasoning plan. SQLCoder is a
# completion model: it cannot follow prose instructions or emit JSON, so it
# stays responsible only for writing SQL against a narrow typed schema block.
# This must be an INSTRUCT model, and it must be present in `ollama list`.
#
# qwen2.5-coder:7b (4.7GB) is the default because it follows the compact output
# format reliably. Note it loads alongside SQLCoder (4.8GB), so plan for ~9.5GB;
# if that thrashes, phi3:mini (2.2GB) is the low-memory alternative:
#   $env:SELECTOR_MODEL = "phi3:mini"
SELECTOR_MODEL = os.environ.get("SELECTOR_MODEL", "qwen2.5-coder:7b")

# ── XBRL business-semantics layer (src/business_semantics.py) ────────────────
# How much of the XBRL-derived business layer to inject into the SQL prompt.
# Levels are CUMULATIVE and ordered by value/risk — see the module docstring of
# src/business_semantics.py for the full rationale:
#
#   off         nothing rendered; prompts are byte-identical to pre-integration
#   units       reporting-unit line only (fixes the silent 100000x error)
#   metrics     + business label -> column cards
#   aggregation + stock/flow SUM guidance
#   dimensions  + usable dimension axes with their live literals
#   derivation  + a rollup formula expressed in physical columns
#
# Roll out ONE level at a time with `python -m eval.run_eval` between each: a 7B
# model does not respond additively to prompt text, so a level that helps in
# isolation can still regress when stacked. Requires concept_map.json in
# EMBEDDING_DIR (built by embedding_building/cims_raq_quarterly/build_concept_map.py);
# without it every level degrades silently to "off".
BUSINESS_SEMANTICS_LEVEL = os.environ.get("BUSINESS_SEMANTICS_LEVEL", "off")

# RRF fusion weights for the two XBRL retrieval signals in src/retriever.py.
# Set either to 0 to disable that signal completely — no search is issued and it
# contributes nothing to fusion, so the ranking is byte-identical to the
# pre-integration behaviour. That makes them A/B-testable with an env var alone:
#   CONCEPT_SIGNAL_WEIGHT=0 MEMBER_SIGNAL_WEIGHT=0 python -m scripts.eval_retrieval
#
# For reference, the existing signals are weighted: qa 2.5, table 2.0,
# column 1.5, row-label 1.0.
#
# Both defaults below are MEASURED, not assumed — a weight sweep over the 100
# quarterly questions in qa_pairs.json with QA_SIGNAL_WEIGHT=0 (leak-free; see
# below) gave, against a 0.23 top1 / 0.381 MRR baseline:
#
#   concept   member    top1     hit@k     MRR
#     1.0       0       0.34      0.69     0.493
#     2.0       0       0.39      0.72     0.534   <- default
#     3.0       0       0.39      0.72     0.538
#     4.0       0       0.37      0.71     0.521
#     2.0     0.75      0.37      0.71     0.518
#     2.0     1.50      0.37      0.66     0.491
#
# concept (E) = 2.0: a concept hit names ONE (table, column) via a mapping
#   verified by a deterministic 4-hop join, so it is as strong as direct table
#   search. 3.0 scores a hair higher on MRR alone and is within noise on 100
#   questions, so the lower, more conservative value is kept.
#
# member (F) = 0 (DISABLED). The design expected this to help a little; it
#   measurably hurts at every weight tried. The cause is structural, not a tuning
#   miss: a member routes to every table whose concepts reference its AXIS, and
#   the axes here are broad (one member reaches a dozen tables), so each hit
#   sprays weak votes across the shortlist and dilutes the precise concept vote.
#   Fixing it would need member->table routing narrowed to tables that actually
#   store that member as a row label. Left in the code, off by default, so that
#   experiment is a one-env-var change rather than a rebuild.
#
# Re-tune with scripts/eval_retrieval.py: no LLM, no DB, ~17s for 100 questions.
CONCEPT_SIGNAL_WEIGHT = _env_float("CONCEPT_SIGNAL_WEIGHT", 2.0)

# How many concept hits a SINGLE table may accumulate votes from. See the long
# comment at the concept-fusion loop in src/retriever.py: an unbounded sum lets a
# table holding many similarly-worded sibling concepts outvote the table holding
# the one exact match. 1 = best hit only.
#
# Measured over qa_pairs.json (QA_SIGNAL_WEIGHT=0) alongside the offline guard
# suite in scripts/test_accuracy_guards.py, whose cases encode real logged
# failures with hand-verified correct answers:
#
#   maxhits   top1    hit@k    MRR     guard failures
#      1      0.29     0.66    0.458        0
#      2      0.33     0.71    0.503        0          <- default
#      3      0.38     0.73    0.534        1
#      4      0.38     0.73    0.533        1
#    none     0.39     0.72    0.534        1
#
# 2 is chosen over 3 deliberately. 3 scores ~5 points higher on aggregate top1
# but breaks "Show inter-bank assets by period of delinquency", where the concept
# index's own rank-0 hit ('Inter bank assets' -> SEC1_PART_B_DOM, 0.865) agrees
# with the guard's expected answer and the sum still hands the win to
# SEC1_PART_A_DOM on four weaker sibling hits. Trading a known-correct answer for
# aggregate movement on a 100-question set is the wrong trade; the aggregate gain
# is within a few questions of noise, the guard failure is a definite wrong answer.
# Raise to 3 if you re-tune and accept that case.
CONCEPT_MAX_HITS_PER_TABLE = _env_int("CONCEPT_MAX_HITS_PER_TABLE", 2)
MEMBER_SIGNAL_WEIGHT = _env_float("MEMBER_SIGNAL_WEIGHT", 0.0)

# Weight of the prior-question (qa_index) signal. Exposed for ONE reason: the
# only ground truth that matches this scope, qa_pairs.json, is also the source of
# that index, so evaluating retrieval with it enabled measures memorisation, not
# retrieval — every question is its own exact match. Setting this to 0 disables
# the qa search, its score bonus, and its strong-match tier together, which makes
# a leak-free retrieval measurement possible:
#   QA_SIGNAL_WEIGHT=0 python -m scripts.eval_retrieval --dataset qa_pairs
# Leave it at the default in production; it is the strongest signal there is.
QA_SIGNAL_WEIGHT = _env_float("QA_SIGNAL_WEIGHT", 2.5)

# ── Context selection / schema slicing (src/context/) ────────────────────────
# Which retrieval-to-prompt path a request takes:
#   legacy  the pre-context flow — retrieval shortlist -> selector -> build_prompt
#           renders the WHOLE selected table (all columns, all sampled row
#           labels, blind-truncated). Unchanged, so it stays the A/B baseline.
#   new     the Context Resolver path: intent + domain + metric binding produce a
#           PromptContext holding only the slice the question needs.
# Kept as a flag rather than a cutover because prompt changes at 7B are NOT
# additive — the same reason BUSINESS_SEMANTICS_LEVEL is staged. Flip the default
# only once `python -m scripts.eval_context` and `python -m eval.run_eval` both
# show the new path winning.
CONTEXT_PIPELINE = os.environ.get("CONTEXT_PIPELINE", "legacy")

# Per-axis context caps — see src/context/budget.py for why each default is what
# it is (they are set against the measured 764-token baseline in
# scratch/sql_generation_context_report.md, not guessed).
CTX_MAX_TABLES = _env_int("CTX_MAX_TABLES", 2)
CTX_MAX_COLUMNS_PER_TABLE = _env_int("CTX_MAX_COLUMNS_PER_TABLE", 12)
# Replaces the effective MAX_LABELS_DDL=14 cap applied to an UNRANKED list. Six
# ranked values plus the always-pinned TOTAL row beat fourteen sample-ordered
# ones: in the traced prompt one column's label list was ~23% of the entire
# prompt, and the value the question needed was not guaranteed to be among them.
CTX_MAX_LABELS_PER_COLUMN = _env_int("CTX_MAX_LABELS_PER_COLUMN", 6)
CTX_MAX_EXAMPLES = _env_int("CTX_MAX_EXAMPLES", 2)
CTX_MAX_RULE_LINES = _env_int("CTX_MAX_RULE_LINES", 12)
CTX_MAX_SEMANTIC_LINES = _env_int("CTX_MAX_SEMANTIC_LINES", 6)
CTX_MAX_TOTAL_TOKENS = _env_int("CTX_MAX_TOTAL_TOKENS", 1800)

# ── Oracle DB connection ─────────────────────────────────────────────────────
# DB_HOST / DB_USER / DB_PASSWORD have NO hardcoded fallback — this repo
# previously committed a live Oracle password and bank-identifying username
# directly in source. They MUST come from a `.env` file (gitignored, never
# committed) or a real environment variable. If unset, these are empty strings
# and the Oracle connection will fail with a clear authentication/connect
# error — that is intentional; it is safer than a working-by-default hardcoded
# credential. See .env.example and MIGRATION_NOTES.md for setup.
DB_HOST = os.environ.get("DB_HOST", "")
DB_PORT = _env_int("DB_PORT", 1521)
DB_SERVICE = os.environ.get("DB_SERVICE", "XE")   # or SID, e.g. "xe" — not sensitive, safe default kept
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_MAX_ROWS = _env_int("DB_MAX_ROWS", 100)         # max rows to fetch per query
