# backend/sql_agent/context_resolver.py
#
# Query-side context for the SQL agent, resolved BEFORE retrieval:
#
#   * which regulatory return(s) the question names  -> detect_returns()
#     (so retrieval/selection can be scoped to that return's tables only)
#   * which reporting date / period the question names -> extract_report_date()
#     (so the generated SQL can be pinned to it; no date means latest RDATE)
#
# Everything here is deterministic and read-only: the return catalogue comes
# from the active embedding folder's schema.json (+ concept_map.json for the
# numeric return codes), the same files retrieval itself reads.

from __future__ import annotations

import calendar
import json
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)

__all__ = [
    "ReturnInfo", "ReportPeriod",
    "load_returns", "detect_returns", "tables_for_returns", "returns_for_tables",
    "short_return_label", "extract_report_date",
]


# ── Return catalogue ──────────────────────────────────────────────────────────

@dataclass
class ReturnInfo:
    name: str                                   # exact return_name from schema.json
    tables: list[str] = field(default_factory=list)
    codes: set[str] = field(default_factory=set)        # "f010", "qcb_f010", "raq", "4091" ...
    title: str = ""                             # "maturity ladder of assets & liabilities"


_lock = threading.Lock()
_cache: dict[str, dict[str, ReturnInfo]] = {}


def _embedding_dir() -> str:
    from backend.sql_agent import config
    # read the live module, not the snapshot constant (see config.SRC_CONFIG)
    return config.SRC_CONFIG.EMBEDDING_DIR


def _split_return_name(name: str) -> tuple[list[str], str]:
    """"QCB_F010_Maturity Ladder of Assets & Liabilities" -> (["qcb", "f010"], "maturity ladder ...")
    "CIMS_RAQ(Quarterly)" -> (["cims", "raq"], "quarterly")"""
    parts = [p for p in re.split(r"_", name) if p]
    codes: list[str] = []
    title_parts: list[str] = []
    for p in parts:
        bare = re.sub(r"\(.*?\)", "", p).strip()
        if not title_parts and bare and re.fullmatch(r"[A-Za-z]{1,6}\d{0,4}", bare.replace(" ", "")) and " " not in bare:
            codes.append(bare.lower())
        else:
            title_parts.append(p)
    paren = " ".join(re.findall(r"\((.*?)\)", name))
    title = " ".join(title_parts).strip() or paren
    return codes, re.sub(r"\s+", " ", title).strip().lower()


# A table's schema.json return_name can list several returns of one family that
# differ only by filing frequency: "CIMS_RAQ(Annually), CIMS_RAQ(Monthly),
# CIMS_RAQ(Quarterly)". Treated verbatim, each such string became its own "return"
# with no usable code (its tokens were shared with the others), so "RAQ" resolved
# to the single plain "CIMS_RAQ(Monthly)" entry (4 of 42 RAQ tables) and "LR" /
# "ALE" resolved to nothing. Grouping by family fixes both. Names without a
# frequency suffix or a list separator (e.g. all 6.0 "QCB_F010_..." names) are
# returned unchanged.
_RETURN_LIST_SPLIT = re.compile(r",\s*(?=[A-Za-z]{2,}_)")
_FREQUENCY_SUFFIX = re.compile(r"\s*\([^()]*\)\s*$")


def _return_families(return_name: str) -> list[str]:
    """Distinct family names in a (possibly composite) schema.json return_name."""
    families: list[str] = []
    for part in _RETURN_LIST_SPLIT.split(return_name or ""):
        family = _FREQUENCY_SUFFIX.sub("", part).strip()
        if family and family not in families:
            families.append(family)
    return families


def load_returns() -> dict[str, ReturnInfo]:
    """{return_name: ReturnInfo} for the active embedding folder (cached per folder)."""
    edir = _embedding_dir()
    with _lock:
        if edir in _cache:
            return _cache[edir]

    returns: dict[str, ReturnInfo] = {}
    try:
        with open(os.path.join(edir, "schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as exc:
        logger.warning("[SQL_AGENT] context_resolver: cannot read schema.json in %s: %s", edir, exc)
        schema = []

    for entry in schema:
        rname = (entry.get("return_name") or "").strip()
        table = (entry.get("table") or "").strip()
        if not rname or not table or entry.get("is_backup"):
            continue
        for family in _return_families(rname):
            info = returns.setdefault(family, ReturnInfo(name=family))
            if table not in info.tables:
                info.tables.append(table)

    # numeric return codes (4091 ...) where the build recorded them
    try:
        with open(os.path.join(edir, "concept_map.json"), encoding="utf-8") as f:
            cmap = json.load(f)
        for m in cmap.get("metrics") or []:
            rn, rc = (m.get("return_name") or "").strip(), str(m.get("return_code") or "").strip()
            for family in _return_families(rn):
                if family in returns and rc:
                    returns[family].codes.add(rc)
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger.debug("[SQL_AGENT] context_resolver: concept_map.json unreadable: %s", exc)

    # code tokens: keep only the ones that identify exactly one return
    token_owner: dict[str, list[str]] = {}
    for rname, info in returns.items():
        codes, title = _split_return_name(rname)
        info.title = title
        joined = "_".join(codes)
        cand = set(codes) | ({joined} if len(codes) > 1 else set())
        for c in cand:
            token_owner.setdefault(c, []).append(rname)
    for tok, owners in token_owner.items():
        if len(owners) == 1:
            returns[owners[0]].codes.add(tok)

    with _lock:
        _cache[edir] = returns
    logger.info(
        "[SQL_AGENT] context_resolver: %d return(s) loaded from %s: %s",
        len(returns), edir, {r: sorted(i.codes) for r, i in returns.items()},
    )
    return returns


def _code_pattern(code: str) -> str:
    """'f010' also matches 'f10', 'f-010', 'F 010'; '4091' matches only itself."""
    m = re.fullmatch(r"([a-z]+)0*(\d+)", code)
    if m:
        return rf"{m.group(1)}[\s_\-]?0*{m.group(2)}"
    return re.escape(code).replace(r"\_", r"[\s_\-]?")


_STOP_TITLE = {"of", "and", "&", "by", "the", "for", "in", "on", "a", "an"}


def detect_returns(query: str) -> list[str]:
    """Return names the question explicitly refers to (by full name, code such as
    F010 / RAQ / 4091, or by title such as "maturity ladder"). Empty when none."""
    q = (query or "").lower()
    if not q.strip():
        return []
    returns = load_returns()
    hits: list[str] = []

    for rname, info in returns.items():
        if rname.lower() in q:
            hits.append(rname)
            continue
        if any(re.search(rf"(?<![a-z0-9]){_code_pattern(c)}(?![a-z0-9])", q) for c in info.codes):
            hits.append(rname)
            continue
        # title: at least two thirds of its significant words present (order-free,
        # prefix match so "exposure" finds "exposures"), or a close fuzzy hit.
        # "breakdown by geography" hits both F013 and F014 -> the caller asks.
        words = [w for w in re.findall(r"[a-z]+", info.title) if w not in _STOP_TITLE and len(w) > 2]
        found = sum(1 for w in words if re.search(rf"\b{re.escape(w[:max(4, len(w) - 2)])}", q))
        if len(words) >= 2 and found >= 2 and found * 3 >= len(words) * 2:
            hits.append(rname)
            continue
        if len(info.title) >= 12:
            try:
                from rapidfuzz import fuzz
                if fuzz.partial_ratio(info.title, q) >= 90:
                    hits.append(rname)
            except Exception:
                pass
    return hits


def tables_for_returns(return_names) -> set[str]:
    returns = load_returns()
    out: set[str] = set()
    for r in return_names or []:
        info = returns.get(r)
        if info:
            out.update(t.lower() for t in info.tables)
    return out


def returns_for_tables(table_names) -> list[str]:
    """Distinct return names owning *table_names*, in first-seen order."""
    owner: dict[str, str] = {}
    for rname, info in load_returns().items():
        for t in info.tables:
            owner[t.lower()] = rname
    seen: list[str] = []
    for t in table_names or []:
        r = owner.get(str(t).lower())
        if r and r not in seen:
            seen.append(r)
    return seen


def short_return_label(return_name: str) -> str:
    """A short, unambiguous label the user can click/type back: the full return name."""
    return return_name


# ── Reporting date / period ───────────────────────────────────────────────────

@dataclass
class ReportPeriod:
    start: date
    end: date
    label: str          # what the user wrote, normalised ("31-Mar-2025", "Q1 2025", "March 2025")

    @property
    def is_single_day(self) -> bool:
        return self.start == self.end


_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
_MONTHS["sept"] = 9
_MON_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

# Multi-period wording: an explicit single period must NOT be forced on these.
_MULTI_PERIOD_RE = re.compile(
    r"\b(trend|trends|over\s+time|history|historical|time\s+series|between|compar\w*|versus|vs\.?|"
    r"growth|yoy|qoq|each\s+(month|quarter|year|period)|all\s+(dates|periods|quarters|months|years)|"
    r"(last|past|previous|prior)\s+\d+|since)\b",
    re.IGNORECASE,
)


def _year(y: str) -> int:
    n = int(y)
    return n + 2000 if n < 100 else n


def _month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def extract_report_date(query: str, today: date | None = None) -> ReportPeriod | None:
    """The single reporting date or period the question names, or None.

    Handles: 2025-03-31, 31-03-2025, 31/03/25, 31.03.2025 (day first),
    31-Mar-2025, 31 March 2025, March 31 2025, March 2025 / Mar-25,
    Q1 2025 / 2025 Q1 / Q1 FY25, FY2024 / FY24, "year 2024" / "in 2024".
    Relative phrases ("last quarter") and multi-period questions are left to
    the existing relative-time resolver and latest-date logic (returns None)."""
    q = (query or "").lower()
    if not q.strip() or _MULTI_PERIOD_RE.search(q):
        return None

    # ISO yyyy-mm-dd
    m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", q)
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            return ReportPeriod(d, d, d.strftime("%d-%b-%Y"))

    # dd-mm-yyyy / dd/mm/yy (day first; swapped when the first part cannot be a day-month)
    m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b", q)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), _year(m.group(3))
        d = _safe_date(y, b, a) or _safe_date(y, a, b)
        if d:
            return ReportPeriod(d, d, d.strftime("%d-%b-%Y"))

    # 31-Mar-2025 / 31 March 2025 / 31st march, 2025
    m = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s\-/]*{_MON_RE}[\s\-/,]*(\d{{2,4}})\b", q)
    if m:
        d = _safe_date(_year(m.group(3)), _MONTHS[m.group(2)[:3]], int(m.group(1)))
        if d:
            return ReportPeriod(d, d, d.strftime("%d-%b-%Y"))

    # March 31, 2025
    m = re.search(rf"\b{_MON_RE}\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", q)
    if m:
        d = _safe_date(int(m.group(3)), _MONTHS[m.group(1)[:3]], int(m.group(2)))
        if d:
            return ReportPeriod(d, d, d.strftime("%d-%b-%Y"))

    # Q1 2025 / Q1 FY2025 / Q1-25 / 2025 Q1
    m = re.search(r"\bq([1-4])[\s\-']*(?:fy)?[\s\-']*(\d{2,4})\b", q) or re.search(r"\b(\d{4})[\s\-]*q([1-4])\b", q)
    if m:
        if m.re.pattern.startswith(r"\bq"):
            qn, y = int(m.group(1)), _year(m.group(2))
        else:
            y, qn = int(m.group(1)), int(m.group(2))
        start = date(y, 3 * qn - 2, 1)
        return ReportPeriod(start, _month_end(y, 3 * qn), f"Q{qn} {y}")

    # March 2025 / Mar-25 / Mar'25
    m = re.search(rf"\b{_MON_RE}[\s\-',]*(\d{{4}}|\d{{2}})\b", q)
    if m:
        mon = _MONTHS[m.group(1)[:3]]
        y = _year(m.group(2))
        return ReportPeriod(date(y, mon, 1), _month_end(y, mon), date(y, mon, 1).strftime("%B %Y"))

    # FY2024 / FY 24 / financial year 2024  (calendar year; QCB/CIMS fiscal = calendar)
    m = re.search(r"\b(?:fy|financial\s+year|fiscal\s+year)[\s\-']*(\d{4}|\d{2})\b", q)
    if m:
        y = _year(m.group(1))
        return ReportPeriod(date(y, 1, 1), date(y, 12, 31), f"FY{y}")

    # a bare year ("for 2024", "year 2024", "in 2024") — only when nothing else matched
    m = re.search(r"\b(?:year|for|in|of|during)\s+(19\d{2}|20\d{2})\b", q)
    if m:
        y = int(m.group(1))
        return ReportPeriod(date(y, 1, 1), date(y, 12, 31), str(y))

    return None
