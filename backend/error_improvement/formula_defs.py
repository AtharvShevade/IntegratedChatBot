"""Rule definitions from the taxonomy's XBRL formula files (<form>/Taxonomy/**/*formula*.xml).

An assertion  <va:valueAssertion id="CRMROffBS_MaxCheck_001" test="$V1 = max(($V2 - $V3), 0)">  names its operands through
variable arcs (V1, V2 ...) and filters on each variable: a concept name, explicit dimension members, and a fallbackValue
(what the operand counts as when nothing was reported). So even an operand the filer never reported has a known item.
The error file's rule name is the assertion id.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET

_XLINK = "http://www.w3.org/1999/xlink"


def _l(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _local(q: str) -> str:
    return (q or "").strip().split(":")[-1]


def _attr(el, name: str) -> str:
    return el.get(f"{{{_XLINK}}}{name}") or el.get(name) or ""


def parse_file(path: str) -> dict:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {}
    assertions, var_arcs, filter_arcs, set_filter_arcs, filters, fallback = {}, [], [], [], {}, {}
    for el in root.iter():
        t = _l(el.tag)
        if t in ("valueAssertion", "existenceAssertion"):        # an existence assertion is a "this value must be reported" rule
            assertions[_attr(el, "label") or el.get("id", "")] = {"id": el.get("id", ""), "test": el.get("test", ""), "kind": "existence" if t == "existenceAssertion" else "value"}
        elif t == "variableArc":
            var_arcs.append((_attr(el, "from"), _attr(el, "to"), el.get("name", "")))
        elif t == "variableFilterArc":
            filter_arcs.append((_attr(el, "from"), _attr(el, "to"), el.get("complement", "false") == "true"))
        elif t == "variableSetFilterArc":
            set_filter_arcs.append((_attr(el, "from"), _attr(el, "to"), el.get("complement", "false") == "true"))
        elif t == "factVariable":
            fallback[_attr(el, "label")] = el.get("fallbackValue")
        elif t == "conceptName":
            filters[_attr(el, "label")] = ("concept", [_local(q.text) for q in el.iter() if _l(q.tag) == "qname"])
        elif t == "explicitDimension":
            dim = next((_local(q.text) for d in el if _l(d.tag) == "dimension" for q in d if _l(q.tag) == "qname"), "")
            members = [_local(q.text) for m in el if _l(m.tag) == "member" for q in m.iter() if _l(q.tag) == "qname"]
            filters[_attr(el, "label")] = ("dim", (dim, members))
    out = {}
    for label, a in assertions.items():
        vars_ = {}
        for frm, to, name in var_arcs:
            if frm != label or not name:
                continue
            v = {"concepts": [], "dims": {}, "fallback": fallback.get(to)}
            for ffrm, fto, complement in filter_arcs:
                if ffrm != to or complement or fto not in filters:
                    continue
                kind, val = filters[fto]
                if kind == "concept":
                    v["concepts"] += val
                else:
                    v["dims"][val[0]] = val[1]
            vars_[name.upper()] = v
        set_dims = {}
        for sfrm, sto, complement in set_filter_arcs:
            if sfrm == label and not complement and sto in filters and filters[sto][0] == "dim":
                set_dims[filters[sto][1][0]] = filters[sto][1][1]
        out[a["id"] or label] = {"test": a["test"], "vars": vars_, "set_dims": set_dims, "kind": a.get("kind", "value")}
    return out


def load(taxonomy_dir: str) -> dict:
    """{assertion id: {'test', 'vars': {'V1': {'concepts', 'dims', 'fallback'}}, 'set_dims'}} for every formula file."""
    defs: dict = {}
    if not os.path.isdir(taxonomy_dir):
        return defs
    for root, _d, files in os.walk(taxonomy_dir):
        for f in files:
            if f.lower().endswith(".xml") and "formula" in f.lower() and not f.endswith(".bak"):
                defs.update(parse_file(os.path.join(root, f)))
    return defs
