"""
Phase 3 of the XBRL-metadata integration: build the two NEW vector indexes that
give retrieval a business-vocabulary entry point, plus the XBRL-enriched text for
the existing table index.

Why these indexes exist
-----------------------
Retrieval currently fuses four signals: table text, column text, row labels, and
prior questions. Three of the four are derived from the same terse, similarly
worded spreadsheet headers, so their cosine scores cluster tightly and
discriminate poorly — src/retriever.py documents this directly, which is why the
prior-question signal carries the heaviest weight today.

A concept hit is different in kind. It is not "this table sounds relevant"; it
resolves to exactly one (table, column) via a mapping verified by a deterministic
4-hop join. That is a precision signal, and it speaks the regulatory vocabulary a
supervisor actually types ("adjusted net bank credit") rather than the DB's
abbreviation of it (ANBC / VALUE on CODE 1002).

What is embedded, and what is deliberately not
----------------------------------------------
Embedded: business label, the human names of the reporting tables the concept
appears in, the human names of its dimension axes, and a short phrase for the
measure's nature. All English.

NOT embedded (kept only as payload, or dropped entirely):
  * raw QNames ('in-rbi-rep:ActualRecoveries') - camel-case identifiers embed
    poorly and merely restate the label
  * role URIs - URL tokens dominate a vector
  * formula expressions - XPath/XBRL syntax carries no natural-language signal,
    so formulas are looked up by concept id, never by similarity
  * sibling_concepts - up to 38 per concept; would make every concept within a
    section look identical
  * abstract concepts - 528 of 774 are presentation scaffolding

Run after build_concept_map.py (which this reads) and after build_embeddings.py
(whose table index this rewrites):
    python embedding_building/cims_raq_quarterly/build_concept_embeddings.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
CONCEPT_MAP_PATH = os.path.join(OUT_DIR, "concept_map.json")
SCHEMA_PATH = os.path.join(OUT_DIR, "schema.json")

from src.vectorizer import embed_documents, build_faiss_index, save_index

# Cap the business-concept labels appended to a table's document. A table with 28
# mapped concepts would otherwise contribute a 300-word blob that dilutes the
# very terms it is meant to sharpen — the same dilution reasoning that keeps
# sibling_concepts out of the concept index.
MAX_TABLE_CONCEPT_LABELS = 14
MAX_TABLE_AXES = 6


def _measure_phrase(m):
    kind, period = m.get("measure"), m.get("period_type")
    if kind == "monetary":
        base = "monetary amount"
    elif kind == "percent":
        base = "percentage"
    elif kind == "ratio":
        base = "ratio"
    elif kind == "count":
        base = "count"
    elif kind == "text":
        return "descriptive text field"
    elif kind == "date":
        return "reporting date field"
    else:
        base = "numeric measure"
    if period == "instant":
        return f"{base} reported as a balance at a point in time"
    if period == "duration":
        return f"{base} reported for a period"
    return base


def concept_documents(cm):
    """One embeddable document per mapped business concept."""
    records = []
    for m in cm["metrics"]:
        parts = [m["label"] + "."]
        if m.get("reported_in"):
            parts.append("Reported in " + ", ".join(m["reported_in"][:4]) + ".")
        if m.get("axes"):
            parts.append("Analysed by " + ", ".join(m["axes"][:5]) + ".")
        parts.append(_measure_phrase(m) + ".")
        if m.get("is_core"):
            parts.append("Core reported metric.")
        records.append({
            "text": " ".join(parts),
            # Payload: everything the prompt layer needs, none of it embedded.
            "concept_id": m["concept_id"],
            "label": m["label"],
            "table": m["table"],
            "column": m.get("column") or m.get("value_column"),
            "is_core": m.get("is_core"),
        })
    return records


def member_documents(cm):
    """
    One embeddable document per distinct axis member — the dimension vocabulary
    ('Doubtful assets two', 'Non-funded', 'Exposures in rupees'). Deduplicated
    across axes: a member reused by several axes is ONE vector carrying all of
    its axis names, not several near-identical vectors competing with each other.
    """
    by_member = {}
    for axis in cm["axes"]:
        for mem in axis["members"]:
            rec = by_member.setdefault(mem["member_id"], {
                "label": mem["label"], "axes": [], "domains": [],
            })
            if axis["label"] not in rec["axes"]:
                rec["axes"].append(axis["label"])
            if axis.get("domain_label") and axis["domain_label"] not in rec["domains"]:
                rec["domains"].append(axis["domain_label"])

    # Which physical tables can this member's axis actually be used on? That is
    # what makes a member hit routable to a table at all.
    tables_by_axis = {}
    for m in cm["metrics"]:
        for a in m.get("axes") or []:
            tables_by_axis.setdefault(a, set()).add(m["table"])

    records = []
    for member_id, rec in by_member.items():
        if not rec["label"]:
            continue
        tables = sorted({t for a in rec["axes"] for t in tables_by_axis.get(a, ())})
        if not tables:
            # A member whose axis reaches no mapped table cannot route anywhere,
            # so it would only ever add noise to the fusion step.
            continue
        parts = [rec["label"] + "."]
        parts.append("A category of " + ", ".join(rec["axes"][:3]) + ".")
        records.append({
            "text": " ".join(parts),
            "member_id": member_id,
            "label": rec["label"],
            "axes": rec["axes"],
            "tables": tables,
        })
    return records


def enriched_table_documents(cm, schema):
    """
    The existing table documents, with the XBRL business layer appended.

    Returns [{text, table}] in the same shape build_vector_records produces, so
    this can replace table_index.faiss without any change to the search path.
    """
    records = []
    for t in schema:
        if t.get("is_backup"):
            continue
        parts = [t.get("text") or "", t.get("description") or ""]
        if t.get("return_name"):
            parts.append(t["return_name"])

        prof = (cm.get("table_profiles") or {}).get(t["table"].upper())
        if prof:
            if prof.get("roles"):
                parts.append("Regulatory reporting table: "
                             + ", ".join(prof["roles"][:3]) + ".")
            if prof.get("concept_labels"):
                parts.append("Business concepts reported here: "
                             + ", ".join(prof["concept_labels"][:MAX_TABLE_CONCEPT_LABELS])
                             + ".")
            if prof.get("axes"):
                parts.append("Dimensions: "
                             + ", ".join(prof["axes"][:MAX_TABLE_AXES]) + ".")
            if cm.get("return_code"):
                parts.append(f"Return {cm['return_code']}.")

        records.append({"text": " ".join(p for p in parts if p), "table": t["table"]})
    return records


def _build(name, records, index_file, meta_file):
    if not records:
        print(f"  [--] {name}: nothing to embed, skipped")
        return
    print(f"Embedding {len(records)} {name} records...")
    vecs = embed_documents([r["text"] for r in records])
    index = build_faiss_index(vecs)
    save_index(index, records,
               os.path.join(OUT_DIR, index_file), os.path.join(OUT_DIR, meta_file))
    print(f"  -> {index_file} ({index.ntotal} vectors)")


def main():
    # The member index is OPT-IN. It measured worse than not having it at every
    # fusion weight tried (see CONCEPT_MAX_HITS_PER_TABLE / MEMBER_SIGNAL_WEIGHT in
    # src/config.py), so config.MEMBER_SIGNAL_WEIGHT defaults to 0 and nothing
    # reads the index. Building it by default would cost ~30s and 1.5MB for a file
    # the pipeline never opens. Pass --with-member-index to rebuild it when
    # revisiting that experiment.
    build_members = "--with-member-index" in sys.argv

    if not os.path.exists(CONCEPT_MAP_PATH):
        sys.exit(f"missing {CONCEPT_MAP_PATH} - run build_concept_map.py first")
    with open(CONCEPT_MAP_PATH, encoding="utf-8") as f:
        cm = json.load(f)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    print(f"concept_map: return {cm['return_code']}, {len(cm['metrics'])} metrics\n")

    concepts = concept_documents(cm)
    members = member_documents(cm)
    tables = enriched_table_documents(cm, schema)

    print("Sample concept document:\n  " + (concepts[0]["text"] if concepts else "-"))
    print("Sample member document:\n  " + (members[0]["text"] if members else "-"))
    print()

    _build("concept", concepts, "concept_index.faiss", "concept_meta.pkl")
    _build("member", members, "member_index.faiss", "member_meta.pkl")
    _build("enriched table", tables, "table_index.faiss", "table_meta.pkl")

    print("\n[ok] concept_index + member_index built; table_index re-embedded "
          "with XBRL business text.")
    print("Restart the API process - src/retriever.py caches indexes for the life "
          "of the process.")


if __name__ == "__main__":
    main()
