# backend/tools/taxonomy_index.py — filesystem-level taxonomy resolution.
#
# Answers the questions a dimension or formula error needs answered, from the
# return's own taxonomy files, with no per-return code:
#
#   * what is this concept called in business language?        (label linkbase)
#   * is this axis typed or explicit?                          (xbrldt:typedDomainRef)
#   * if typed, what value does it require?                    (typed domain's XSD type + facets)
#   * if explicit, which members are allowed?                  (dimension-domain / domain-member arcs)
#   * which axes does this concept's hypercube require?        (all / hypercube-dimension arcs)
#
# WHY NOT THE PREVIOUS APPROACH
# -----------------------------
# dimension_taxonomy._find_definition_linkbases searched for
# '*<stem>*-definition.xml'. Return 2047's definition linkbase is
# 'in-rbi-rep-fmr4_def1.xml', which that pattern can never match — so all 23 of
# its dimension errors fell through to "Cannot be determined". And form_id does
# not reliably identify a taxonomy either: DataBase/4038/Taxonomy holds mpd07
# while 4038's BTDetails file is an mpd03 filing.
#
# So discovery here is by CONTENT (does this XML contain dimensional arcroles?
# does this XSD declare element definitions?) and candidates are RANKED by
# evidence (does it declare the concept we asked about?), never chosen by name.
#
# Everything is cached per taxonomy directory and invalidated on the directory
# tree's newest mtime, so a redeployed taxonomy is picked up without a restart.
# Every public function fails soft: missing folder, unreadable file, or
# malformed XML yields None/{}/[] and a log line, never an exception.

from __future__ import annotations

import logging
import os
import re
import threading
import xml.etree.ElementTree as ET

from backend import config

logger = logging.getLogger(__name__)

__all__ = [
    "TaxonomyIndex", "get_index_for_form", "get_index_for_paths",
    "humanize_local_name", "local_name",
]

_XLINK = "{http://www.w3.org/1999/xlink}"
_XBRLDT = "{http://xbrl.org/2005/xbrldt}"
_XBRLI = "{http://www.xbrl.org/2003/instance}"
_XSD = "{http://www.w3.org/2001/XMLSchema}"
_LINK = "{http://www.xbrl.org/2003/linkbase}"

_STANDARD_LABEL_ROLE = "http://www.xbrl.org/2003/role/label"

# Arcroles that identify a definition linkbase carrying dimensional structure.
_ARCROLE_ALL = "/arcrole/all"
_ARCROLE_HYPERCUBE_DIMENSION = "/arcrole/hypercube-dimension"
_ARCROLE_DIMENSION_DOMAIN = "/arcrole/dimension-domain"
_ARCROLE_DOMAIN_MEMBER = "/arcrole/domain-member"
_ARCROLE_DIMENSION_DEFAULT = "/arcrole/dimension-default"

# Folders under the active repo root that can hold taxonomy packages. Same set
# the previous implementation used, kept so no deployment layout is lost.
_TAXONOMY_ROOTS = ("DataBase", "conf", "confCims")

# Files this size or larger are skipped during content sniffing — taxonomy
# linkbases in this repo are well under it, and the cap stops a stray instance
# document or data dump from dominating index build time.
_MAX_SNIFF_BYTES = 24 * 1024 * 1024

_CACHE_LOCK = threading.Lock()
_INDEX_CACHE: dict[tuple, "TaxonomyIndex"] = {}


def local_name(qname: str) -> str:
    """'in-rbi-rep:DateAxis' -> 'DateAxis'; also strips a URI fragment id."""
    text = (qname or "").strip()
    if "#" in text:
        text = text.rsplit("#", 1)[-1]
    if ":" in text:
        text = text.rsplit(":", 1)[-1]
    return text


_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def humanize_local_name(name: str, strip_suffixes: tuple[str, ...] = ()) -> str:
    """Mechanical CamelCase split, optionally dropping a generic taxonomy
    suffix ('Axis', 'Member', 'Domain'). Acronym runs stay intact ('NPAs'),
    which a naive per-capital split would shatter."""
    text = local_name(name)
    if not text:
        return ""
    for suffix in strip_suffixes:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    words = _CAMEL_SPLIT_RE.sub(" ", text).replace("_", " ").split()
    return " ".join(words) if words else text


def _tree_signature(roots: tuple[str, ...]) -> tuple:
    """Cheap invalidation key: each root's own mtime plus its immediate
    subdirectories'.

    Deliberately NOT a full recursive walk. The cache key is computed on every
    lookup, and a recursive signature over a repo-wide taxonomy root made that
    O(files) per call — enough to stall an explanation batch outright. Directory
    mtimes change whenever a file inside is added, removed or replaced, which
    is what a redeployed taxonomy actually looks like.
    """
    signature: list[tuple] = []
    for root in roots:
        try:
            newest = os.path.getmtime(root)
            with os.scandir(root) as entries:
                for entry in entries:
                    try:
                        newest = max(newest, entry.stat().st_mtime)
                    except OSError:
                        continue
        except OSError:
            newest = 0.0
        signature.append((os.path.normcase(root), round(newest, 3)))
    return tuple(signature)


# ─────────────────────────────────────────────────────────────────────────────
# The index
# ─────────────────────────────────────────────────────────────────────────────

class TaxonomyIndex:
    """Lazily-built, per-taxonomy-folder view of concepts, axes and hypercubes.

    Construction only walks the directory listing; the expensive parsing of
    label linkbases, schemas and definition linkbases happens on first use of
    the corresponding lookup and is then memoised.
    """

    def __init__(self, roots: tuple[str, ...]) -> None:
        self.roots = roots
        self._lock = threading.RLock()

        self._schema_files: list[str] | None = None
        self._label_files: list[str] | None = None
        self._definition_files: list[str] | None = None

        self._labels: dict[str, str] | None = None
        self._elements: dict[str, dict] | None = None
        self._elements_by_id: dict[str, str] | None = None
        self._hypercube_cache: dict[str, dict | None] = {}
        self._axis_cache: dict[str, dict | None] = {}

    # ── reference resolution ────────────────────────────────────────────────

    def resolve_ref(self, ref: str) -> str:
        """Element NAME for a linkbase href or typedDomainRef.

        Both point at an element by its schema `id`, not its `name`
        ('in-rbi-rep.xsd#in-rbi-rep_PlaceOfOccurence' -> 'PlaceOfOccurence';
        'in-rbi-rep-par.xsd#in-rbi-rep-par_DateDomain' -> 'DateDomain').
        Treating the fragment as a name is why labels and hypercubes both came
        back empty on the first pass — every lookup key was an id.

        Resolution is by the schemas' own id index, so it holds for any
        id-naming convention. The '<prefix>_<Name>' shortcut is only a
        fallback for a reference into a schema that isn't in this taxonomy
        folder, and only when the remainder is itself a known element.
        """
        fragment = local_name(ref)
        if not fragment:
            return ""
        by_id = self._build_element_ids()
        resolved = by_id.get(fragment)
        if resolved:
            return resolved
        elements = self._build_elements()
        if fragment in elements:
            return fragment
        if "_" in fragment:
            tail = fragment.rsplit("_", 1)[-1]
            if tail in elements:
                return tail
            return tail
        return fragment

    def _build_element_ids(self) -> dict[str, str]:
        self._build_elements()
        return self._elements_by_id or {}

    # ── file discovery ──────────────────────────────────────────────────────

    def _walk(self) -> list[str]:
        found: list[str] = []
        for root in self.roots:
            if not os.path.isdir(root):
                continue
            for dirpath, _dirs, files in os.walk(root):
                for fn in files:
                    if fn.lower().endswith((".xml", ".xsd")):
                        found.append(os.path.join(dirpath, fn))
        return sorted(found)

    def _classify_files(self) -> None:
        """Partition the taxonomy folder by CONTENT, not filename.

        This is what finds 'in-rbi-rep-fmr4_def1.xml' as a definition linkbase
        — a file no name-based pattern in this repo would have matched.
        """
        with self._lock:
            if self._definition_files is not None:
                return
            schemas: list[str] = []
            labels: list[str] = []
            definitions: list[str] = []
            for path in self._walk():
                try:
                    if os.path.getsize(path) > _MAX_SNIFF_BYTES:
                        continue
                except OSError:
                    continue
                if path.lower().endswith(".xsd"):
                    schemas.append(path)
                    continue
                head = self._read_head(path)
                if not head:
                    continue
                if "labelArc" in head or "labelLink" in head:
                    labels.append(path)
                if _ARCROLE_HYPERCUBE_DIMENSION in head or _ARCROLE_DIMENSION_DOMAIN in head:
                    definitions.append(path)
            self._schema_files = schemas
            self._label_files = labels
            self._definition_files = definitions
            logger.info(
                "[taxonomy_index] %s -> %d schemas, %d label linkbases, %d definition linkbases",
                self.roots, len(schemas), len(labels), len(definitions),
            )

    @staticmethod
    def _read_head(path: str, limit: int = 262144) -> str:
        """Read enough of a file to classify it. Linkbases declare their
        arcroles on the arcs themselves, which can appear late in a large
        file, so on a miss the whole file is read once."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                head = fh.read(limit)
                if ("labelArc" in head or _ARCROLE_HYPERCUBE_DIMENSION in head
                        or _ARCROLE_DIMENSION_DOMAIN in head):
                    return head
                rest = fh.read()
                return head + rest
        except OSError as exc:
            logger.debug("[taxonomy_index] cannot read %s: %s", path, exc)
            return ""

    # ── labels ──────────────────────────────────────────────────────────────

    def _build_labels(self) -> dict[str, str]:
        with self._lock:
            if self._labels is not None:
                return self._labels
            self._classify_files()
            self._build_elements()   # resolve_ref needs the id index first
            labels: dict[str, str] = {}
            for path in (self._label_files or []):
                try:
                    root = ET.parse(path).getroot()
                except (ET.ParseError, OSError) as exc:
                    logger.debug("[taxonomy_index] label parse failed %s: %s", path, exc)
                    continue
                for link in root.iter(f"{_LINK}labelLink"):
                    # locator label -> concept local name
                    loc_to_concept: dict[str, str] = {}
                    for loc in link.findall(f"{_LINK}loc"):
                        lab = loc.get(f"{_XLINK}label")
                        href = loc.get(f"{_XLINK}href") or ""
                        if lab:
                            loc_to_concept[lab] = self.resolve_ref(href)
                    # resource label -> text, standard role preferred
                    res_to_text: dict[str, str] = {}
                    for res in link.findall(f"{_LINK}label"):
                        lab = res.get(f"{_XLINK}label")
                        role = res.get(f"{_XLINK}role") or ""
                        if not lab or (role and role != _STANDARD_LABEL_ROLE):
                            continue
                        text = (res.text or "").strip()
                        if text:
                            res_to_text.setdefault(lab, text)
                    for arc in link.findall(f"{_LINK}labelArc"):
                        concept = loc_to_concept.get(arc.get(f"{_XLINK}from") or "")
                        text = res_to_text.get(arc.get(f"{_XLINK}to") or "")
                        if concept and text:
                            labels.setdefault(concept, text)
            self._labels = labels
            logger.info("[taxonomy_index] %d concept labels indexed", len(labels))
            return labels

    def concept_label(self, concept: str) -> str:
        """Human label for a concept/axis/member local name, or ""."""
        if not concept:
            return ""
        return self._build_labels().get(local_name(concept), "")

    # ── element declarations (schemas) ───────────────────────────────────────

    def _build_elements(self) -> dict[str, dict]:
        """local name -> declaration facts, across every .xsd in the taxonomy.

        Also resolves each declaration's simple-type restriction (base type and
        facets) whether the type is inline or a named simpleType elsewhere in
        the same schema — the two spellings the repo actually uses:

            <element name="DateDomain"><simpleType><restriction base="xsd:date"/></...>
            <element name="XDomain" type="ns:XDomain"/>  + <simpleType name="XDomain">…
        """
        with self._lock:
            if self._elements is not None:
                return self._elements
            self._classify_files()
            elements: dict[str, dict] = {}
            by_id: dict[str, str] = {}
            for path in (self._schema_files or []):
                try:
                    root = ET.parse(path).getroot()
                except (ET.ParseError, OSError) as exc:
                    logger.debug("[taxonomy_index] schema parse failed %s: %s", path, exc)
                    continue

                named_types: dict[str, dict] = {}
                for st in root.iter(f"{_XSD}simpleType"):
                    name = st.get("name")
                    if name:
                        named_types[name] = _restriction_facts(st)

                for el in root.iter(f"{_XSD}element"):
                    name = el.get("name")
                    if not name:
                        continue
                    element_id = el.get("id")
                    if element_id:
                        by_id.setdefault(element_id, name)
                    if name in elements:
                        continue
                    typed_ref = el.get(f"{_XBRLDT}typedDomainRef")
                    inline = el.find(f"{_XSD}simpleType")
                    restriction = _restriction_facts(inline) if inline is not None else None
                    if restriction is None:
                        type_attr = el.get("type") or ""
                        restriction = named_types.get(local_name(type_attr))
                    elements[name] = {
                        "name": name,
                        "source_file": path,
                        "type": el.get("type") or "",
                        "substitution_group": el.get("substitutionGroup") or "",
                        "abstract": (el.get("abstract") or "").lower() == "true",
                        "period_type": el.get(f"{_XBRLI}periodType") or "",
                        "balance": el.get(f"{_XBRLI}balance") or "",
                        "typed_domain_ref": typed_ref or "",
                        "restriction": restriction,
                    }
            self._elements = elements
            self._elements_by_id = by_id
            logger.info(
                "[taxonomy_index] %d element declarations indexed (%d by id)",
                len(elements), len(by_id),
            )
            return elements

    def element(self, name: str) -> dict | None:
        return self._build_elements().get(local_name(name))

    # ── axes ────────────────────────────────────────────────────────────────

    def axis_info(self, axis: str) -> dict | None:
        """Everything known about one dimension/axis.

        {
          "axis_id", "label", "is_typed",
          "typed_domain": {"name", "base_type", "facets": {...}, "example"} | None,
          "domain": local name | "",
          "members": [{"id", "label"}],
          "source_file",
        }

        `is_typed` comes from the presence of `xbrldt:typedDomainRef` on the
        axis declaration — the taxonomy's own authoritative statement, rather
        than inferred from "the member list came back empty", which cannot
        distinguish a typed axis from a lookup that simply failed.
        """
        key = local_name(axis)
        if not key:
            return None
        with self._lock:
            if key in self._axis_cache:
                return self._axis_cache[key]

        decl = self.element(key)
        info: dict = {
            "axis_id": key,
            "label": self.concept_label(key),
            "is_typed": False,
            "typed_domain": None,
            "domain": "",
            "members": [],
            "source_file": (decl or {}).get("source_file", ""),
        }

        if decl and decl.get("typed_domain_ref"):
            info["is_typed"] = True
            domain_name = self.resolve_ref(decl["typed_domain_ref"])
            domain_decl = self.element(domain_name)
            restriction = (domain_decl or {}).get("restriction")
            info["typed_domain"] = {
                "name": domain_name,
                "label": self.concept_label(domain_name),
                "base_type": (restriction or {}).get("base", ""),
                "facets": (restriction or {}).get("facets", {}),
                "example": _example_for_base_type((restriction or {}).get("base", "")),
                "source_file": (domain_decl or {}).get("source_file", ""),
            }
        else:
            domain, members = self._domain_and_members(key)
            info["domain"] = domain
            info["members"] = [
                {"id": m, "label": self.concept_label(m) or humanize_local_name(m, ("Member", "Domain"))}
                for m in members
            ]

        with self._lock:
            self._axis_cache[key] = info
        return info

    def _domain_and_members(self, axis_local: str) -> tuple[str, list[str]]:
        """Walk dimension-domain then domain-member for one explicit axis,
        across every definition linkbase (a domain can be extended in more
        than one file, so results are unioned, not first-match)."""
        self._classify_files()
        domain = ""
        members: list[str] = []
        seen: set[str] = set()
        for path in (self._definition_files or []):
            try:
                root = ET.parse(path).getroot()
            except (ET.ParseError, OSError):
                continue
            for link in root.iter(f"{_LINK}definitionLink"):
                locs = _locator_map(link, self.resolve_ref)
                arcs = _arc_list(link, locs)
                dd = [a for a in arcs if a["arcrole"].endswith(_ARCROLE_DIMENSION_DOMAIN)
                      and a["from"] == axis_local]
                if not dd:
                    continue
                for arc in dd:
                    target = arc["to"]
                    if not target:
                        continue
                    domain = domain or target
                    for member_arc in arcs:
                        if (member_arc["arcrole"].endswith(_ARCROLE_DOMAIN_MEMBER)
                                and member_arc["from"] == target
                                and member_arc["to"]
                                and member_arc["to"] not in seen):
                            seen.add(member_arc["to"])
                            members.append(member_arc["to"])
        return domain, sorted(members)

    # ── hypercubes ──────────────────────────────────────────────────────────

    def hypercube_for_concept(self, concept: str) -> dict | None:
        """The hypercube declaring *concept* as a primary item, with every axis
        it requires.

        Candidate definition linkbases are tried in order and the first that
        actually declares the concept as a primary item wins — evidence, not
        filename, decides. Returns None when no linkbase declares it, which is
        an honest "the taxonomy we found doesn't cover this concept" and must
        not be presented as "the concept is invalid".
        """
        key = local_name(concept)
        if not key:
            return None
        with self._lock:
            if key in self._hypercube_cache:
                return self._hypercube_cache[key]

        self._classify_files()
        result: dict | None = None
        for path in (self._definition_files or []):
            result = self._hypercube_in_file(path, key)
            if result:
                break

        with self._lock:
            self._hypercube_cache[key] = result
        return result

    def _hypercube_in_file(self, path: str, concept_local: str) -> dict | None:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            logger.debug("[taxonomy_index] definition parse failed %s: %s", path, exc)
            return None

        for link in root.iter(f"{_LINK}definitionLink"):
            locs = _locator_map(link, self.resolve_ref)
            if concept_local not in locs.values():
                continue
            arcs = _arc_list(link, locs)

            all_arc = next((a for a in arcs if a["arcrole"].endswith(_ARCROLE_ALL)), None)
            if not all_arc:
                continue

            domain_member = [a for a in arcs if a["arcrole"].endswith(_ARCROLE_DOMAIN_MEMBER)]
            hypercube_dims = [a for a in arcs if a["arcrole"].endswith(_ARCROLE_HYPERCUBE_DIMENSION)]
            dimension_domain = [a for a in arcs if a["arcrole"].endswith(_ARCROLE_DIMENSION_DOMAIN)]

            # Primary items are everything reachable from the `all` arc's
            # source through domain-member arcs. Two layouts occur in the real
            # taxonomies — some insert a LineItems node between the abstract
            # and the concepts, others attach the concepts directly — so a
            # transitive walk covers both without a per-taxonomy branch.
            # Members of the hypercube's own DIMENSIONS are excluded: they are
            # also linked by domain-member arcs, but from a dimension's domain,
            # and they are not primary items.
            dimension_domains = {a["to"] for a in dimension_domain if a["to"]}
            primary_items = _reachable_members(
                domain_member, start=all_arc["from"], blocked=dimension_domains,
            )
            if concept_local not in primary_items:
                continue

            dimensions: dict[str, dict] = {}
            for hd in hypercube_dims:
                axis = hd["to"]
                if not axis or axis in dimensions:
                    continue
                dd = next((a for a in dimension_domain if a["from"] == axis), None)
                domain = dd["to"] if dd else ""
                members = sorted({
                    a["to"] for a in domain_member if a["from"] == domain and a["to"]
                }) if domain else []
                dimensions[axis] = {"domain": domain, "members": members}

            return {
                "source_file": path,
                "role": link.get(f"{_XLINK}role") or "",
                "primary_item_count": len(primary_items),
                "hypercube": all_arc["to"],
                "closed": (all_arc.get("closed") or "").lower() == "true",
                "primary_items": primary_items,
                "dimensions": dimensions,
            }
        return None

    def describe_axis_for_concept(self, concept: str) -> list[dict]:
        """Full axis descriptions for every axis the concept's hypercube
        requires, merging the hypercube's own member lists with the axis-level
        typed/explicit determination. [] when no hypercube was found."""
        hypercube = self.hypercube_for_concept(concept)
        if not hypercube:
            return []
        out: list[dict] = []
        for axis_id, entry in (hypercube.get("dimensions") or {}).items():
            info = self.axis_info(axis_id) or {
                "axis_id": axis_id, "label": "", "is_typed": False,
                "typed_domain": None, "domain": "", "members": [],
            }
            info = dict(info)
            if not info["is_typed"] and not info.get("members") and entry.get("members"):
                info["domain"] = info.get("domain") or entry.get("domain", "")
                info["members"] = [
                    {"id": m, "label": self.concept_label(m) or humanize_local_name(m, ("Member", "Domain"))}
                    for m in entry["members"]
                ]
            out.append(info)
        return out


# ─────────────────────────────────────────────────────────────────────────────
# XML helpers
# ─────────────────────────────────────────────────────────────────────────────

def _locator_map(link: ET.Element, resolve) -> dict[str, str]:
    """xlink:label -> concept NAME, for one extended link.

    *resolve* turns an href fragment (an element id) into the element's name;
    xlink:title is the fallback because this generator writes the plain name
    there, which covers a locator pointing outside this taxonomy folder.
    """
    out: dict[str, str] = {}
    for loc in link.findall(f"{_LINK}loc"):
        label = loc.get(f"{_XLINK}label")
        if not label:
            continue
        href = loc.get(f"{_XLINK}href") or ""
        out[label] = resolve(href) or (loc.get(f"{_XLINK}title") or "")
    return out


def _reachable_members(
    domain_member_arcs: list[dict], start: str, blocked: set[str],
) -> list[str]:
    """Transitive closure of domain-member arcs from *start*, not descending
    into any node in *blocked* (the hypercube's dimension domains). Cycle-safe;
    the start node itself is not a primary item."""
    seen: set[str] = set()
    frontier = [start]
    while frontier:
        node = frontier.pop()
        for arc in domain_member_arcs:
            if arc["from"] != node:
                continue
            target = arc["to"]
            if not target or target in seen or target in blocked:
                continue
            seen.add(target)
            frontier.append(target)
    seen.discard(start)
    return sorted(seen)


def _arc_list(link: ET.Element, locs: dict[str, str]) -> list[dict]:
    arcs: list[dict] = []
    for arc in link.findall(f"{_LINK}definitionArc"):
        arcs.append({
            "arcrole": arc.get(f"{_XLINK}arcrole") or "",
            "from": locs.get(arc.get(f"{_XLINK}from") or "", ""),
            "to": locs.get(arc.get(f"{_XLINK}to") or "", ""),
            "closed": arc.get(f"{_XBRLDT}closed") or "",
            "order": arc.get("order") or "",
        })
    return arcs


_FACET_TAGS = (
    "pattern", "enumeration", "minInclusive", "maxInclusive",
    "minExclusive", "maxExclusive", "minLength", "maxLength",
    "length", "totalDigits", "fractionDigits", "whiteSpace",
)


def _restriction_facts(simple_type: ET.Element | None) -> dict | None:
    """Base type + every facet declared on a simpleType restriction.

    All facets are captured, not just `base`, so a typed dimension constrained
    by a pattern or enumeration is described by what it actually requires
    rather than only by its underlying primitive.
    """
    if simple_type is None:
        return None
    restriction = simple_type.find(f"{_XSD}restriction")
    if restriction is None:
        return None
    facets: dict[str, list[str]] = {}
    for tag in _FACET_TAGS:
        for node in restriction.findall(f"{_XSD}{tag}"):
            value = node.get("value")
            if value is not None:
                facets.setdefault(tag, []).append(value)
    return {"base": restriction.get("base") or "", "facets": facets}


# Illustrative values per XSD primitive, used only to show the SHAPE a typed
# dimension requires. Never presented as the value the filing should have used.
_BASE_TYPE_EXAMPLES = {
    "date":       ("a date in YYYY-MM-DD format", "2018-11-12"),
    "datetime":   ("a date and time in YYYY-MM-DDThh:mm:ss format", "2023-10-23T12:51:00"),
    "gyearmonth": ("a year and month in YYYY-MM format", "2025-03"),
    "gyear":      ("a four-digit year", "2025"),
    "time":       ("a time in hh:mm:ss format", "12:51:00"),
    "integer":    ("a whole number", "42"),
    "int":        ("a whole number", "42"),
    "long":       ("a whole number", "42"),
    "decimal":    ("a decimal number", "1234.56"),
    "double":     ("a decimal number", "1234.56"),
    "float":      ("a decimal number", "1234.56"),
    "boolean":    ("true or false", "true"),
    "string":     ("a text value", ""),
    "normalizedstring": ("a text value", ""),
    "token":      ("a text value", ""),
    "anyuri":     ("a URI", "https://example.org/x"),
}


def _example_for_base_type(base: str) -> dict:
    key = local_name(base).lower()
    description, sample = _BASE_TYPE_EXAMPLES.get(key, ("", ""))
    return {"description": description, "sample": sample}


# ─────────────────────────────────────────────────────────────────────────────
# Index construction / caching
# ─────────────────────────────────────────────────────────────────────────────

_TAXONOMY_DIR_NAME = "Taxonomy"
_SCHEMA_LOCATION_CACHE: dict[tuple[str, str], tuple[str, ...]] = {}


def _all_taxonomy_dirs(active_root: str) -> list[str]:
    """Every `DataBase/*/Taxonomy` folder, plus the standalone conf roots.

    Enumerated one directory level deep — never a recursive walk of DataBase,
    which also holds hundreds of Mapping_*.xml files per return and is far too
    expensive to traverse on an explanation request.
    """
    dirs: list[str] = []
    database = os.path.join(active_root, "DataBase")
    try:
        with os.scandir(database) as entries:
            for entry in entries:
                if not entry.is_dir():
                    continue
                candidate = os.path.join(entry.path, _TAXONOMY_DIR_NAME)
                if os.path.isdir(candidate):
                    dirs.append(candidate)
    except OSError:
        pass
    for sub in _TAXONOMY_ROOTS:
        if sub == "DataBase":
            continue
        wide = os.path.join(active_root, sub)
        if os.path.isdir(wide):
            dirs.append(wide)
    return dirs


def find_roots_for_schema(schema_href: str) -> tuple[str, ...]:
    """Taxonomy folders containing the entry-point schema a filing names in its
    own `<link:schemaRef>`.

    This is the strongest available signal for WHICH taxonomy to explain an
    error against, and it is the answer to the case where a form's own folder
    holds a different return's files (measured: DataBase/4038/Taxonomy is
    mpd07 while 4038's BTDetails file is an mpd03 filing). Cached per
    (repo root, schema basename); the scan is over taxonomy folders only.
    """
    name = os.path.basename((schema_href or "").replace("\\", "/")).strip().lower()
    if not name:
        return ()
    active_root = config._active_root()
    key = (os.path.normcase(active_root), name)
    with _CACHE_LOCK:
        cached = _SCHEMA_LOCATION_CACHE.get(key)
    if cached is not None:
        return cached

    matches: list[str] = []
    for root in _all_taxonomy_dirs(active_root):
        for dirpath, _dirs, files in os.walk(root):
            if any(f.lower() == name for f in files):
                matches.append(root)
                break
    result = tuple(matches)
    with _CACHE_LOCK:
        _SCHEMA_LOCATION_CACHE[key] = result
    if result:
        logger.info("[taxonomy_index] schemaRef %r resolved to %s", name, result)
    return result


def _candidate_roots(form_id: str, extra_roots: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Taxonomy folders to search, strongest evidence first.

    Order: folders the caller resolved from harder evidence (a schemaRef),
    then the form's own DataBase/<form_id>/Taxonomy. The repo-wide roots are
    NOT included — searching them costs more than it is worth on a request
    path, and a caller that needs them can pass a root from
    find_roots_for_schema() instead.
    """
    active_root = config._active_root()
    roots: list[str] = [r for r in extra_roots if r and os.path.isdir(r)]

    fid = os.path.basename(str(form_id or "").strip())
    if fid:
        own = os.path.join(active_root, "DataBase", fid, _TAXONOMY_DIR_NAME)
        if os.path.isdir(own):
            roots.append(own)

    unique: list[str] = []
    for root in roots:
        norm = os.path.normcase(os.path.abspath(root))
        if any(norm == os.path.normcase(os.path.abspath(u)) for u in unique):
            continue
        unique.append(root)
    return tuple(unique)


def get_index_for_paths(roots: tuple[str, ...]) -> "TaxonomyIndex | None":
    """Index for an explicit set of taxonomy folders. Cached by content
    signature so a redeployed taxonomy invalidates without a restart."""
    roots = tuple(r for r in roots if r and os.path.isdir(r))
    if not roots:
        return None
    try:
        signature = (roots, _tree_signature(roots))
    except OSError as exc:
        logger.warning("[taxonomy_index] cannot stat %s: %s", roots, exc)
        return None
    with _CACHE_LOCK:
        cached = _INDEX_CACHE.get(signature)
        if cached is not None:
            return cached
        index = TaxonomyIndex(roots)
        _INDEX_CACHE[signature] = index
        return index


def get_index_for_form(form_id: str, extra_roots: tuple[str, ...] = ()) -> "TaxonomyIndex | None":
    """The taxonomy index a given return's errors should be explained against.

    *extra_roots* lets a caller inject a folder it resolved from stronger
    evidence (e.g. the entry point named by the filing's own instance XML), and
    those are searched before anything derived from form_id.
    """
    roots = _candidate_roots(form_id, extra_roots)
    if not roots:
        logger.info("[taxonomy_index] no taxonomy folder for form_id=%s", form_id)
        return None
    return get_index_for_paths(roots)
