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
# Defaults to the `embeddings/` folder shipped alongside this package (a
# sibling of `src/`, i.e. `<this file>/../../embeddings`) — a self-contained,
# prebuilt artifact set with no embedding-building code anywhere in this
# runtime package. Override with the EMBEDDING_DIR env var to point at a
# different prebuilt artifact folder (e.g. when swapping in a refreshed
# embeddings drop) — never point it at build-time tooling.
# Every module that needs this MUST read `config.EMBEDDING_DIR` at call time
# (not `from src.config import EMBEDDING_DIR`, which freezes a stale copy at
# import time and silently ignores any later reassignment or env override).
EMBEDDING_DIR = os.environ.get("EMBEDDING_DIR", os.path.join(_REPO_ROOT, "embeddings"))

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

# NOTE: table/column selection (src/selector.py) used to make its own LLM call
# here (an instruct model, e.g. qwen2.5-coder:7b, alongside SQLCoder). Measured
# in production, that single call cost 75-135s+ per request — often MORE than
# SQL generation itself — almost certainly because the two 7B models did not
# both fit in the Ollama host's memory, forcing a reload on every alternating
# call. It was replaced with a deterministic heuristic (retrieval's own fused
# score, plus the declared semantic-layer join graph for the rare two-table
# case) that makes no network call at all. SELECTOR_MODEL/SELECTOR_OUTPUT_FORMAT
# no longer exist; nothing in src/selector.py talks to Ollama anymore.

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

# ── Phase 1 retrieval-accuracy roadmap: BM25 + hybrid fusion ─────────────────
# Weight of the BM25 lexical signal (src/lexical_search.py), fused alongside
# the 5 existing dense/embedding signals. Same tier as column_index (1.5): a
# precision signal on exact terms, weaker than a verified QA/concept match.
# Complementary to dense embedding, not a replacement — targets the confirmed
# sibling-table collision failure mode (e.g. SEC1_PART_A_DOM vs
# SEC1_PART_B_DOM score within ~0.02 cosine of each other; BM25 separates them
# on the exact term "Part A"/"Part B" instead — confirmed directly: BM25 scores
# SEC1_PART_A_DOM 9.11 vs SEC1_PART_B_DOM 8.57 on "total loan assets for
# domestic operations", the dense-only miss case). Set to 0 to disable (no
# BM25 search issued), reverting fusion to byte-identical pre-Phase-1 behaviour.
#
# Swept 0.75-3.0 at HYBRID_BLEND_GAMMA=0.3 (below): NO sensitivity in this
# range — the plain RRF vote from BM25 (max ~0.05 at this weight) is dwarfed
# by the existing QA-match bonus (~0.32 in the measured case above), so the
# RRF-side contribution alone cannot flip a ranking; gamma is what actually
# does the work (see below). 1.5 kept as a principled default (same tier as
# column_index) rather than an empty knob.
BM25_SIGNAL_WEIGHT = _env_float("BM25_SIGNAL_WEIGHT", 1.5)

# RRF is rank-only by design — a near-exact match (raw score 0.95) and a
# mediocre one (0.81) get almost the same fusion vote if they land at the same
# rank. HYBRID_BLEND_GAMMA adds a small term on top of the pure-RRF fused
# score: gamma * (each table's best raw score, min-max normalised WITHIN its
# own best-performing signal's hit list). 0.0 = pure RRF, byte-identical to
# pre-Phase-1 behaviour.
#
# Measured on eval/raq_user_queries.json (production config, QA signal on —
# this is the whole point: unlike CONCEPT_SIGNAL_WEIGHT this had to be tuned
# WITH the QA bonus active, since that bonus is exactly what it needs to
# counterbalance):
#
#   gamma   top1     hit@k    MRR      notes
#    0.0    0.733    0.933    0.809    baseline (BM25 in RRF only, no blend)
#    0.3    0.733    0.956    0.826    <- default: hit@k/MRR gain, ZERO regressions
#    0.6    0.733    0.956    0.828    same wins, s4-03 still safe
#    0.8-1.0 0.733   0.933    0.820    s4-03 REGRESSES (drops out of shortlist)
#    1.2-2.0 0.756   0.933    0.832    unit-02 gained, but s4-03 stays lost
#
# 1.2+ scores higher on top1 alone, but costs a shortlist miss on a question
# that gamma=0.3 answers correctly (s4-03: "written off as technical
# write-offs... domestic operations" -> CIMS_RAQ_Q_SEC4_PART_A) to gain a
# different one (unit-02: "total loan assets... in crore"). Trading a working
# case for a different one is not a win — same discipline already applied to
# CONCEPT_MAX_HITS_PER_TABLE: prefer the value with zero verified regressions
# over the value with a higher aggregate score bought by a different failure.
# Re-tune via scripts/eval_retrieval.py --dataset raq_form if the QA corpus or
# BM25 corpus changes meaningfully.
HYBRID_BLEND_GAMMA = _env_float("HYBRID_BLEND_GAMMA", 0.3)

# Weight of the prior-question (qa_index) signal. Exposed for ONE reason: the
# only ground truth that matches this scope, qa_pairs.json, is also the source of
# that index, so evaluating retrieval with it enabled measures memorisation, not
# retrieval — every question is its own exact match. Setting this to 0 disables
# the qa search, its score bonus, and its strong-match tier together, which makes
# a leak-free retrieval measurement possible:
#   QA_SIGNAL_WEIGHT=0 python -m scripts.eval_retrieval --dataset qa_pairs
# Leave it at the default in production; it is the strongest signal there is.
QA_SIGNAL_WEIGHT = _env_float("QA_SIGNAL_WEIGHT", 2.5)

# The QA-match bonus (src/retriever.py) adds an uncapped addend to one table's
# score to let a confident question match override a crowd of similarly-scored
# unrelated tables. Bug fixed here: the RELATIVE_FLOOR prune threshold used to
# be computed AFTER that bonus was applied, so the bonus (which can add ~1.25
# vs typical fused scores of 0.05-0.4) inflated the reference point every OTHER
# table's prune floor was measured against — a genuinely relevant second table
# (e.g. a join partner for a "compare X vs Y" question) could score below the
# inflated floor and be silently dropped before the selector ever saw it, even
# though effective_k had room for it. Fixed by snapshotting the floor reference
# BEFORE the bonus is applied; the bonus's effect on final ranking/inclusion is
# unchanged. Set to 0 to fall back to the old (buggy) post-bonus floor if this
# fix ever needs to be dark-launched/reverted without a code change:
#   QA_BONUS_FLOOR_FIX=0 python -m scripts.eval_retrieval --dataset raq_form
QA_BONUS_FLOOR_FIX = _env_int("QA_BONUS_FLOOR_FIX", 1)

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
