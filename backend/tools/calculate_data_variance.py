# ========================= calculate_data_variance.py =========================

from __future__ import annotations

import calendar
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from dateutil.relativedelta import relativedelta
from typing import Callable, List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Canonical frequency-code groups ──────────────────────────────────────────

_MONTHLY      = {"M", "MONTHLY"}
_QUARTERLY    = {"Q", "QUARTERLY"}

_HY_FIN       = {"H", "HALFYEARLY", "HY", "FH"}
_HY_CAL       = {"C", "CH"}

_ANNUAL_FIN   = {"A", "ANNUAL", "Y", "FY"}
_ANNUAL_CAL   = {"B", "CY"}

_WEEKLY       = {"W", "WEEKLY"}
_FORTNIGHTLY  = {"F", "FORTNIGHTLY", "HM"}

_DAILY        = {"D", "DAILY", "G"}


def get_previous_dates(
    current_date: datetime,
    report_freq: str,
    periods: int,
) -> List[datetime]:

    logger.info(
        "[variance] Calculating previous dates | current=%s | freq=%s | periods=%s",
        current_date, report_freq, periods,
    )

    dates: List[datetime] = []
    prev = current_date
    freq = report_freq.strip().upper()

    for _ in range(periods):

        if freq in _MONTHLY:
            prev = prev - relativedelta(months=1)

        elif freq in _QUARTERLY:
            prev = prev - relativedelta(months=3)

        elif freq in _HY_FIN or freq in _HY_CAL:
            prev = prev - relativedelta(months=6)

        elif freq in _ANNUAL_FIN or freq in _ANNUAL_CAL:
            prev = prev - relativedelta(years=1)

        elif freq in _WEEKLY:
            prev = prev - relativedelta(weeks=1)
            logger.info("[variance] Weekly previous date=%s", prev)
            dates.append(prev)
            continue

        elif freq in _FORTNIGHTLY:
            if prev.day == 15:
                prev = prev.replace(day=1) - relativedelta(days=1)
            else:
                prev = prev.replace(day=15)
            logger.info("[variance] Fortnightly previous date=%s", prev)
            dates.append(prev)
            continue

        elif freq in _DAILY:
            prev = prev - relativedelta(days=1)
            logger.info("[variance] Daily previous date=%s", prev)
            dates.append(prev)
            continue

        else:
            logger.warning(
                "[variance] Unknown frequency=%s defaulting to monthly", freq
            )
            prev = prev - relativedelta(months=1)

        last_day = calendar.monthrange(prev.year, prev.month)[1]
        prev = prev.replace(day=last_day)
        logger.info("[variance] Generated previous date=%s", prev.strftime("%d-%b-%Y"))
        dates.append(prev)

    return dates


def validate_reporting_date(
    report_date: datetime,
    report_freq: str,
) -> bool:

    freq = report_freq.strip().upper()
    day = report_date.day
    month = report_date.month
    year = report_date.year
    last_day = calendar.monthrange(year, month)[1]

    logger.info(
        "[variance] Validating date=%s | day=%s | last_day=%s | freq=%s",
        report_date, day, last_day, freq,
    )

    if freq in _WEEKLY:
        result = report_date.weekday() == 4
        logger.info("[variance] Weekly validation: weekday=%s valid=%s", report_date.weekday(), result)
        return result

    if freq in _FORTNIGHTLY:
        result = day in (15, last_day)
        logger.info("[variance] Fortnightly validation: day=%s valid=%s", day, result)
        return result

    if freq in _DAILY:
        return True

    if day != last_day:
        logger.warning(
            "[variance] Date validation FAILED: day=%s != last_day=%s for freq=%s",
            day, last_day, freq,
        )
        return False

    if freq in _MONTHLY:
        return True

    if freq in _QUARTERLY:
        result = month in (3, 6, 9, 12)
        logger.info("[variance] Quarterly validation: month=%s valid=%s", month, result)
        return result

    if freq in _HY_FIN:
        result = month in (3, 9)
        logger.info("[variance] HY-Fin validation: month=%s valid=%s", month, result)
        return result

    if freq in _HY_CAL:
        result = month in (6, 12)
        logger.info("[variance] HY-Cal validation: month=%s valid=%s", month, result)
        return result

    if freq in _ANNUAL_FIN:
        result = month == 3
        logger.info("[variance] Annual-Fin validation: month=%s valid=%s", month, result)
        return result

    if freq in _ANNUAL_CAL:
        result = month == 12
        logger.info("[variance] Annual-Cal validation: month=%s valid=%s", month, result)
        return result

    logger.warning("[variance] Freq=%s not matched in validation — defaulting True", freq)
    return True


def _to_decimal(v: Any) -> Decimal:
    if v is None:
        raise InvalidOperation("None")
    return Decimal(str(v).replace(",", ""))


def get_difference(prev_val: Any, curr_val: Any) -> Optional[Dict[str, Any]]:
    try:
        p = _to_decimal(prev_val)
        c = _to_decimal(curr_val)
        diff = (c - p).quantize(Decimal("0.01"))
        color = "danger" if c < p else ("success" if c > p else "")
        return {"value": str(diff), "color": color}
    except Exception:
        try:
            if str(prev_val).strip().lower() != str(curr_val).strip().lower():
                return {"value": str(curr_val), "color": ""}
            return None
        except Exception:
            return None


def get_pct_change(prev_val: Any, curr_val: Any) -> Optional[Dict[str, Any]]:
    try:
        p = _to_decimal(prev_val)
        c = _to_decimal(curr_val)
        pct = ((c - p) / abs(p)) * Decimal("100") if p != 0 else Decimal("0")
        rounded = pct.quantize(Decimal("0.01"))
        color = "danger" if c < p else ("success" if c > p else "")
        return {"value": f"{rounded}%", "color": color}
    except Exception:
        return None


def get_variance_summary(prev_val: Any, curr_val: Any) -> Optional[Dict[str, Any]]:
    try:
        p = _to_decimal(prev_val)
        c = _to_decimal(curr_val)
        pct = ((c - p) / abs(p)) * Decimal("100") if p != 0 else Decimal("0")
        rounded_pct = pct.quantize(Decimal("0.01"))
        arrow = "▲" if c > p else ("▼" if c < p else "")
        color = "success" if c > p else ("danger" if c < p else "")
        return {
            "text": f"{c:,.2f} {arrow} {rounded_pct:+.2f}% (Prev: {p:,.2f})",
            "arrow": arrow,
            "color": color,
        }
    except Exception:
        return None


def build_identifier(row: Dict[str, Any], comp_filter_cols: List[str]) -> str:
    row_upper = {k.upper(): v for k, v in row.items()}
    parts = []
    for col in comp_filter_cols:
        val = str(row_upper.get(col.upper(), "")).strip()
        if val:
            parts.append(val)
    return "_".join(parts)


def build_query(
    table_name: str,
    metadata: Dict[str, Any],
    current_date: datetime,
    prev_dates: List[datetime],
    return_code: Any,
    selected_columns: Optional[List[str]] = None,
) -> str:

    fc = metadata["filter_col"]
    all_dates = [current_date] + prev_dates
    date_conditions = []

    for d in all_dates:
        fmt = d.strftime("%d-%b-%Y").upper()
        date_conditions.append(f"{fc} = TO_DATE('{fmt}', 'DD-MON-YYYY')")

    date_sql = " OR ".join(date_conditions)

    rc_filter = ""
    if metadata.get("is_single"):
        rc_filter = f" AND {metadata.get('return_code_col')} = '{return_code}'"

    freq_filter = ""
    if metadata.get("freq_col") and metadata.get("freq_val"):
        freq_filter = f" AND {metadata.get('freq_col')} = '{metadata.get('freq_val')}'"

    cols = ", ".join(selected_columns) if selected_columns else "*"

    query = f"""
        SELECT {cols}
        FROM {table_name}
        WHERE ({date_sql})
        {rc_filter}
        {freq_filter}
    """.strip()

    logger.info("[variance] Generated Query:\n%s", query)
    return query


def _parse_date_like(value: Any) -> Optional[datetime]:
    """
    Robust date parser. Tries 4-digit year formats first, then 2-digit.
    Logs a warning if nothing matches so mismatches are instantly visible.
    """
    if isinstance(value, datetime):
        return value

    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    # 4-digit year formats first (unambiguous)
    for fmt in (
        "%Y-%m-%d",
        "%d-%b-%Y",           # 31-Mar-2025
        "%d-%m-%Y",           # 31-03-2025
        "%d-%m-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(s, fmt)
            logger.debug("[variance] Parsed date=%r using fmt=%s → %s", s, fmt, parsed)
            return parsed
        except Exception:
            continue

    # 2-digit year formats (Python pivot: 00-68 → 2000s, 69-99 → 1900s)
    for fmt in (
        "%d-%b-%y",           # 31-Mar-25
        "%d-%m-%y",           # 31-03-25
    ):
        try:
            parsed = datetime.strptime(s, fmt)
            logger.warning(
                "[variance] Parsed 2-digit year date=%r using fmt=%s → %s "
                "(verify century is correct)",
                s, fmt, parsed,
            )
            return parsed
        except Exception:
            continue

    logger.error(
        "[variance] *** COULD NOT PARSE DATE value=%r type=%s — "
        "add the format to _parse_date_like if needed ***",
        value, type(value).__name__,
    )
    return None


def dates_match(value: Any, target: datetime) -> bool:
    d = _parse_date_like(value)
    if d is None:
        return False
    match = (d.year == target.year and d.month == target.month and d.day == target.day)
    if not match:
        logger.debug(
            "[variance] dates_match MISS: db_value=%r parsed=%s target=%s",
            value, d.strftime("%d-%b-%Y") if d else "None",
            target.strftime("%d-%b-%Y"),
        )
    return match


def _normalize_row_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    """Uppercase all dict keys so Oracle column names always match XML FilterColumn."""
    return {k.upper(): v for k, v in row.items()}


def calculate_variance(
    return_code: Any,
    table_name: str,
    reporting_date: str,
    get_table_metadata_fn: Callable[..., Dict[str, Any]],
    execute_query_fn: Callable[..., List[Dict[str, Any]]],
    connection_string: Optional[str] = None,
    is_non_xbrl: bool = False,
    reporting_period: int = 1,
    selected_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:

    logger.info(
        "[variance] ══ START calculate_variance | table=%s | date=%s | periods=%s ══",
        table_name, reporting_date, reporting_period,
    )

    # ── Parse reporting date ──────────────────────────────────────────────────
    try:
        rdate = datetime.strptime(reporting_date.upper(), "%d-%b-%Y")
        logger.info("[variance] Parsed rdate=%s", rdate)
    except Exception as e:
        logger.exception("[variance] Invalid reporting date format")
        return {"error": f"Invalid reporting date format: {e}"}

    # ── Load metadata ─────────────────────────────────────────────────────────
    metadata = get_table_metadata_fn(return_code, table_name, is_non_xbrl)
    logger.info("[variance] Metadata=%s", metadata)

    report_freq = metadata.get("report_freq", "M")
    logger.info("[variance] report_freq resolved to=%s", report_freq)

    # ── Validate date against frequency ──────────────────────────────────────
    if not validate_reporting_date(rdate, report_freq):
        logger.error(
            "[variance] Date %s is invalid for freq=%s",
            reporting_date, report_freq,
        )
        return {"error": "Invalid Reporting Date According To Frequency."}

    # ── Build previous period dates ───────────────────────────────────────────
    prev_dates = get_previous_dates(rdate, report_freq, reporting_period)
    logger.info(
        "[variance] Querying dates: current=%s | previous=%s",
        rdate.strftime("%d-%b-%Y"),
        [d.strftime("%d-%b-%Y") for d in prev_dates],
    )

    # ── Build and execute query ───────────────────────────────────────────────
    query = build_query(
        table_name, metadata, rdate, prev_dates, return_code, selected_columns
    )

    try:
        logger.info("[variance] Executing query against DB …")
        if connection_string is not None:
            all_rows = execute_query_fn(query, connection_string)
        else:
            all_rows = execute_query_fn(query)
    except Exception as e:
        logger.exception("[variance] Query execution FAILED")
        return {"error": str(e)}

    logger.info("[variance] Total rows fetched from DB=%s", len(all_rows))

    if not all_rows:
        logger.error(
            "[variance] *** ZERO ROWS — query returned nothing. "
            "Check table diagnostics above (logged by variance_service). ***"
        )
        return {"error": f"No data found for {table_name} on {reporting_date}"}

    # ── Normalize row keys to uppercase ───────────────────────────────────────
    all_rows = [_normalize_row_keys(r) for r in all_rows]

    fc = metadata["filter_col"].upper()
    logger.info("[variance] filter_col (uppercase)=%s", fc)

    # ── Log sample row for debugging ─────────────────────────────────────────
    sample_row = all_rows[0]
    logger.info(
        "[variance] Sample row | keys=%s | %s value=%r | type=%s",
        list(sample_row.keys()),
        fc,
        sample_row.get(fc),
        type(sample_row.get(fc)).__name__,
    )

    # ── Split rows into current vs previous periods ───────────────────────────
    current_rows = [r for r in all_rows if dates_match(r.get(fc), rdate)]
    logger.info(
        "[variance] Current rows matched (rdate=%s): %s / %s total",
        rdate.strftime("%d-%b-%Y"), len(current_rows), len(all_rows),
    )

    if not current_rows:
        distinct_dates = sorted({str(r.get(fc)) for r in all_rows})
        logger.error(
            "[variance] *** NO CURRENT ROWS MATCHED ***\n"
            "  Target rdate  : %s\n"
            "  filter_col    : %s\n"
            "  Dates in DB   : %s\n"
            "  Hint: If DB dates look like datetime objects with time "
            "components, _parse_date_like should handle them. "
            "If they are strings in an unexpected format, add the format "
            "to _parse_date_like.",
            rdate.strftime("%d-%b-%Y"),
            fc,
            distinct_dates,
        )
        return {
            "error": (
                f"No data found for {table_name} on {reporting_date}. "
                f"Dates available in DB: {', '.join(distinct_dates)}"
            )
        }

    # ── Build previous-period lookup maps ─────────────────────────────────────
    prev_row_sets: Dict[str, Any] = {}

    for i, pd in enumerate(prev_dates):
        period_rows = [r for r in all_rows if dates_match(r.get(fc), pd)]
        logger.info(
            "[variance] Previous period %s (%s): %s rows matched",
            i + 1, pd.strftime("%d-%b-%Y"), len(period_rows),
        )
        if not period_rows:
            logger.warning(
                "[variance] No rows found for previous period %s — "
                "variance will be empty for this period",
                pd.strftime("%d-%b-%Y"),
            )

        lookup: Dict[str, Any] = {}
        for row in period_rows:
            identifier = build_identifier(
                row, metadata.get("comp_filter_col_names") or []
            )
            lookup[identifier] = row

        prev_row_sets[f"previous_{i+1}"] = {"date": pd, "lookup": lookup}

    # ── Determine columns to compare ─────────────────────────────────────────
    if selected_columns is None:
        selected_columns = [
            k for k in all_rows[0].keys() if k.upper() != fc.upper()
        ]
        logger.info("[variance] Auto-selected columns=%s", selected_columns)

    # ── Build result rows ─────────────────────────────────────────────────────
    comp_cols = [c.upper() for c in (metadata.get("comp_filter_col_names") or [])]
    result_rows = []
    unmatched_identifiers = []

    for curr_row in current_rows:
        identifier = build_identifier(curr_row, comp_cols)
        row_result: Dict[str, Any] = {
            "identifier": identifier,
            "current": curr_row,
            "previous": {},
        }

        for period_key, pdata in prev_row_sets.items():
            matched = pdata["lookup"].get(identifier)

            if not matched:
                unmatched_identifiers.append(
                    f"{period_key}:{identifier}"
                )
                logger.warning(
                    "[variance] No previous row found | "
                    "period=%s | identifier=%s",
                    period_key, identifier,
                )
                continue

            metrics: Dict[str, Any] = {}
            for col in selected_columns:
                col_upper = col.upper()
                prev_v = matched.get(col_upper)
                curr_v = curr_row.get(col_upper)
                metrics[col] = {
                    "value": prev_v,
                    "change": get_difference(prev_v, curr_v),
                    "pct_change": get_pct_change(prev_v, curr_v),
                    "variance_summary": get_variance_summary(prev_v, curr_v),
                }

            row_result["previous"][period_key] = metrics

        result_rows.append(row_result)

    if unmatched_identifiers:
        logger.warning(
            "[variance] %s current rows had no matching previous row: %s",
            len(unmatched_identifiers), unmatched_identifiers,
        )

    logger.info(
        "[variance] ══ COMPLETE | result_rows=%s | columns=%s ══",
        len(result_rows), len(selected_columns),
    )

    return {
        "table_name": table_name,
        "reporting_date": reporting_date,
        "comparison_periods": [
            pd.strftime("%d-%b-%Y").upper() for pd in prev_dates
        ],
        "columns": selected_columns,
        "rows": result_rows,
    }