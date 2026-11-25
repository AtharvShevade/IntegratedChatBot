"""Where an XBRL schema error lives in the database, for a database return.

A schema error (cvc-datatype-valid ... 'is not a valid value for integer') names the instance file and the line of the
offending fact. That line holds the item (element) and its context, which is the same (concept, context) pair a formula
error's operand has, so the same lookup finds its table cell: table, column, row key and what the table holds there.

Nothing is invented: an Excel return, a line that cannot be read, or an item the return's queries do not read is left as
it was (the error keeps its ordinary explanation).
"""
from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

_FACT = re.compile(r"<(?:[\w.-]+:)?([\w.-]+)\b[^>]*?\bcontextRef\s*=\s*['\"]([^'\"]+)['\"][^>]*>([^<]*)<", re.IGNORECASE)


def _fact_on_line(instance_path: str, line_no) -> tuple[str, str, str] | None:
    """(element local name, context id, reported text) of the fact on that 1-based line of the instance, or None."""
    try:
        n = int(str(line_no).strip())
        with open(instance_path, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if i == n:
                    m = _FACT.search(line)
                    return (m.group(1), m.group(2), m.group(3).strip()) if m else None
    except (OSError, ValueError):
        pass
    return None


def _instance_for(err: dict, error_file: str) -> str | None:
    from . import reported_facts as rf
    p = rf.instance_path(error_file)
    if p:
        return p
    name = os.path.basename(str(err.get("filename") or ""))
    cand = os.path.join(os.path.dirname(error_file), name) if name else ""
    return cand if cand and os.path.isfile(cand) else None


def _members(meta, ctx_id: str) -> str:
    dims = meta.reported.ctx_dims(ctx_id) if getattr(meta, "reported", None) else None
    if not dims:
        return ""
    return ", ".join(f"{k}: {v}" for k, v in dims.items())


_REGION = (("domestic", ("DOM",)), ("overseas", ("OVER", "OVR")), ("global", ("GLOBAL", "GLB")))


def _by_region(addrs: list, meta, ctx_id: str) -> list:
    """Candidate columns that differ only by region (domestic / overseas / global) are narrowed by the context: its
    region member names the column, and a context with no region is the global figure. Narrowed only to exactly one."""
    if len(addrs) < 2:
        return addrs
    dims = (meta.reported.ctx_dims(ctx_id) if getattr(meta, "reported", None) else None) or {}
    member = next((str(v).lower() for k, v in dims.items() if "region" in str(k).lower()), "")
    want = next((w for w, _p in _REGION if member and w in member), "" if member else "global")
    prefixes = dict(_REGION).get(want)
    if not prefixes:
        return addrs
    hit = [a for a in addrs if str(a.column).upper().startswith(prefixes)]
    return hit if len(hit) == 1 else addrs


def locate_all(errors: list[dict], error_file: str, repo: str | None) -> dict[int, dict]:
    """{index in errors: {"table", "column", "row_label", "cell", "context", "state", "held", "candidates"}} for the schema errors
    that can be placed in a database table. {} when the return is not a database return or nothing can be placed."""
    out: dict[int, dict] = {}
    try:
        from . import cell_locator as cl, db_return as dbr, explain as ex, reported_facts as rf
        if not errors or not error_file or not dbr.enabled():
            return out
        form = ex.form_of(error_file, repo)
        folder = ex.metadata_folder(repo, form) if form else None
        if not folder:
            return out
        meta = cl.load_form_folder(folder, form)
        meta.reported = rf.load(error_file)
        if dbr.return_kind(meta) is True:               # an Excel return is located in its workbook, not in a table
            return out
        for i, err in enumerate(errors):
            inst = _instance_for(err, error_file)
            fact = _fact_on_line(inst, err.get("line_no")) if inst else None
            if not fact:
                continue
            element, ctx_id, text = fact
            res = dbr.resolve_db(meta, element, ctx_id, text)
            if res is None or not res.addresses:
                continue
            addrs = _by_region(res.addresses, meta, ctx_id)
            best = addrs[0]
            out[i] = {
                "table": best.table, "column": best.column, "row_label": (best.row_label or "").strip(),
                "cell": " / ".join(dict.fromkeys(a.a1 for a in addrs)),
                "context": _members(meta, ctx_id), "state": res.status,
                "held": best.db_value if best.state == "differs" else None,
                "candidates": len(addrs),
            }
    except Exception as exc:                            # noqa: BLE001 - location is extra; the error keeps its explanation
        logger.warning("[schema_locator] not located: %s", exc)
    return out


def _num(x) -> str:
    try:
        return f"{float(x):,.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(x)


def apply(errors: list[dict], error_file: str, repo: str | None = None) -> list[dict]:
    """Fill each error's table_info (table, row, cell, context) and add one sentence to its explanation, in place."""
    if repo is None:
        from . import adapter
        repo = adapter._repo_root()
    found = locate_all(errors, error_file, repo)
    for i, loc in found.items():
        err = errors[i]
        ti = dict(err.get("table_info") or {})
        ti.update(db_table_name=loc["table"], row_label=loc["row_label"] or ti.get("row_label", ""),
                  cell_code=loc["cell"], context=loc["context"] or ti.get("context", ""))
        err["table_info"] = ti
        filed = _num(err.get("actualValue") or "")
        if loc["state"] == "CONFIRMED":
            sentence = f" Found in {loc['table']}.{loc['column']}: the table holds the same value."
        elif loc["candidates"] > 1:                      # which of the columns it is depends on the context: name them, do not pick
            sentence = f" The return has {filed}. Check {loc['table']}: {loc['cell']}."
        elif loc["held"] is not None:
            sentence = f" The return has {filed}; the table holds {_num(loc['held'])} in {loc['table']}.{loc['column']}."
        else:
            sentence = f" The return has {filed}. Check {loc['table']}.{loc['column']} (not confirmed in the table)."
        err["explanation"] = (err.get("explanation") or "").rstrip() + sentence
        err["location"] = {k: loc[k] for k in ("table", "column", "state")}
    return errors
