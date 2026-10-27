"""Cell-location resolver (prototype): from an error's (concept, context) to where the data lives.

For a failing fact the error file always names the CONTEXT and the value; the instance XML next to it
names the CONCEPT. From the return's own metadata this module finds:

    layout  -> sheet      -> cell code  (+ row~col index)  -> table / sheet name

using only files in <repo>/DataBase/<form id>/ :
    PreLnkBases.xml  layout id -> layout name                 (Mapping_<id>.xml belongs to that layout)
    Mapping_<id>.xml rows: concept (PriEle), dimension members (DimDom), cell code (Code), Cell "r~c"
    XML_Query.xml    layout (TemplateId) -> Excel sheet and range, parsed from "From [Sheet$A1:B2]"

Nothing is specific to any return. When a link cannot be resolved the result says so ("unresolved") and
lists what it did find; it never guesses. Read-only. No imports from the chatbot.
"""
from __future__ import annotations

import glob
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

_RANGE = re.compile(r"\[\s*'?([^\]$']+?)'?\s*\$\s*([A-Za-z]+\d+(?::[A-Za-z]+\d+)?)\s*\]")
_LAYOUT_SUFFIX = re.compile(r"_layout\d+$", re.I)
_COLUMN_SELECT = re.compile(
    r"F1\s*&\s*'([^']*)'\s*as\s+Description\s*,\s*F(\d+)\s+as\s+Val\s+From\s+\[\s*'?([^\]$']+?)'?\s*\$\s*([A-Za-z]+\d+:[A-Za-z]+\d+)\s*\]",
    re.I)
_XBRLI_NS = ("http://www.xbrl.org/2003/instance", "http://www.xbrl.org/2003/linkbase", "http://xbrl.org/2006/xbrldi")


def local(qname: str) -> str:
    """'rbi-core:ComplaintsPending' -> 'ComplaintsPending'  (also accepts '{ns}Local')."""
    q = (qname or "").strip()
    if q.startswith("{"):
        return q.rsplit("}", 1)[-1]
    return q.rsplit(":", 1)[-1]


def norm_value(text: str) -> str:
    """A comparable form of a reported value: numbers compare as numbers, anything else as stripped text."""
    t = (text or "").strip().replace(",", "")
    try:
        d = Decimal(t)
        return format(d.normalize(), "f")
    except InvalidOperation:
        return (text or "").strip()


# ── instance document: contexts and facts ────────────────────────────────────

@dataclass
class Context:
    id: str
    explicit: frozenset = frozenset()     # {(axis_local, member_local)}
    typed: frozenset = frozenset()        # {(axis_local, typed value)}


@dataclass
class Fact:
    concept: str                          # local name
    qname: str
    context: str
    unit: str
    value: str


@dataclass
class Instance:
    contexts: dict[str, Context]
    facts: list[Fact]
    by_ctx_value: dict[tuple[str, str], list[Fact]]


def read_instance(path: str) -> Instance:
    contexts: dict[str, Context] = {}
    facts: list[Fact] = []
    ns_prefix: dict[str, str] = {}
    for event, el in ET.iterparse(path, events=("start-ns", "end")):
        if event == "start-ns":
            prefix, uri = el
            ns_prefix.setdefault(uri, prefix)
            continue
        tag = el.tag
        if not isinstance(tag, str):
            continue
        uri = tag[1:].split("}")[0] if tag.startswith("{") else ""
        lname = local(tag)
        if uri == _XBRLI_NS[0] and lname == "context":
            explicit, typed = set(), set()
            for m in el.iter():
                ml = local(m.tag)
                if ml == "explicitMember":
                    explicit.add((local(m.get("dimension", "")), local((m.text or "").strip())))
                elif ml == "typedMember":
                    inner = next(iter(m), None)
                    typed.add((local(m.get("dimension", "")), ((inner.text or "").strip() if inner is not None else "")))
            cid = el.get("id", "")
            contexts[cid] = Context(cid, frozenset(explicit), frozenset(typed))
            el.clear()
        elif uri not in _XBRLI_NS and el.get("contextRef"):
            facts.append(Fact(lname, f"{ns_prefix.get(uri, '')}:{lname}", el.get("contextRef", ""),
                              el.get("unitRef", ""), (el.text or "").strip()))
    by: dict[tuple[str, str], list[Fact]] = {}
    for f in facts:
        by.setdefault((f.context, norm_value(f.value)), []).append(f)
    return Instance(contexts, facts, by)


# ── form metadata ────────────────────────────────────────────────────────────

@dataclass
class MapRow:
    layout_id: str
    cell: str                             # "r~c"
    code: str
    concept: str                          # local name of PriEle
    explicit: frozenset                   # {(axis_local, member_local)}
    typed_axes: frozenset                 # axes that carry a typed domain (single token in DimDom)
    multiplier: int = 1                   # template scale: instance value = workbook value * multiplier


@dataclass
class FormMeta:
    form_id: str
    folder: str
    layouts: dict[str, str] = field(default_factory=dict)             # layout id -> layout name
    layout_axes: dict[str, set] = field(default_factory=dict)         # layout id -> every dimension axis it uses
    rows_by_concept: dict[str, list[MapRow]] = field(default_factory=dict)
    sheets: dict[str, list[tuple[str, str]]] = field(default_factory=dict)   # layout id -> [(sheet, range)]
    staging: dict[tuple[str, str], str] = field(default_factory=dict)        # (layout id, code) -> "row label" + "_SUFFIX"
    columns: dict[str, list[tuple[str, int, str, str]]] = field(default_factory=dict)  # layout id -> [(suffix, F<n>, sheet, range)]


def _parse_dimdom(text: str) -> tuple[frozenset, frozenset]:
    explicit, typed = set(), set()
    for part in (text or "").split("||"):
        bits = [b.strip() for b in part.split("|")]
        if len(bits) >= 2 and bits[0] and bits[1]:
            explicit.add((local(bits[0]), local(bits[1])))
        elif len(bits) == 1 and bits[0]:
            typed.add(local(bits[0]))
    return frozenset(explicit), frozenset(typed)


def load_form(repo: str, form_id: str) -> FormMeta:
    return load_form_folder(os.path.join(repo, "DataBase", form_id), form_id)


def load_form_folder(folder: str, form_id: str = "") -> FormMeta:
    """The same metadata, read straight from a form's metadata folder (e.g. one copied from a server)."""
    meta = FormMeta(form_id or os.path.basename(folder), folder)

    pri_ids: dict[str, dict[str, str]] = {}                    # layout id -> {PriEle id -> concept local name}
    dim_ids: dict[str, dict[str, tuple[str, str]]] = {}        # layout id -> {DimDom id -> (axis, member)}
    path = os.path.join(folder, "PreLnkBases.xml")
    if os.path.isfile(path):
        for el in ET.parse(path).getroot().iter("PreLnkBase"):
            lid_ = el.get("Id", "")
            meta.layouts[lid_] = el.get("Name", "")
            pri_ids[lid_] = {e.get("Id", ""): local(e.get("Pri", "")) for e in el.iter("PriEle") if e.get("Pri")}
            dim_ids[lid_] = {e.get("Id", ""): (local(e.get("Dim", "")), local(e.get("Dom", "")))
                             for e in el.iter("DimDom") if e.get("Dim")}

    for p in glob.glob(os.path.join(folder, "Mapping_*.xml")):
        lid = re.search(r"Mapping_(\d+)\.xml$", p, re.I)
        if not lid:
            continue                       # e.g. Mapping_2_wring.xml: not a layout mapping
        axes = meta.layout_axes.setdefault(lid.group(1), set())
        for el in ET.parse(p).getroot().iter("Row"):
            code, pri = el.get("Code", ""), el.get("PriEle", "")
            if pri.isdigit():                                  # some forms store ids that PreLnkBases.xml resolves
                pri = pri_ids.get(lid.group(1), {}).get(pri, pri)
            dd = el.get("DimDom", "")
            if dd and "|" not in dd and all(t.strip().isdigit() for t in re.split(r"[,;]", dd)):
                ids = [dim_ids.get(lid.group(1), {}).get(t.strip()) for t in re.split(r"[,;]", dd)]
                explicit, typed = frozenset(i for i in ids if i), frozenset()
            else:
                explicit, typed = _parse_dimdom(dd)
            axes |= {a for a, _ in explicit} | set(typed)     # axis rows (no PriEle) declare the layout's axes
            if not code or not pri:
                continue
            try:
                mult = int(el.get("Multiplier") or 1) or 1
            except ValueError:
                mult = 1
            row = MapRow(lid.group(1), el.get("Cell", ""), code, local(pri), explicit, typed, mult)
            meta.rows_by_concept.setdefault(row.concept, []).append(row)

    path = os.path.join(folder, "XML_Query.xml")
    if os.path.isfile(path):
        for el in ET.parse(path).getroot().iter("Row"):
            tid = el.get("TemplateId", "")
            sql = (el.findtext("SelectQuery") or "")
            for sheet, rng in _RANGE.findall(sql):
                meta.sheets.setdefault(tid, [])
                if (sheet, rng) not in meta.sheets[tid]:
                    meta.sheets[tid].append((sheet, rng))
            # "Select F1 & '_TFCE' as Description, F2 as Val From [Sheet$B7:AF20]": column F2 holds the "_TFCE" values
            for suffix, fnum, sheet, rng in _COLUMN_SELECT.findall(sql):
                entry = (suffix, int(fnum), sheet, rng)
                meta.columns.setdefault(tid, [])
                if entry not in meta.columns[tid]:
                    meta.columns[tid].append(entry)

    path = os.path.join(folder, "Staging.xml")
    if os.path.isfile(path):
        for el in ET.parse(path).getroot().iter("Row"):
            meta.staging[(el.get("PreLnkBaseId", ""), el.get("Code", ""))] = el.get("CodeDescription", "")
    return meta


# ── resolution ───────────────────────────────────────────────────────────────

@dataclass
class Location:
    layout_id: str
    layout_name: str
    table_name: str                       # layout name without "_LayoutN"  (a derived name - see confidence note)
    sheets: list[str]
    cell_code: str
    cell_index: str
    unexplained: int                      # context dimensions the mapping row does not account for (0 = exact)


def resolve(meta: FormMeta, concept: str, ctx: Context | None) -> list[Location]:
    """All mapping rows that could hold this fact, best match first.

    A row is a candidate when it has the concept, the members it names are in the context, and the layout
    it belongs to uses every dimension axis the context carries. Candidates are ranked by how closely the
    layout's axes equal the context's axes, then by how few context members the row leaves unexplained.
    """
    rows = meta.rows_by_concept.get(local(concept), [])
    if not rows:
        return []
    ctx_explicit = set(ctx.explicit) if ctx else set()
    ctx_axes = ({a for a, _ in ctx.explicit} | {a for a, _ in ctx.typed}) if ctx else set()
    out: dict[tuple[str, str], tuple[tuple[int, int], Location]] = {}
    for r in rows:
        if not r.explicit <= ctx_explicit:
            continue                       # the row requires a member the fact does not have
        layout_axes = meta.layout_axes.get(r.layout_id, set())
        if not ctx_axes <= layout_axes:
            continue                       # the context carries an axis this layout does not use
        unexplained = len(ctx_explicit - r.explicit)
        axis_gap = len(layout_axes ^ ctx_axes)
        name = meta.layouts.get(r.layout_id, "")
        loc = Location(r.layout_id, name, _LAYOUT_SUFFIX.sub("", name),
                       sorted({s for s, _ in meta.sheets.get(r.layout_id, [])}), r.code, r.cell, unexplained)
        key = (r.layout_id, r.code)
        rank = (axis_gap, unexplained)
        if key not in out or rank < out[key][0]:
            out[key] = (rank, loc)
    ordered = sorted(out.values(), key=lambda t: (t[0], t[1].layout_id, t[1].cell_code))
    return [loc for _, loc in ordered]


def identify_fact(inst: Instance, context: str, value: str) -> list[Fact]:
    """Facts of the instance reported in `context` with this value (the concept is read from them)."""
    return inst.by_ctx_value.get((context, norm_value(value)), [])


def resolve_relaxed(meta: FormMeta, concept: str, ctx: Context | None) -> list[Location]:
    """For a fact whose dimension combination matches NO layout (typically a dimension error): the layouts
    that carry the concept at all, closest axis match first. These are 'where the figure is supposed to
    live', not a confirmed location - the caller must say so."""
    rows = meta.rows_by_concept.get(local(concept), [])
    ctx_axes = ({a for a, _ in ctx.explicit} | {a for a, _ in ctx.typed}) if ctx else set()
    out: dict[tuple[str, str], tuple[int, Location]] = {}
    for r in rows:
        layout_axes = meta.layout_axes.get(r.layout_id, set())
        gap = len(layout_axes ^ ctx_axes)
        name = meta.layouts.get(r.layout_id, "")
        loc = Location(r.layout_id, name, _LAYOUT_SUFFIX.sub("", name),
                       sorted({sh for sh, _ in meta.sheets.get(r.layout_id, [])}), r.code, r.cell, gap)
        key = (r.layout_id, r.code)
        if key not in out or gap < out[key][0]:
            out[key] = (gap, loc)
    return [loc for _, loc in sorted(out.values(), key=lambda t: (t[0], t[1].layout_id, t[1].cell_code))]
