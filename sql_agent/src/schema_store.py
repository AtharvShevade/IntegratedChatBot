"""
Cached, indexed access to the on-disk schema artefacts.

Why this exists
---------------
Every schema lookup in this codebase used to `json.load()` a whole file and then
LINEARLY SCAN it for the handful of tables the request cared about — and it did
that several times per request. In one `/query` call the chain was:

    build_prompt      -> _load_all_columns   (parse schema.json, scan)
                      -> _load_table_entries (parse schema.json, scan)
                      -> load_samples        (parse description_samples.json)
    generate_sql      -> _load_all_columns   (parse again)
    validate_sql      -> _load_all_columns   (parse again)
                      -> load_samples        (parse again)
    selector          -> _load_table_entries (parse again)

The FAISS indexes were already cached for exactly this reason (see
`src.retriever._index_cache`); the schema files were not, even though
schema.json is the larger cost once the catalog grows — 119 KB today, ~2 MB at
the multi-return scale this pipeline is being sized for, parsed 4-6 times per
request.

So: parse once per (path, process), keep a `{table_lower: entry}` index, and
serve every lookup as a dict hit.

Cache lifetime and refresh
--------------------------
Cached for the life of the process, matching `_index_cache`'s documented
behaviour: rebuilding the artefacts requires a restart to pick them up, because
uvicorn's reloader watches `api/` and `src/`, not `embedding_building/`. Call
`clear_cache()` after editing an artefact in a live process (tests do this).

Keyed on the resolved PATH, not on `config.EMBEDDING_DIR`, so a scope switch
naturally gets its own cache entry instead of being served a stale index — and
so callers that pass an explicit `schema_path` are cached too.
"""

import json
import logging
import os

import src.config as config

log = logging.getLogger("schema_store")

# The pre-scoping schema build. Tables missing from the active schema.json are
# looked up here as a fallback, preserving the behaviour the sql_generator
# loaders have always had. Note the path is relative, so the fallback only
# resolves when cwd is the repo root.
LEGACY_SCHEMA_PATH = "embedding_building/output/schema.json"

# {path: {table_lower: entry}}
_schema_cache: dict = {}
# {path: {table_as_stored: {column_lower: [value, ...]}}}
_samples_cache: dict = {}
# {path: {table: [label_column, ...]}}
_needs_trim_cache: dict = {}


# ── path resolution (always read config at CALL time, never at import) ────────

def schema_path() -> str:
    return f"{config.EMBEDDING_DIR}/schema.json"


def samples_path() -> str:
    return f"{config.EMBEDDING_DIR}/description_samples.json"


def needs_trim_path() -> str:
    return os.path.join(config.EMBEDDING_DIR, "needs_trim.json")


def clear_cache():
    """Drop every cached artefact. Call after rebuilding indexes in-process."""
    _schema_cache.clear()
    _samples_cache.clear()
    _needs_trim_cache.clear()


# ── schema.json ──────────────────────────────────────────────────────────────

def _load_schema_index(path: str) -> dict:
    """
    {table_lower: entry} for one schema.json, parsed at most once per process.

    A missing file caches an empty index rather than raising: the loaders this
    replaces treated FileNotFoundError as "no tables here", and the legacy
    fallback path is legitimately absent in most deployments.
    """
    if path in _schema_cache:
        return _schema_cache[path]

    index: dict = {}
    try:
        with open(path, encoding="utf-8") as fh:
            schema = json.load(fh)
    except FileNotFoundError:
        schema = []
    except (OSError, ValueError) as e:
        # A malformed schema.json is worth a log line — silently behaving as if
        # the catalog were empty is how a build error turns into "the agent
        # suddenly can't find any table".
        log.error("Could not read schema %s: %s", path, e)
        schema = []

    for entry in schema:
        name = entry.get("table") or entry.get("table_name")
        if name:
            index[name.lower()] = entry

    _schema_cache[path] = index
    return index


def table_entries(table_names, path: str | None = None) -> dict:
    """
    {table_lower: entry} for the requested tables — full schema.json entries
    (columns with type/nullable/is_primary_key, plus table-level
    primary_key/foreign_keys/description).

    Tables absent from the active schema are looked up in LEGACY_SCHEMA_PATH,
    preserving `_load_table_entries`' fallback.
    """
    if path is None:
        path = schema_path()

    wanted = {str(n).lower() for n in table_names}
    index = _load_schema_index(path)
    out = {name: index[name] for name in wanted if name in index}

    missing = wanted - set(out)
    if missing and path != LEGACY_SCHEMA_PATH:
        legacy = _load_schema_index(LEGACY_SCHEMA_PATH)
        out.update({name: legacy[name] for name in missing if name in legacy})

    return out


def columns_for(table_names, path: str | None = None) -> list:
    """
    [{"table": <as stored>, "column": <as stored>}, ...] for the requested
    tables, in schema order. Same shape and ordering `_load_all_columns`
    returned, so every existing consumer (eval/metrics.py, validate_sql,
    scripts/merge_qa_pairs.py) is unaffected.
    """
    result = []
    for entry in table_entries(table_names, path).values():
        table_name = entry.get("table") or entry.get("table_name")
        for col in entry.get("columns") or []:
            column_name = col.get("name") or col.get("column_name")
            if column_name:
                result.append({"table": table_name, "column": column_name})
    return result


def column_names_by_table(table_names, path: str | None = None) -> dict:
    """
    {table_lower: {column_lower, ...}} — the shape validate_sql and the slicer
    both want, built directly instead of re-derived from a flat list on every
    call.
    """
    out: dict = {}
    for name, entry in table_entries(table_names, path).items():
        out[name] = {
            (c.get("name") or c.get("column_name") or "").lower()
            for c in entry.get("columns") or []
            if (c.get("name") or c.get("column_name"))
        }
    return out


def all_table_names(path: str | None = None) -> list:
    """Every table in the active schema, as stored. Needed by the domain gate,
    which has to resolve a section/return reference to an allow-set."""
    index = _load_schema_index(path or schema_path())
    return [(e.get("table") or e.get("table_name")) for e in index.values()]


# ── description_samples.json (row labels) ────────────────────────────────────

def label_samples(path: str | None = None) -> dict:
    """
    {table: {column: [value, ...]}} of sampled row-label values, parsed once.

    Returns the CACHED dict — callers must not mutate it. `build_prompt`
    historically copied values out of this into its own label_map, which is
    still the right pattern.
    """
    if path is None:
        path = samples_path()
    if path not in _samples_cache:
        try:
            with open(path, encoding="utf-8") as fh:
                _samples_cache[path] = json.load(fh)
        except FileNotFoundError:
            _samples_cache[path] = {}
        except (OSError, ValueError) as e:
            log.error("Could not read row-label samples %s: %s", path, e)
            _samples_cache[path] = {}
    return _samples_cache[path]


def label_samples_lower(path: str | None = None) -> dict:
    """
    `label_samples()` with table keys lowercased.

    Different EMBEDDING_DIR scopes have been observed storing table keys with
    different casing, so two call sites in sql_generator rebuilt this same
    lowercased dict on every request. Built once here instead.
    """
    key = ("__lower__", path or samples_path())
    if key not in _samples_cache:
        _samples_cache[key] = {
            k.lower(): v for k, v in label_samples(path).items()
        }
    return _samples_cache[key]


def labels_for(table: str, path: str | None = None) -> dict:
    """{column_lower: [value, ...]} for one table, case-insensitively."""
    return {
        col.lower(): vals
        for col, vals in (label_samples_lower(path).get(table.lower()) or {}).items()
    }


# ── needs_trim.json ─────────────────────────────────────────────────────────

def needs_trim(path: str | None = None) -> dict:
    """
    {table_lower: {column_lower, ...}} for label columns whose stored values are
    whitespace-padded, so a filter must be written TRIM(COL) = 'value'.

    Written by `description_fetcher.fetch_and_save`. Absent in most builds —
    the slicer therefore treats this as one of TWO sources and also runs the
    live padding check, rather than trusting it alone.
    """
    if path is None:
        path = needs_trim_path()
    if path not in _needs_trim_cache:
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except FileNotFoundError:
            raw = {}
        except (OSError, ValueError) as e:
            log.error("Could not read %s: %s", path, e)
            raw = {}
        _needs_trim_cache[path] = {
            str(tbl).lower(): {str(c).lower() for c in cols}
            for tbl, cols in (raw or {}).items()
        }
    return _needs_trim_cache[path]
