# ========================= variance_service.py =========================

from __future__ import annotations

import os
import logging
from typing import List, Dict, Any

from backend.tools.xml_loader import load_xml_tree
from backend.tools.calculate_data_variance import calculate_variance
from backend.tools.report_lookup import find_matching_reports, _parse_returns
from backend.config import (
    INSTANCE_BASE_DIR,
    TABLE_MAPPING_BASE_DIR,
    RETURNS_XML_PATH,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTIC HELPER
# Runs three cheap queries against the real Oracle connection so we can see
# exactly what is (or isn't) in the table without touching application logic.
# ─────────────────────────────────────────────────────────────────────────────

def _run_table_diagnostics(
    table_name: str,
    filter_col: str,
    execute_query_fn,
) -> None:
    """
    Fire three diagnostic queries and log results at ERROR level so they
    stand out even when the main pipeline produces 0 rows.

    Queries:
      1. Total row count  → tells us if the table is empty
      2. Distinct RDATE values (last 10) → tells us what dates actually exist
      3. Column data-type check via all_tab_columns → confirms RDATE is DATE
    """

    separator = "=" * 70

    # ── 1. Row count ──────────────────────────────────────────────────────────
    try:
        count_sql = f"SELECT COUNT(*) AS CNT FROM {table_name}"
        logger.error(
            "[DIAG] %s\n[DIAG] STEP 1 — Total row count\n[DIAG] SQL: %s",
            separator, count_sql,
        )
        cols, rows, err = execute_query_fn(count_sql)
        if err:
            logger.error("[DIAG] STEP 1 ERROR: %s", err)
        else:
            count_val = rows[0][0] if rows else "N/A"
            logger.error(
                "[DIAG] STEP 1 RESULT: table=%s | total_rows=%s",
                table_name, count_val,
            )
            if count_val == 0:
                logger.error(
                    "[DIAG] *** TABLE IS EMPTY — no data has been loaded "
                    "into %s. Insert data first. ***",
                    table_name,
                )
    except Exception as exc:
        logger.error("[DIAG] STEP 1 EXCEPTION: %s", exc)

    # ── 2. Distinct date values ───────────────────────────────────────────────
    try:
        dates_sql = (
            f"SELECT DISTINCT {filter_col} "
            f"FROM {table_name} "
            f"ORDER BY {filter_col} DESC "
            f"FETCH FIRST 10 ROWS ONLY"
        )
        logger.error(
            "[DIAG] %s\n[DIAG] STEP 2 — Distinct %s values (last 10)\n[DIAG] SQL: %s",
            separator, filter_col, dates_sql,
        )
        cols, rows, err = execute_query_fn(dates_sql)
        if err:
            # Oracle < 12c doesn't support FETCH FIRST — retry with ROWNUM
            dates_sql_fallback = (
                f"SELECT DISTINCT {filter_col} FROM "
                f"(SELECT {filter_col} FROM {table_name} "
                f"ORDER BY {filter_col} DESC) "
                f"WHERE ROWNUM <= 10"
            )
            logger.error(
                "[DIAG] STEP 2 retrying with ROWNUM syntax:\n%s",
                dates_sql_fallback,
            )
            cols, rows, err2 = execute_query_fn(dates_sql_fallback)
            if err2:
                logger.error("[DIAG] STEP 2 ERROR (both attempts): %s | %s", err, err2)
                rows = []
        if rows:
            date_vals = [str(r[0]) for r in rows]
            logger.error(
                "[DIAG] STEP 2 RESULT: distinct %s values = %s",
                filter_col, date_vals,
            )
        else:
            logger.error(
                "[DIAG] STEP 2 RESULT: no distinct date values found "
                "(table is empty or query failed)"
            )
    except Exception as exc:
        logger.error("[DIAG] STEP 2 EXCEPTION: %s", exc)

    # ── 3. Column metadata from Oracle data dictionary ────────────────────────
    try:
        meta_sql = (
            "SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, NULLABLE "
            "FROM ALL_TAB_COLUMNS "
            f"WHERE UPPER(TABLE_NAME) = UPPER('{table_name}') "
            "ORDER BY COLUMN_ID"
        )
        logger.error(
            "[DIAG] %s\n[DIAG] STEP 3 — Column data types from ALL_TAB_COLUMNS\n[DIAG] SQL: %s",
            separator, meta_sql,
        )
        cols, rows, err = execute_query_fn(meta_sql)
        if err:
            logger.error("[DIAG] STEP 3 ERROR: %s", err)
        elif not rows:
            logger.error(
                "[DIAG] STEP 3 RESULT: no columns found — "
                "table '%s' may not exist or current user has no SELECT privilege",
                table_name,
            )
        else:
            col_info = [
                f"{r[0]}({r[1]}{'(' + str(r[2]) + ')' if r[1] != 'DATE' else ''}, nullable={r[3]})"
                for r in rows
            ]
            logger.error(
                "[DIAG] STEP 3 RESULT: columns = %s",
                col_info,
            )
            # Specifically flag the filter column type
            for r in rows:
                if str(r[0]).upper() == filter_col.upper():
                    logger.error(
                        "[DIAG] STEP 3 filter_col=%s | data_type=%s | "
                        "expected=DATE",
                        r[0], r[1],
                    )
                    if str(r[1]).upper() != "DATE":
                        logger.error(
                            "[DIAG] *** filter_col %s is %s not DATE — "
                            "TO_DATE() comparison will never match. "
                            "Change build_query to use string comparison. ***",
                            r[0], r[1],
                        )
    except Exception as exc:
        logger.error("[DIAG] STEP 3 EXCEPTION: %s", exc)

    logger.error("[DIAG] %s\n[DIAG] Diagnostics complete.", separator)


def _load_table_mapping(return_id: str, tbl_path: str):

    logger.info(
        "[variance_service] Loading table mapping | return_id=%s | tbl_path=%s",
        return_id,
        tbl_path,
    )

    candidates = []

    if os.path.isabs(tbl_path):
        candidates.append(tbl_path)

    candidates.append(
        os.path.join(TABLE_MAPPING_BASE_DIR, str(return_id), tbl_path)
    )
    candidates.append(
        os.path.join(TABLE_MAPPING_BASE_DIR, tbl_path)
    )
    candidates.append(
        os.path.join(INSTANCE_BASE_DIR, str(return_id), tbl_path)
    )

    if RETURNS_XML_PATH:
        candidates.append(
            os.path.join(
                os.path.dirname(RETURNS_XML_PATH), str(return_id), tbl_path
            )
        )

    for fixed_name in ("TableMapping.xml", "TabelMapping.xml"):
        candidates.append(
            os.path.join(TABLE_MAPPING_BASE_DIR, str(return_id), fixed_name)
        )

    for c in candidates:
        if not c:
            continue
        norm = os.path.normpath(c)
        logger.info("[variance_service] Checking mapping path=%s", norm)
        if os.path.exists(norm):
            logger.info("[variance_service] Found mapping=%s", norm)
            root = load_xml_tree(
                norm, label=f"Table mapping for return {return_id}"
            )
            return root, norm

    fallback = os.path.normpath(
        os.path.join(TABLE_MAPPING_BASE_DIR, str(return_id), tbl_path)
    )
    logger.error("[variance_service] Mapping file not found")
    root = load_xml_tree(
        fallback, label=f"Table mapping for return {return_id}"
    )
    return root, fallback


def find_return_and_tables(return_input: str) -> Dict[str, Any]:

    logger.info("[variance_service] Finding return=%s", return_input)

    matches = find_matching_reports(return_input)

    if not matches:
        logger.error("[variance_service] Return not found=%s", return_input)
        return {"error": f"Return '{return_input}' not found."}

    r = matches[0]
    return_id = r.get("Id")
    tbl_path = r.get("TblPath")

    logger.info("[variance_service] Return matched | return_id=%s", return_id)

    if not tbl_path:
        return {"error": "Table mapping path not specified."}

    root, resolved_path = _load_table_mapping(return_id, tbl_path)

    if root is None:
        return {"error": f"Table mapping file not found at {resolved_path}"}

    tables = []
    for el in root.findall("Row"):
        tables.append({
            "table_name": el.attrib.get("TableName"),
            "filter_col": el.attrib.get("FilterColumn"),
            "primary_column": el.attrib.get("PrimaryColumn"),
            "comp_filter_col_name": el.attrib.get("CompFilterColName"),
            **el.attrib,
        })

    logger.info(
        "[variance_service] Tables found in mapping: %s",
        [t["table_name"] for t in tables],
    )

    canonical_freq = r.get("RepFreq", "")

    return {
        "return_id": return_id,
        "return_name": r.get("Name"),
        "report_freq": canonical_freq,
        "tbl_path": tbl_path,
        "table_mapping_path": resolved_path,
        "tables": tables,
    }


def _get_table_metadata_from_mapping(
    return_id: str,
    tbl_path: str,
    table_name: str,
) -> Dict[str, Any]:

    logger.info(
        "[variance_service] Loading metadata for table=%s", table_name
    )

    root, _ = _load_table_mapping(return_id, tbl_path)

    if root is None:
        raise FileNotFoundError("table mapping not found")

    table_name_upper = table_name.strip().upper()

    for el in root.findall("Row"):
        xml_table_name = (el.attrib.get("TableName") or "").strip().upper()
        if xml_table_name == table_name_upper:

            comp = el.attrib.get("CompFilterColName", "")
            comp_cols = [
                c.strip().upper() for c in comp.split("|") if c.strip()
            ]
            filter_col = (el.attrib.get("FilterColumn") or "").strip().upper()

            if not filter_col:
                logger.warning(
                    "[variance_service] FilterColumn is empty for table=%s",
                    table_name,
                )

            meta = {
                "filter_col": filter_col,
                "comp_filter_col_names": comp_cols,
                "report_freq": None,
                "is_single": el.attrib.get("IsSingle", "false").lower() == "true",
                "return_code_col": (el.attrib.get("ReturnCodeColumn") or "").upper() or None,
                "freq_col": (el.attrib.get("FreqColumn") or "").upper() or None,
                "freq_val": el.attrib.get("FreqValue"),
            }

            logger.info("[variance_service] Table metadata=%s", meta)
            return meta

    available = [el.attrib.get("TableName", "") for el in root.findall("Row")]
    logger.error(
        "[variance_service] Table '%s' not found in mapping. Available: %s",
        table_name, available,
    )
    raise KeyError(
        f"Table '{table_name}' not found in mapping. Available: {available}"
    )


def compute_variance(
    return_id: str,
    return_tbl_path: str,
    table_name: str,
    reporting_date: str,
    reporting_period: int,
    execute_query_fn,
    connection_string: str | None = None,
    selected_columns: List[str] | None = None,
):
    logger.info("[variance_service] compute_variance started")

    parsed = _parse_returns()

    return_meta = next(
        (r for r in parsed if r.get("Id") == str(return_id)), None
    )

    report_freq = None
    if return_meta:
        report_freq = (return_meta.get("RepFreq") or "").strip().upper() or None

    if not report_freq:
        logger.warning("[variance_service] Frequency not found defaulting to M")
        report_freq = "M"

    logger.info(
        "[variance_service] return_id=%s | report_freq=%s | "
        "table=%s | reporting_date=%s | periods=%s",
        return_id, report_freq, table_name, reporting_date, reporting_period,
    )

    table_meta = _get_table_metadata_from_mapping(
        return_id, return_tbl_path, table_name
    )

    metadata = {
        "filter_col": table_meta["filter_col"],
        "comp_filter_col_names": table_meta["comp_filter_col_names"],
        "report_freq": report_freq,
        "is_single": table_meta.get("is_single", False),
        "return_code_col": table_meta.get("return_code_col"),
        "freq_col": table_meta.get("freq_col"),
        "freq_val": table_meta.get("freq_val"),
    }

    logger.info(
        "[variance_service] Final metadata passed to calculate_variance=%s",
        metadata,
    )

    def get_table_metadata_fn(rc, tn, isnon):
        logger.info("[variance_service] Returning metadata for rc=%s tn=%s", rc, tn)
        return metadata

    def execute_query_adapter(query, conn_str=None):

        logger.info(
            "[variance_service] Executing Oracle query:\n%s", query
        )

        cols, rows, err = execute_query_fn(query)

        if err:
            logger.error("[variance_service] Oracle query error=%s", err)
            raise RuntimeError(err)

        logger.info(
            "[variance_service] Oracle rows fetched=%s | cols=%s",
            len(rows), cols,
        )

        # ── DIAGNOSTIC: if 0 rows returned, fire deep DB diagnostics ─────────
        if len(rows) == 0:
            logger.error(
                "[variance_service] *** ZERO ROWS RETURNED — "
                "firing table diagnostics to find root cause ***"
            )
            _run_table_diagnostics(
                table_name=table_name,
                filter_col=metadata["filter_col"],
                execute_query_fn=execute_query_fn,
            )

        # Normalize column names to uppercase
        cols_upper = [c.upper() for c in cols]

        out = []
        for r in rows:
            d = {cols_upper[i]: r[i] for i in range(len(cols_upper))}
            out.append(d)

        logger.info(
            "[variance_service] Converted %s rows to dict (uppercase keys)",
            len(out),
        )

        if out:
            logger.info(
                "[variance_service] Sample row keys=%s | sample values=%s",
                list(out[0].keys()),
                {k: str(v)[:60] for k, v in out[0].items()},
            )

        return out

    result = calculate_variance(
        return_code=return_id,
        table_name=table_name,
        reporting_date=reporting_date,
        get_table_metadata_fn=get_table_metadata_fn,
        execute_query_fn=execute_query_adapter,
        connection_string=connection_string,
        is_non_xbrl=False,
        reporting_period=reporting_period,
        selected_columns=selected_columns,
    )

    logger.info("[variance_service] compute_variance completed | result_keys=%s", list(result.keys()))
    return result