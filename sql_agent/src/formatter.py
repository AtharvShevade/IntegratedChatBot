import json
from src.generators import generate_table_description, generate_column_description


def load_descriptions(json_path="data/.json-formatted"):
    """
    Load column descriptions from the JSON-formatted file.

    The file is expected to have the structure:
        { "results": [ { "items": [ { "table_name", "db_name", "excel_name",
                                      "return_name", ... }, ... ] } ] }

    Returns a dict keyed by (TABLE_NAME_UPPER, DB_NAME_UPPER) with values:
        { "excel_name": str, "return_name": str }
    """
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)

    mapping = {}
    results = data.get("results", [])
    items = results[0].get("items", []) if results else []

    for item in items:
        table_key = str(item.get("table_name", "")).upper()
        col_key = str(item.get("db_name", "")).upper()
        if table_key and col_key:
            mapping[(table_key, col_key)] = {
                "excel_name": item.get("excel_name", ""),
                "return_name": item.get("return_name", ""),
            }

    return mapping


def build_schema_json(tables, descriptions=None):
    """
    Build the enriched schema JSON list.

    Each column entry contains:
        name          – original DB column name (lowercase)
        excel_name    – human-readable label from the descriptions file
        description   – excel_name if available, else auto-generated
        return_name   – regulatory/return name from the descriptions file

    Each table entry contains:
        table         – table name
        return_name   – comma-separated unique return names across its columns
        description   – rich auto-generated description using name expansion
                        and column labels
        columns       – list of enriched column objects
        text          – comprehensive plain-text used for vector embedding
    """
    if descriptions is None:
        descriptions = {}

    result = []

    for table, cols in tables.items():
        col_objs = []
        col_names = []
        col_excel_names = []   # human-readable labels from the mapping
        table_return_names = set()

        for col in cols:
            col_upper = col["name"].upper()
            table_upper = table.upper()
            desc_entry = descriptions.get((table_upper, col_upper), {})

            excel_name = desc_entry.get("excel_name", "").strip()
            return_name = desc_entry.get("return_name", "").strip()

            # Friendly description: prefer excel_name, fall back to auto-generated
            friendly_desc = excel_name if excel_name else generate_column_description(col["name"])

            if excel_name:
                col_excel_names.append(excel_name)
            if return_name:
                table_return_names.add(return_name)

            col_objs.append({
                "name": col["name"],
                "description": friendly_desc,
                "return_name": return_name,
            })
            col_names.append(col["name"])

        return_name_str = ", ".join(sorted(table_return_names))
        is_backup = any(t in table.lower().split("_") for t in ("bk", "bkup", "bckup", "backup"))

        # Rich description: uses token expansion + embedded column labels
        table_desc = generate_table_description(table, col_excel_names)

        # Rich text for embedding — every angle the retriever might search from:
        #   1. raw table name
        #   2. return_name  (e.g. "CIMS_RAQ(Quarterly)")
        #   3. ALL column names (raw)
        #   4. ALL column descriptions (excel_names OR expanded auto-descriptions)
        all_col_descriptions = [
            c["description"] for c in col_objs
            if c["description"] and c["description"] not in (c["name"], c["name"].replace("_", " "))
        ]

        text_parts = [table]
        if return_name_str:
            text_parts.append(return_name_str)
        text_parts.append(" ".join(col_names))           # every column name
        if all_col_descriptions:
            text_parts.append(" | ".join(all_col_descriptions))  # every description
        if col_excel_names:
            # also append just the excel labels deduplicated
            extra = [e for e in col_excel_names if e not in all_col_descriptions]
            if extra:
                text_parts.append(" | ".join(extra))

        result.append({
            "table": table,
            "return_name": return_name_str,
            "description": table_desc,
            "is_backup": is_backup,
            "col_count": len(col_objs),
            "columns": col_objs,
            "text": " | ".join(text_parts),
        })

    return result


# Placeholder descriptions that add no signal — filter these out of embed text
_GENERIC_DESCS = {"value of", "date of event", "unique identifier",
                  "monetary value", "account balance", "status of record",
                  "reference to user", "category type"}


def _is_generic(desc: str) -> bool:
    d = desc.lower().strip()
    return any(d.startswith(g) for g in _GENERIC_DESCS) or len(d) < 4


def build_vector_records(schema_json):
    table_records = []
    column_records = []

    for t in schema_json:
        # Skip backup tables from the search index entirely
        if t.get("is_backup"):
            continue

        # ── Table record ──────────────────────────────────────────────────────
        table_text_parts = [t["text"], t["description"]]
        if t.get("return_name"):
            table_text_parts.append(t["return_name"])

        table_records.append({
            "text": " ".join(table_text_parts),
            "table": t["table"],
        })

        # ── Column records ────────────────────────────────────────────────────
        for c in t["columns"]:
            col_parts = [
                f"{t['table']}.{c['name']}",   # table.column context
                c["name"].replace("_", " "),    # humanised column name
                c["description"],               # excel_name or expanded
            ]
            if c.get("return_name"):
                col_parts.append(c["return_name"])
            # Add table description so column inherits table context
            if t.get("description"):
                col_parts.append(t["description"])

            column_records.append({
                "text": " | ".join(p for p in col_parts if p),
                "table": t["table"],
                "column": c["name"],
            })

    return table_records, column_records
