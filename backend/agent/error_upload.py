"""backend/agent/error_upload.py -- "Error Resolution" tab: explain an error file the user uploads.

The check-status flow explains an error file the server already holds (Instance/<form>/<file>, found through the report's own
InstanceLog row). Here the file comes from the user, so three things are new:

  1. IDENTIFY the return.   Layered, most reliable first; a wrong return would give confidently wrong cell locations, so a guess is
     never silently accepted:
        a. the file name  -> InstanceLog (ErrorDocPath -> FormId): exact, and it also lets the engine find the user's workbook
        b. the rules in the file -> the taxonomy formula files (rule id = assertion id): accepted only for one clear winner
        c. a form id the user typed / picked (candidates are offered when a. and b. do not settle it)
        d. none: the engine still explains the rules from the file alone ("error file only"), and says so
  2. STORE the file safely.  Under a server-made folder, `<scratch>/<upload id>/Instance/<form>/<safe name>`: the same shape the engine
     reads (it finds the form from that path), never a client path, deleted after RETENTION_SECONDS.
  3. EXPLAIN in batches.    The very same pipeline as check-status (report_lookup.explain_errors_by_category_for_form), so a card here
     is byte-for-byte a card there.

Nothing here talks HTTP; main.py owns the endpoints and the access checks.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from typing import Any

from backend import config
from backend.agent.state import _build

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = (".html", ".htm", ".xml")
MAX_BYTES = int(os.getenv("ERROR_UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))
RETENTION_SECONDS = int(os.getenv("ERROR_UPLOAD_RETENTION_SECONDS", str(60 * 60)))
FINGERPRINT_BUDGET_SECONDS = float(os.getenv("ERROR_UPLOAD_FINGERPRINT_SECONDS", "20"))

_UPLOAD_ID = re.compile(r"^[0-9a-f]{32}$")
_FORM_ID = re.compile(r"^\d{1,6}$")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\- ()]")
_UNKNOWN_FORM = "_unknown"


class UploadError(ValueError):
    """A problem the user can fix (wrong type, empty, too big, expired); the message is safe to show."""


# ── scratch storage ────────────────────────────────────────────────────────────────────────────────────────────
def scratch_root() -> str:
    root = os.getenv("ERROR_UPLOAD_DIR", "").strip() or os.path.join(tempfile.gettempdir(), "chatbot_error_resolution")
    os.makedirs(root, exist_ok=True)
    return root


def _folder(upload_id: str) -> str:
    if not _UPLOAD_ID.match(upload_id or ""):
        raise UploadError("This upload is not valid. Please upload the error file again.")
    return os.path.join(scratch_root(), upload_id)


def purge_expired(now: float | None = None) -> int:
    """Delete upload folders older than RETENTION_SECONDS. Cheap (a directory listing); called on every upload."""
    now = now or time.time()
    removed = 0
    try:
        for name in os.listdir(scratch_root()):
            path = os.path.join(scratch_root(), name)
            try:
                if os.path.isdir(path) and now - os.path.getmtime(path) > RETENTION_SECONDS:
                    shutil.rmtree(path, ignore_errors=True)
                    removed += 1
            except OSError:
                continue
    except OSError:
        pass
    return removed


def safe_filename(original: str | None) -> str:
    """Keep the file's own base name (the InstanceLog match is by name) but nothing that could be a path or odd character."""
    base = re.split(r"[\\/]", (original or "").strip())[-1]
    stem, ext = os.path.splitext(base)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadError("Please upload the error file the validator produced (.html or .xml).")
    stem = _SAFE_NAME.sub("_", stem).strip(" .")[:120] or "error_file"
    return stem + ext


def check_content(data: bytes, filename: str) -> None:
    """Size and a content sniff, so a renamed binary is not accepted on its extension alone."""
    if not data:
        raise UploadError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise UploadError(f"The file is too large (limit {MAX_BYTES // (1024 * 1024)} MB).")
    head = data[:4096].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if b"\x00" in data[:4096]:
        raise UploadError("This does not look like a validator error file.")
    if filename.lower().endswith((".html", ".htm")):
        if b"<" not in head or not (b"<html" in head or b"<!doctype" in head or b"<div" in head or b"<table" in head):
            raise UploadError("This does not look like a validator error report (HTML).")
    elif not head.startswith(b"<"):
        raise UploadError("This does not look like a validator error file (XML).")


# ── identifying the return ─────────────────────────────────────────────────────────────────────────────────────
def _db_folder() -> str:
    return os.path.join(config._active_root(), "DataBase")


def form_from_instance_log(filename: str) -> str | None:
    """FormId of the run whose ErrorDocPath is this file name (5.5 XML_InstanceLog.xml / 6.0 InstanceLog.xml)."""
    name = os.path.basename(filename).lower()
    for fn in ("XML_InstanceLog.xml", "InstanceLog.xml"):
        path = os.path.join(_db_folder(), fn)
        if not os.path.isfile(path):
            continue
        try:
            import defusedxml.ElementTree as ET
            hits = {(row.get("FormId") or row.get("ReturnId") or "").strip()
                    for row in ET.parse(path).getroot().iter("Row")
                    if os.path.basename((row.get("ErrorDocPath") or row.get("ErrorDoc") or "").replace("\\", "/")).lower() == name}
        except Exception as exc:                                    # noqa: BLE001 - an unreadable log just means "not found here"
            logger.warning("[ERROR_UPLOAD] instance log unreadable (%s): %s", fn, exc)
            continue
        hits.discard("")
        if len(hits) == 1:                                          # one name, two forms would be a guess: leave it to the next step
            return hits.pop()
    return None


_RULE_ID = re.compile(r'<(?:\w+:)?(?:valueAssertion|existenceAssertion)\b[^>]*?\bid="([^"]+)"', re.I)
_RULE_INDEX: dict[str, tuple[float, dict[str, frozenset]]] = {}


def _form_folders(repo: str) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for base in (os.path.join(repo, "DataBase"), repo):
        try:
            for name in os.listdir(base):
                p = os.path.join(base, name)
                if name.isdigit() and os.path.isdir(os.path.join(p, "Taxonomy")):
                    seen.setdefault(name, p)
        except OSError:
            continue
    return sorted(seen.items())


def _rule_ids_of(folder: str) -> frozenset:
    ids: set[str] = set()
    for dirpath, _dirs, files in os.walk(os.path.join(folder, "Taxonomy")):
        for fn in files:
            if "formula" in fn.lower() and fn.lower().endswith(".xml"):
                try:
                    with open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore") as fh:
                        ids.update(_RULE_ID.findall(fh.read()))
                except OSError:
                    continue
    return frozenset(ids)


def rule_index(repo: str, budget: float = FINGERPRINT_BUDGET_SECONDS) -> dict[str, frozenset]:
    """{form id: rule ids its taxonomy defines}, built once per repo root and kept. Stops at the time budget (partial is fine: the
    caller only accepts a clear winner)."""
    hit = _RULE_INDEX.get(repo)
    if hit:
        return hit[1]
    t0, index = time.monotonic(), {}
    for form, folder in _form_folders(repo):
        if time.monotonic() - t0 > budget:
            logger.warning("[ERROR_UPLOAD] rule index stopped at the time budget after %d forms", len(index))
            break
        index[form] = _rule_ids_of(folder)
    else:
        _RULE_INDEX[repo] = (time.time(), index)                    # only a COMPLETE index is kept
    return index


def rule_names_in(html: str) -> list[str]:
    from backend.error_improvement import error_html as eh
    try:
        return [r.name for r in eh.parse_rules(html) if r.name]
    except Exception:                                               # noqa: BLE001
        return []


def candidates_by_rules(rule_names: list[str], repo: str | None = None) -> list[tuple[str, float]]:
    """[(form id, share of this file's rules the form's taxonomy defines)], best first, only forms that match something."""
    if not rule_names:
        return []
    repo = repo or config._active_root()
    names = set(rule_names)
    scored = []
    for form, ids in rule_index(repo).items():
        n = len(names & ids)
        if n:
            scored.append((form, n / len(names)))
    return sorted(scored, key=lambda fs: (-fs[1], fs[0]))[:5]


def pick_winner(scored: list[tuple[str, float]]) -> str | None:
    """A clear winner or nothing: the best form must hold nearly all the rules AND beat the runner-up by a margin.
    (Two returns can share rule ids; guessing between them would explain against the wrong return's cells.)"""
    if not scored:
        return None
    best_form, best = scored[0]
    runner = scored[1][1] if len(scored) > 1 else 0.0
    return best_form if best >= 0.9 and best - runner >= 0.2 else None


def identify(filename: str, data: bytes, form_id: str | None = None) -> dict[str, Any]:
    """{form_id, method, candidates:[{form_id, score}]}. method: given | instance_log | rules | none."""
    if form_id:
        if not _FORM_ID.match(form_id):
            raise UploadError("Return id must be a number, for example 4046.")
        return {"form_id": form_id, "method": "given", "candidates": []}
    f = form_from_instance_log(filename)
    if f:
        return {"form_id": f, "method": "instance_log", "candidates": []}
    scored: list[tuple[str, float]] = []
    if filename.lower().endswith((".html", ".htm")):
        try:
            scored = candidates_by_rules(rule_names_in(data.decode("utf-8", errors="ignore")))
        except Exception as exc:                                    # noqa: BLE001
            logger.warning("[ERROR_UPLOAD] rule fingerprint failed: %s", exc)
    winner = pick_winner(scored)
    cands = [{"form_id": f_, "score": round(s, 2)} for f_, s in scored]
    return {"form_id": winner, "method": "rules" if winner else "none", "candidates": cands}


def return_name(form_id: str) -> str:
    try:
        from backend.tools.report_lookup import _parse_returns
        for r in _parse_returns():
            if str(r.get("Id", "")).strip() == str(form_id):
                return r.get("Name", "") or ""
    except Exception:                                               # noqa: BLE001 - a missing name is cosmetic
        pass
    return ""


# ── store / load ───────────────────────────────────────────────────────────────────────────────────────────────
def _path_of(upload_id: str, form_id: str | None, filename: str) -> str:
    return os.path.join(_folder(upload_id), "Instance", form_id or _UNKNOWN_FORM, filename)


def _meta_path(upload_id: str) -> str:
    return os.path.join(_folder(upload_id), "meta.json")


def store(data: bytes, filename: str, form_id: str | None, login_id: str | None, identification: dict) -> str:
    """Write the file and its meta; returns the upload id."""
    purge_expired()
    upload_id = uuid.uuid4().hex
    path = _path_of(upload_id, form_id, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    with open(_meta_path(upload_id), "w", encoding="utf-8") as fh:
        json.dump({"filename": filename, "form_id": form_id, "login_id": login_id or "", "method": identification.get("method")}, fh)
    return upload_id


def load_meta(upload_id: str, login_id: str | None) -> dict:
    """The upload's meta, only for the user who made it (and only while it exists)."""
    try:
        with open(_meta_path(upload_id), encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        raise UploadError("This upload has expired. Please upload the error file again.") from None
    if (meta.get("login_id") or "") != (login_id or ""):
        raise UploadError("This upload has expired. Please upload the error file again.")
    return meta


def set_form(upload_id: str, login_id: str | None, form_id: str) -> dict:
    """The user picked / typed the return: move the stored file under that form and record it."""
    meta = load_meta(upload_id, login_id)
    if not _FORM_ID.match(form_id or ""):
        raise UploadError("Return id must be a number, for example 4046.")
    old = _path_of(upload_id, meta.get("form_id"), meta["filename"])
    new = _path_of(upload_id, form_id, meta["filename"])
    if old != new:
        os.makedirs(os.path.dirname(new), exist_ok=True)
        shutil.move(old, new)
    meta.update(form_id=form_id, method="given")
    with open(_meta_path(upload_id), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    return meta


def file_path(upload_id: str, meta: dict) -> str:
    return _path_of(upload_id, meta.get("form_id"), meta["filename"])


# ── summary + batches (same engine as check-status) ────────────────────────────────────────────────────────────
def summarise(upload_id: str, meta: dict) -> dict[str, Any]:
    """What the UI needs to show the summary panel: counts per category, the identified return, how sure we are."""
    from backend.tools.report_lookup import count_errors_by_category, _is_4000_series
    form_id = meta.get("form_id") or ""
    counts = count_errors_by_category(file_path(upload_id, meta), form_id=form_id)
    return {
        "upload_id": upload_id,
        "filename": meta["filename"],
        "form_id": form_id,
        "report_name": return_name(form_id) if form_id else "",
        "identified_by": meta.get("method") or "none",
        "is_4000_series": _is_4000_series(form_id) if form_id else False,
        "error_category_counts": counts,
    }


async def explain_batch(upload_id: str, login_id: str | None, category: str, offset: int, lang: str = "en") -> dict[str, Any]:
    """One batch (3) of a category, shaped exactly like /explain-category's response."""
    from backend.tools.report_lookup import explain_errors_by_category_for_form, count_errors_by_category
    from backend.agent.error_explanation import _CATEGORY_DISPLAY

    if category not in _CATEGORY_DISPLAY:
        return _build(intent="explain_errors", report_name=None, response_text=f"Unsupported error category: {category}", result_type="error")
    meta = load_meta(upload_id, login_id)
    path, form_id = file_path(upload_id, meta), meta.get("form_id") or ""
    offset = max(0, int(offset or 0))
    label = _CATEGORY_DISPLAY[category]
    report = return_name(form_id) if form_id else None
    try:
        explained = await asyncio.to_thread(explain_errors_by_category_for_form, path, category, form_id, offset, lang or "en")
    except Exception as exc:                                        # noqa: BLE001
        logger.error("[ERROR_UPLOAD] explain failed category=%s file=%s: %s", category, meta.get("filename"), exc)
        return _build(intent="explain_errors", report_name=report,
                      response_text=f"Sorry, I couldn't explain the {label.lower()} in this file right now. Please try again.", result_type="error")
    if not explained:
        return _build(intent="explain_errors", report_name=report,
                      response_text=(f"No {label.lower()} could be read from this file." if offset == 0 else f"No further {label.lower()} remain to explain."),
                      result_type="error")
    nxt = offset + len(explained)
    total, errs, warns = nxt, None, None
    try:
        counts = await asyncio.to_thread(count_errors_by_category, path, form_id)
        total = counts.get(category, nxt)
        if category == "formula_error":
            errs, warns = counts.get("formula_error", 0), counts.get("formula_warning", 0)
            total = counts.get("formula_total", errs + warns) or nxt
    except Exception as exc:                                        # noqa: BLE001
        logger.warning("[ERROR_UPLOAD] count lookup failed, falling back: %s", exc)
    text = f"⚙ {label} — showing {offset + 1}-{nxt} of {total}" if total else f"⚙ {label} — showing {len(explained)}"
    data = {"has_more": nxt < total, "next_offset": nxt, "total_count": total}
    if errs is not None:
        data.update(error_count=errs, warning_count=warns)
    return _build(intent="explain_errors", report_name=report, response_text=text, result_type="final", error_details=explained, data=data)


__all__ = ["UploadError", "ALLOWED_EXTENSIONS", "safe_filename", "check_content", "identify", "store", "set_form", "load_meta",
           "summarise", "explain_batch", "purge_expired"]
