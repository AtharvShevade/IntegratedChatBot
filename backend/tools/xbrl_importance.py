# xbrl_importance.py — regulatory-importance scoring for XBRL variance analysis.
#
# WHY THIS EXISTS
# ---------------
# xbrl_comparator ranks variance rows by how much a number MOVED. That answers
# "what changed?" but not "what matters?". A 400% swing on a memorandum note and
# a 12% swing on gross NPAs are not the same finding, and a concept-by-concept
# table cannot express the difference.
#
# The return's own taxonomy already states which figures the regulator treats as
# important. Nothing here is hand-written per return; every signal below is read
# out of the taxonomy folder that ships with the filing:
#
#   1. REFERENCE LINKBASE  — a concept carrying an <...:Circular> reference is
#      mandated by a named regulatory circular. Concepts with no reference are
#      supporting/derived fields. This is the single strongest signal.
#   2. ROLE SCHEMA         — <link:definition>[NNNN] Title</link:definition>
#      gives every concept a business SECTION and an ordinal. Low ordinals are
#      the return's original core mandate; high ones are later bolt-ons.
#   3. FORMULA LINKBASES   — the count of value/existence assertions touching a
#      concept is how hard the regulator validates it. Regulators validate
#      hardest where misreporting costs the most.
#   4. WARNING vs ERROR    — assertions living in a linkbase whose name marks it
#      as warnings are advisory; everything else is blocking. Blocking beats
#      advisory.
#   5. AMENDMENT RECENCY   — dated formula files (in-rbi-Sep2017, cimsSep20,
#      Nov2021, Mar2022 …) are a regulatory changelog. A concept re-validated in
#      a recent amendment is one the regulator has recently tightened.
#
# EVERYTHING FAILS SOFT. No taxonomy folder, unreadable files, malformed XML or
# an unrecognised layout all yield None/{}/0 and a log line — never an
# exception. When the index is unavailable the comparator behaves exactly as it
# did before this module existed.

from __future__ import annotations

import logging
import math
import os
import re
import threading
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

__all__ = [
    "ImportanceIndex",
    "get_importance_index",
    "group_by_importance",
    "format_importance_report",
    "TIER_ORDER",
]

_LINK = "{http://www.xbrl.org/2003/linkbase}"
_XLINK = "{http://www.w3.org/1999/xlink}"

# "[2050] Movement in provisions for NPAs in loans advances"
_RE_SECTION_DEF = re.compile(r"^\s*\[(\d+)\]\s*(.+?)\s*$")

# Assertion elements in a formula linkbase, whatever prefix the file uses.
_RE_ASSERTION = re.compile(r"<\w+:(?:value|existence|consistency)Assertion\b", re.I)

# <cf:qname>in-rbi-rep:GrossNPAs</cf:qname> — how formula filters name a concept.
_RE_QNAME = re.compile(r"<\w*:?qname\s*>\s*[\w.-]*:?([\w.-]+)\s*</", re.I)

# Locator hrefs — '../core/in-rbi-rep.xsd#in-rbi-rep_GrossNPAs' → 'GrossNPAs'.
# The fragment is 'prefix_LocalName'; the prefix itself may contain hyphens, so
# we take everything after the LAST underscore that precedes a capital letter.
_RE_HREF_FRAGMENT = re.compile(r'href="[^"#]*#([A-Za-z0-9_.\-]+)"')

# Dated amendment files: 'in-rbi-Sep2017', 'cimsSep20_1', 'raq-Jan21', 'Mar2022'.
_RE_AMENDMENT = re.compile(
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-_]?(\d{4}|\d{2})(?![\d])",
    re.I,
)

# Filename markers that make a formula linkbase advisory rather than blocking.
_ADVISORY_MARKERS = ("warning", "advisory", "soft", "info")

# ── Score weights (sum to 100) ───────────────────────────────────────────────
# Ordered by how directly each signal states regulatory intent.
W_MANDATE = 25    # named circular in the reference linkbase
W_RULES = 25      # validation-assertion density
W_SECTION = 20    # position in the return's core mandate
W_BLOCKING = 15   # blocking (error) rules present, not warnings only
W_RECENCY = 15    # touched by a recent regulatory amendment

TIER_ORDER = ["Critical", "High", "Medium", "Low"]

_TIER_CUTOFFS = ((70.0, "Critical"), (45.0, "High"), (20.0, "Medium"))

# An amendment this recent or later counts as "current supervisory focus".
# Older files still score, on a linear ramp from _RECENCY_FLOOR_YEAR.
_RECENCY_FLOOR_YEAR = 2015
_RECENCY_CEIL_YEAR = 2024


def _tier_for(score: float) -> str:
    for cutoff, tier in _TIER_CUTOFFS:
        if score >= cutoff:
            return tier
    return "Low"


def _local_name(fragment: str) -> str:
    """'in-rbi-rep_GrossNPAs' → 'GrossNPAs'; 'GrossNPAs' → 'GrossNPAs'.

    Taxonomy element ids are 'prefix_LocalName' and the prefix may itself
    contain underscores or hyphens ('in-rbi-raq_gen'), so splitting on the
    first underscore is wrong. The local name always begins at the last
    underscore, because XBRL element names are PascalCase and contain none.
    """
    return fragment.rsplit("_", 1)[-1] if "_" in fragment else fragment


def _amendment_year(filename: str) -> int | None:
    """Latest regulatory-amendment year encoded in a formula linkbase filename."""
    years: list[int] = []
    for _month, digits in _RE_AMENDMENT.findall(filename):
        try:
            n = int(digits)
        except ValueError:
            continue
        year = n if n >= 1000 else 2000 + n
        if _RECENCY_FLOOR_YEAR - 10 <= year <= _RECENCY_CEIL_YEAR + 10:
            years.append(year)
    return max(years) if years else None


class ImportanceIndex:
    """Regulatory-importance view of one return's taxonomy folder.

    Construction only records the roots. Every linkbase is parsed lazily on the
    first call to `score_concept` and then memoised, so building an index for a
    return that is never scored costs nothing.
    """

    def __init__(self, roots: tuple[str, ...]) -> None:
        self.roots = roots
        self._lock = threading.RLock()
        self._built = False

        # role URI → {"code": "2050", "ordinal": 2050, "title": str}
        self._sections: dict[str, dict] = {}
        # concept local name → role URI (first/lowest-ordinal section wins)
        self._concept_section: dict[str, str] = {}
        # concept local name → sorted list of circular identifiers
        self._concept_circulars: dict[str, list[str]] = {}
        # concept local name → {"blocking": int, "advisory": int, "year": int|None}
        self._concept_rules: dict[str, dict] = {}
        # role URI → core factor in [0, 1]; 0 for evidence-free sections
        self._section_core: dict[str, float] = {}
        # memoised per-concept results
        self._scores: dict[str, dict] = {}

    # ── file discovery ──────────────────────────────────────────────────────

    def _walk(self, suffixes: tuple[str, ...]) -> list[str]:
        found: list[str] = []
        for root in self.roots:
            try:
                for dirpath, _dirs, files in os.walk(root):
                    for fn in files:
                        if fn.lower().endswith(suffixes):
                            found.append(os.path.join(dirpath, fn))
            except OSError as exc:
                logger.warning("[importance] cannot walk %s: %s", root, exc)
        return sorted(found)

    @staticmethod
    def _read(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read()
        except OSError as exc:
            logger.debug("[importance] unreadable %s: %s", path, exc)
            return ""

    # ── linkbase parsers ────────────────────────────────────────────────────

    def _parse_sections(self, xsd_paths: list[str]) -> None:
        """Role schema → section code, ordinal and business title."""
        for path in xsd_paths:
            text = self._read(path)
            if "roleType" not in text:
                continue
            try:
                root = ET.fromstring(text)
            except ET.ParseError as exc:
                logger.debug("[importance] bad role xsd %s: %s", path, exc)
                continue
            for rt in root.iter(f"{_LINK}roleType"):
                uri = rt.get("roleURI", "")
                if not uri:
                    continue
                definition = ""
                for d in rt.iter(f"{_LINK}definition"):
                    definition = (d.text or "").strip()
                    break
                m = _RE_SECTION_DEF.match(definition)
                if not m:
                    # Layout/table roles carry no [NNNN] code — not business
                    # sections, and including them would double-count concepts.
                    continue
                code, title = m.group(1), m.group(2)
                self._sections[uri] = {
                    "code": code,
                    "ordinal": int(code),
                    "title": title,
                }

    def _parse_presentation(self, xml_paths: list[str]) -> None:
        """Presentation linkbase → concept → business section.

        A concept can appear in several sections; the LOWEST ordinal wins, so a
        figure is attributed to the most core section that presents it.
        """
        for path in xml_paths:
            text = self._read(path)
            if "presentationLink" not in text:
                continue
            try:
                root = ET.fromstring(text)
            except ET.ParseError as exc:
                logger.debug("[importance] bad presentation %s: %s", path, exc)
                continue
            for plink in root.iter(f"{_LINK}presentationLink"):
                uri = plink.get(f"{_XLINK}role", "")
                section = self._sections.get(uri)
                if section is None:
                    continue
                ordinal = section["ordinal"]
                for loc in plink.iter(f"{_LINK}loc"):
                    href = loc.get(f"{_XLINK}href", "")
                    if "#" not in href:
                        continue
                    name = _local_name(href.split("#", 1)[1])
                    if not name:
                        continue
                    current = self._concept_section.get(name)
                    if current is None or ordinal < self._sections[current]["ordinal"]:
                        self._concept_section[name] = uri

    def _parse_references(self, xml_paths: list[str]) -> None:
        """Reference linkbase → concept → the circular(s) that mandate it.

        Locator label → concept, referenceArc label → resource, resource text →
        circular id. Walking the arcs (rather than assuming document order)
        keeps this correct for linkbases that group all resources at the end.
        """
        for path in xml_paths:
            text = self._read(path)
            if "referenceLink" not in text:
                continue
            try:
                root = ET.fromstring(text)
            except ET.ParseError as exc:
                logger.debug("[importance] bad reference linkbase %s: %s", path, exc)
                continue
            for rlink in root.iter(f"{_LINK}referenceLink"):
                loc_concept: dict[str, str] = {}
                for loc in rlink.iter(f"{_LINK}loc"):
                    href = loc.get(f"{_XLINK}href", "")
                    label = loc.get(f"{_XLINK}label", "")
                    if label and "#" in href:
                        loc_concept[label] = _local_name(href.split("#", 1)[1])

                res_text: dict[str, list[str]] = {}
                for res in rlink.iter(f"{_LINK}reference"):
                    label = res.get(f"{_XLINK}label", "")
                    if not label:
                        continue
                    parts = [
                        (child.text or "").strip()
                        for child in res
                        if (child.text or "").strip()
                    ]
                    if parts:
                        res_text[label] = parts

                for arc in rlink.iter(f"{_LINK}referenceArc"):
                    concept = loc_concept.get(arc.get(f"{_XLINK}from", ""))
                    parts = res_text.get(arc.get(f"{_XLINK}to", ""))
                    if not concept or not parts:
                        continue
                    bucket = self._concept_circulars.setdefault(concept, [])
                    for p in parts:
                        if p not in bucket:
                            bucket.append(p)

    def _parse_formulas(self, xml_paths: list[str]) -> None:
        """Formula linkbases → per-concept blocking/advisory rule counts.

        Regex over the raw text rather than an ElementTree parse: formula
        linkbases here reach 500 KB, use a dozen namespace prefixes, and we need
        only two facts from each — how many assertions it holds, and which
        concepts it names. Both are unambiguous lexically.
        """
        for path in xml_paths:
            text = self._read(path)
            assertions = len(_RE_ASSERTION.findall(text))
            if not assertions:
                continue
            fname = os.path.basename(path)
            advisory = any(m in fname.lower() for m in _ADVISORY_MARKERS)
            year = _amendment_year(fname)

            concepts = set(_RE_QNAME.findall(text))
            for frag in _RE_HREF_FRAGMENT.findall(text):
                # Skip the standard XBRL spec resources every formula file links
                # to (generic-label.xsd#standard-label and friends) — they are
                # not the return's concepts.
                if frag.count("-") and frag[:1].islower():
                    continue
                name = _local_name(frag)
                if name and name[:1].isupper():
                    concepts.add(name)

            if not concepts:
                continue
            # An assertion names a handful of concepts; attributing the file's
            # full assertion count to each would inflate a concept that appears
            # in one rule of a 49-rule file. Share it out instead.
            share = assertions / len(concepts)
            for name in concepts:
                entry = self._concept_rules.setdefault(
                    name, {"blocking": 0.0, "advisory": 0.0, "year": None}
                )
                if advisory:
                    entry["advisory"] += share
                else:
                    entry["blocking"] += share
                if year and (entry["year"] is None or year > entry["year"]):
                    entry["year"] = year

    def _compute_section_core(self) -> None:
        """How central each section is to the return's regulatory purpose.

        The obvious implementation — rank by the [NNNN] ordinal — is wrong, and
        measurably so: it puts '[1000] General information about reporting
        institution' first, which is administrative preamble, ahead of every
        risk section in the filing. Ordinal tells you when a section was added,
        not how much it matters.

        So the primary signal is EVIDENCE DENSITY: what fraction of a section's
        concepts are named by a circular, and what fraction carry blocking
        validation. A section where most figures are mandated and validated is
        a section the regulator built the return around. General Information is
        mostly free text with one or two format checks and lands near the
        bottom on its own numbers. Ordinal survives only as a 30% tiebreaker,
        which is roughly the weight it deserves.
        """
        # One pass: section URI → member concept names.
        members: dict[str, list[str]] = {}
        for name, uri in self._concept_section.items():
            members.setdefault(uri, []).append(name)

        raw: dict[str, float] = {}
        for uri, _section in self._sections.items():
            names = members.get(uri, [])
            if not names:
                self._section_core[uri] = 0.0
                continue
            mandated = sum(1 for n in names if self._concept_circulars.get(n))
            blocking = sum(
                1 for n in names
                if (self._concept_rules.get(n) or {}).get("blocking", 0) > 0
            )
            total = len(names)
            # Mandate is the rarer and stronger signal, so it is weighted above
            # validation coverage rather than averaged with it.
            raw[uri] = 0.6 * (mandated / total) + 0.4 * (blocking / total)

        if not raw:
            return

        # Normalise density to [0, 1] against the strongest section present, so
        # the scale adapts to a taxonomy whose references are sparse (RAQ maps
        # only two circulars) instead of collapsing every section to near-zero.
        peak = max(raw.values()) or 1.0

        ordinals = sorted({self._sections[u]["ordinal"] for u in raw})
        span = len(ordinals) - 1

        for uri, density in raw.items():
            ordinal_rank = ordinals.index(self._sections[uri]["ordinal"])
            ordinal_factor = 1.0 - (ordinal_rank / span) if span else 1.0
            self._section_core[uri] = min(
                1.0, 0.7 * (density / peak) + 0.3 * ordinal_factor
            )

    # ── build ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        with self._lock:
            if self._built:
                return
            xsd_paths = self._walk((".xsd",))
            xml_paths = self._walk((".xml",))
            self._parse_sections(xsd_paths)
            self._parse_presentation(xml_paths)
            self._parse_references(xml_paths)
            self._parse_formulas(xml_paths)
            self._compute_section_core()
            self._built = True
            logger.info(
                "[importance] built index: sections=%d mapped_concepts=%d "
                "mandated=%d rule_bearing=%d roots=%s",
                len(self._sections),
                len(self._concept_section),
                len(self._concept_circulars),
                len(self._concept_rules),
                [os.path.basename(r) for r in self.roots],
            )

    @property
    def is_usable(self) -> bool:
        """True when the taxonomy yielded enough structure to rank anything."""
        self._build()
        return bool(self._sections and self._concept_section)

    # ── scoring ─────────────────────────────────────────────────────────────

    def score_concept(self, concept: str) -> dict:
        """Regulatory-importance profile for one concept.

        Returns a dict that is always populated (never None) so callers need no
        branch: an unrecognised concept scores 0 in the 'Unclassified' section.

            {
              "score": float 0-100, "tier": str,
              "section": str, "section_code": str, "section_ordinal": int,
              "circulars": [str], "blocking_rules": int, "advisory_rules": int,
              "last_amended": int|None, "drivers": [str],
            }
        """
        self._build()
        cached = self._scores.get(concept)
        if cached is not None:
            return cached

        section_uri = self._concept_section.get(concept)
        section = self._sections.get(section_uri or "", None)
        circulars = self._concept_circulars.get(concept, [])
        rules = self._concept_rules.get(concept) or {}
        blocking = float(rules.get("blocking", 0.0))
        advisory = float(rules.get("advisory", 0.0))
        year = rules.get("year")

        drivers: list[str] = []

        # 1 — mandate: the concept is named by a regulatory circular.
        mandate = W_MANDATE if circulars else 0.0
        if circulars:
            drivers.append(f"Mandated by circular {circulars[0]}")

        # 2 — validation density. Log-scaled: the step from 0 to 1 rule matters
        # far more than the step from 20 to 21, and a linear scale would let one
        # heavily-validated concept flatten every other.
        total_rules = blocking + advisory
        if total_rules > 0:
            rule_score = W_RULES * min(1.0, math.log10(1 + total_rules) / math.log10(21))
            drivers.append(
                f"{total_rules:.0f} validation rule(s) reference this figure"
            )
        else:
            rule_score = 0.0

        # 3 — position in the return's core mandate.
        core_factor = self._section_core.get(section_uri or "", 0.0)
        section_score = W_SECTION * core_factor
        if section and core_factor >= 0.6:
            drivers.append(f"Core section [{section['code']}] {section['title']}")

        # 4 — blocking beats advisory. A figure whose rules are all warnings is
        # one the regulator wants to see but will still accept as filed.
        if blocking > 0:
            blocking_score = W_BLOCKING
            drivers.append("Has blocking (error-severity) validation")
        elif advisory > 0:
            blocking_score = W_BLOCKING * 0.3
            drivers.append("Advisory (warning-only) validation")
        else:
            blocking_score = 0.0

        # 5 — recency of regulatory attention.
        if year:
            span = _RECENCY_CEIL_YEAR - _RECENCY_FLOOR_YEAR
            ramp = (year - _RECENCY_FLOOR_YEAR) / span if span else 1.0
            recency_score = W_RECENCY * max(0.0, min(1.0, ramp))
            if year >= 2020:
                drivers.append(f"Re-validated in a {year} amendment")
        else:
            recency_score = 0.0

        score = round(
            mandate + rule_score + section_score + blocking_score + recency_score, 1
        )
        result = {
            "score": score,
            "tier": _tier_for(score),
            "section": section["title"] if section else "Unclassified",
            "section_code": section["code"] if section else "",
            "section_ordinal": section["ordinal"] if section else 999_999,
            "circulars": list(circulars),
            "blocking_rules": int(round(blocking)),
            "advisory_rules": int(round(advisory)),
            "last_amended": year,
            "drivers": drivers,
        }
        self._scores[concept] = result
        return result


# ---------------------------------------------------------------------------
# Index resolution — cached per taxonomy folder set
# ---------------------------------------------------------------------------

_CACHE_LOCK = threading.Lock()
_INDEX_CACHE: dict[tuple, ImportanceIndex] = {}


def _tree_signature(roots: tuple[str, ...]) -> tuple:
    """Cheap invalidation key — each root's mtime plus its subdirectories'.

    Mirrors taxonomy_index._tree_signature deliberately: a directory mtime
    changes when a file inside is added, removed or replaced, which is what a
    redeployed taxonomy looks like, and a full recursive stat on every lookup
    would be far too expensive on a request path.
    """
    sig: list[tuple] = []
    for root in roots:
        try:
            sig.append((root, os.stat(root).st_mtime))
            with os.scandir(root) as entries:
                for entry in entries:
                    if entry.is_dir():
                        sig.append((entry.path, entry.stat().st_mtime))
        except OSError:
            sig.append((root, 0.0))
    return tuple(sig)


def get_importance_index(form_id: str | None) -> ImportanceIndex | None:
    """The importance index for a return, or None when it cannot be built.

    Resolution reuses taxonomy_index's own root discovery so this module never
    invents a second, divergent idea of where a return's taxonomy lives.
    Returns None — never raises — when the folder is missing or the taxonomy
    yields no usable section structure.
    """
    if not form_id:
        return None
    try:
        from backend.tools.taxonomy_index import _candidate_roots

        roots = _candidate_roots(str(form_id))
    except Exception as exc:
        logger.warning("[importance] root resolution failed for %s: %s", form_id, exc)
        return None

    if not roots:
        logger.info("[importance] no taxonomy folder for form_id=%s", form_id)
        return None

    try:
        signature = (roots, _tree_signature(roots))
    except Exception:
        signature = (roots,)

    with _CACHE_LOCK:
        cached = _INDEX_CACHE.get(signature)
        if cached is not None:
            return cached

    index = ImportanceIndex(roots)
    try:
        if not index.is_usable:
            logger.info(
                "[importance] taxonomy at %s has no [NNNN] role sections — "
                "importance view unavailable for form_id=%s",
                [os.path.basename(r) for r in roots], form_id,
            )
            return None
    except Exception as exc:
        logger.warning("[importance] index build failed for %s: %s", form_id, exc)
        return None

    with _CACHE_LOCK:
        _INDEX_CACHE[signature] = index
    return index


# ---------------------------------------------------------------------------
# Grouping — variance rows → business sections ranked by regulatory importance
# ---------------------------------------------------------------------------

def _movement_score(row: dict) -> float:
    """0-100 measure of how much this row moved, magnitude-aware.

    Deliberately NOT the raw percentage: a 900% swing on a rounding-scale figure
    must not outrank a 15% swing on the loan book. compute_variance has already
    graded exactly that into `severity`, so this reuses that grade and refines it
    with the percentage inside the band rather than re-deriving a second,
    possibly contradictory, notion of materiality.
    """
    # A figure that did not move has no movement to score, however heavily
    # regulated it is. Scoring it 10 like any other low-severity row let a
    # maximally-mandated unchanged fact head the variance table — which is the
    # one thing a variance table must never do. The grouped section view is
    # where "critical area, no movement" gets said.
    if not (row.get("diff") or 0):
        return 0.0
    base = {"critical": 80.0, "high": 60.0, "medium": 35.0}.get(
        row.get("severity", ""), 10.0
    )
    pct = row.get("pct_change")
    if pct is None:
        refine = 10.0            # zero baseline — real, but no percentage to grade
    else:
        refine = min(20.0, abs(pct) / 5.0)
    return min(100.0, base + refine)


def group_by_importance(
    rows: list[dict],
    label_a: str,
    label_b: str,
    index: ImportanceIndex,
    top_rows_per_section: int = 5,
) -> list[dict]:
    """Collapse variance rows into business sections ranked by importance.

    *rows* must be the UNCAPPED compute_variance result — grouping a top-30
    slice would silently drop whole sections whose movements were individually
    too small to make that slice but collectively material.

    Each returned group:
        {
          "section", "section_code", "importance", "tier",
          "circulars", "blocking_rules", "last_amended", "drivers",
          "row_count", "significant_count", "anomaly_count", "max_severity",
          "net_diff", "gross_movement", "value_a", "value_b", "pct_change",
          "top_rows": [row, ...],       # highest-priority rows in this section
        }
    """
    buckets: dict[str, dict] = {}

    for row in rows:
        concept = row.get("concept_base") or row.get("concept", "")
        profile = index.score_concept(concept)
        key = profile["section_code"] or profile["section"]

        bucket = buckets.get(key)
        if bucket is None:
            bucket = buckets[key] = {
                "section": profile["section"],
                "section_code": profile["section_code"],
                "section_ordinal": profile["section_ordinal"],
                "importance": 0.0,
                "circulars": [],
                "blocking_rules": 0,
                "last_amended": None,
                "drivers": [],
                "row_count": 0,
                "significant_count": 0,
                "anomaly_count": 0,
                "max_severity": "low",
                "net_diff": 0.0,
                "gross_movement": 0.0,
                "value_a": 0.0,
                "value_b": 0.0,
                "_rows": [],
            }

        # A section is as important as its most important member concept: one
        # circular-mandated, heavily-validated figure makes the whole section
        # worth reading, and averaging would bury it under its own supporting
        # line items.
        # A JSON-backed profile reports score None for a concept its taxonomy
        # JSON does not classify — distinct from a real 0.0. It contributes
        # nothing to a section's importance, so read it as 0 here rather than
        # letting the comparison raise on None.
        _score = profile["score"] or 0.0
        if _score > bucket["importance"]:
            bucket["importance"] = _score
            bucket["drivers"] = list(profile["drivers"])
        for circ in profile["circulars"]:
            if circ not in bucket["circulars"]:
                bucket["circulars"].append(circ)
        bucket["blocking_rules"] = max(
            bucket["blocking_rules"], profile["blocking_rules"]
        )
        if profile["last_amended"] and (
            bucket["last_amended"] is None
            or profile["last_amended"] > bucket["last_amended"]
        ):
            bucket["last_amended"] = profile["last_amended"]

        val_a = row.get(label_a)
        val_b = row.get(label_b)
        diff = row.get("diff")
        bucket["row_count"] += 1
        if row.get("significant"):
            bucket["significant_count"] += 1
        if row.get("anomaly_flags"):
            bucket["anomaly_count"] += 1
        # Severity only counts from facts that actually moved. compute_variance
        # grades a zero-baseline row as critical because it has no percentage to
        # judge, which is right for a 0 → 50M row and wrong for a 0 → 0 one —
        # and the latter would otherwise stamp 'critical' on a section where
        # nothing happened at all.
        severity = row.get("severity", "low")
        _sev_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        if isinstance(diff, (int, float)) and diff != 0:
            if _sev_rank.get(severity, 0) > _sev_rank.get(bucket["max_severity"], 0):
                bucket["max_severity"] = severity
        if isinstance(diff, (int, float)):
            bucket["net_diff"] += diff
            bucket["gross_movement"] += abs(diff)
        if isinstance(val_a, (int, float)):
            bucket["value_a"] += val_a
        if isinstance(val_b, (int, float)):
            bucket["value_b"] += val_b

        # Row priority balances "how regulated is this?" against "how much did
        # it move?" — a heavily-mandated figure that barely moved and a trivial
        # figure that exploded both belong in the report, neither at the top.
        enriched = dict(row)
        enriched["importance"] = profile["score"]
        enriched["importance_tier"] = profile["tier"]
        enriched["section"] = profile["section"]
        enriched["section_code"] = profile["section_code"]
        enriched["mandated_by"] = list(profile["circulars"])
        enriched["blocking_rules"] = profile["blocking_rules"]
        # Unclassified (score None) ranks on movement alone — blending it as
        # 0.6*0 would push it below a genuinely low-importance concept, which
        # the data does not support.
        enriched["priority"] = (
            round(0.6 * profile["score"] + 0.4 * _movement_score(row), 1)
            if profile["score"] is not None
            else round(_movement_score(row), 1)
        )
        bucket["_rows"].append(enriched)

    groups: list[dict] = []
    for bucket in buckets.values():
        # Absolute movement breaks priority ties. Without it, a section whose
        # concepts all share one importance score (the common case — they come
        # from the same circular and the same rule set) would surface whichever
        # rows happened to be first, including ones that did not move at all.
        bucket["_rows"].sort(
            key=lambda r: (
                r["priority"],
                abs(r.get("diff") or 0.0),
                1 if r.get("significant") else 0,
            ),
            reverse=True,
        )
        # Rows that actually moved lead, ranked by priority among themselves;
        # unchanged rows fill any remaining slots. A section's top rows should
        # answer "what changed here", and a purely priority-ordered slice can
        # be entirely unchanged facts while real movements sit at position six.
        all_rows = bucket.pop("_rows")
        moved = [r for r in all_rows if (r.get("diff") or 0) != 0]
        still = [r for r in all_rows if (r.get("diff") or 0) == 0]
        bucket["moved_count"] = len(moved)
        bucket["top_rows"] = (moved + still)[:top_rows_per_section]
        bucket["all_rows"] = all_rows
        bucket["importance"] = round(bucket["importance"], 1)
        bucket["tier"] = _tier_for(bucket["importance"])
        v_b = bucket["value_b"]
        bucket["pct_change"] = (
            ((bucket["value_a"] - v_b) / abs(v_b)) * 100 if v_b else None
        )
        groups.append(bucket)

    # Importance first — the whole point is that a Critical section with a
    # modest movement outranks a Low section with a dramatic one. Gross
    # movement only orders sections that are equally regulated.
    groups.sort(
        key=lambda g: (g["importance"], g["gross_movement"]),
        reverse=True,
    )
    return groups


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _humanise(name: str, max_len: int = 46) -> str:
    words = _CAMEL_RE.sub(" ", name)
    return words if len(words) <= max_len else words[: max_len - 1] + "…"


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{v / 1_000_000_000:,.2f}B"
    if a >= 1_000_000:
        return f"{v / 1_000_000:,.2f}M"
    if a >= 1_000:
        return f"{v / 1_000:,.2f}K"
    if a >= 1:
        return f"{v:,.2f}"
    return f"{v:,.4f}"


def _pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    if v == 0:
        return "0.0%"
    sign = "+" if v > 0 else "-"
    a = abs(v)
    if a > 1_000:
        return f"{sign}>1,000%"
    # A section total that moves by a sliver of a huge base rounds to '0.0%' at
    # one decimal, which reads as "nothing happened" next to a non-zero net
    # figure. Say it is small instead of saying it is nothing.
    if a < 0.05:
        return "≈0%"
    return f"{sign}{a:.1f}%"


def format_importance_report(
    groups: list[dict],
    label_a: str,
    label_b: str,
    max_sections: int = 8,
    rows_per_section: int = 3,
) -> str:
    """Render importance-grouped variance as a plain-text chat report.

    Sections lead, concepts follow — the inverse of format_variance_table, and
    the reason this exists. Each heading states WHY the section ranks where it
    does, so the ordering is auditable rather than an opaque score.
    """
    if not groups:
        return "No comparable facts could be attributed to a business section."

    lines: list[str] = [
        f"Regulatory-Importance View  —  {label_a}  vs  {label_b}",
        "Sections ranked by what the taxonomy says the regulator cares about,",
        "not by size of movement.",
        "",
    ]

    for group in groups[:max_sections]:
        code = f"[{group['section_code']}] " if group["section_code"] else ""
        lines.append(
            f"{group['tier'].upper():<8} │ {code}{group['section']}"
        )
        lines.append(
            f"         │ importance {group['importance']:.0f}/100  ·  "
            f"{group['row_count']} fact(s)  ·  "
            f"{group.get('moved_count', 0)} changed  ·  "
            f"{group['significant_count']} significant  ·  "
            f"net {_fmt(group['net_diff'])} ({_pct(group['pct_change'])})"
        )
        why: list[str] = []
        if group["circulars"]:
            why.append(f"circular {group['circulars'][0]}")
        if group["blocking_rules"]:
            why.append(f"{group['blocking_rules']} blocking rule(s)")
        if group["last_amended"]:
            why.append(f"last amended {group['last_amended']}")
        if why:
            lines.append(f"         │ why: {' · '.join(why)}")

        # A section that did not move is a finding in its own right — a
        # critical area holding steady is worth stating — but listing three
        # rows of zeroes to say it is noise. Say it in one line instead.
        movers = [r for r in group["top_rows"] if (r.get("diff") or 0) != 0]
        if not group.get("moved_count"):
            lines.append(
                f"         │   no movement across {group['row_count']} reported fact(s)"
            )
        for row in movers[:rows_per_section]:
            concept = row.get("concept", "")
            if " [" in concept:
                idx = concept.index(" [")
                display = _humanise(concept[:idx], 40) + concept[idx:]
            else:
                display = _humanise(concept, 46)
            marker = " ⚠" if row.get("significant") else ""
            lines.append(
                f"         │   {display[:52]:<52} "
                f"{_fmt(row.get('diff')):>12}  {_pct(row.get('pct_change')):>10}{marker}"
            )
        lines.append("")

    remaining = len(groups) - max_sections
    if remaining > 0:
        lines.append(f"({remaining} further section(s) of lower regulatory importance.)")
    return "\n".join(lines).rstrip()
