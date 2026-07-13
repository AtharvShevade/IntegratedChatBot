# instance_label_parser.py — Parse XBRL instance filenames into display labels.
#
# Two filename conventions are recognised — both coexist in the same 6.0
# tenant repos (confirmed: D:\Repo6\Repo6\1001\Instance\1001 uses the compact
# 5.5 form, D:\Repo6\Repo6\1001\Instance\2034 uses the hyphenated 6.0 form) —
# so both patterns are tried on every filename rather than switching based on
# tenant_id.
#
# 5.5 (compact, no separators):
#   {PREFIX}{YY}{MM}{DD}R{serial}_{DD}-{MM}-{YY}_{HH}-{MM}-{SS}_Instance.xml
#   Example: HDFC200522R00002M_30-09-24_12-43-45_Instance.xml
#            → reporting_date : "22-May-2020"
#
# 6.0 (hyphenated, 4-digit year):
#   {PREFIX}{YYYY}-{MM}-{DD}R{serial}_{DD}-{MM}-{YY}_{HH}-{MM}-{SS}_Instance.xml
#   Example: IDBI2023-04-12R02602D_11-11-24_07-19-12_Instance.xml
#            → reporting_date : "12-Apr-2023"
#
# Both formats → generated_dt : "30-Sep-2024 12:43:45 PM" (same shape either way)
#             → label        : "22-May-2020 | Generated: 30-Sep-2024 12:43:45 PM"

from __future__ import annotations

import re
from datetime import datetime

_MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# 5.5 — unchanged from before 6.0 support existed.
# Captures:
#   group 1-3 : reporting YY MM DD   (digits right after the alpha prefix)
#   group 4-9 : generated DD MM YY HH MI SS  (from _DD-MM-YY_HH-MM-SS_ segment)
_FNAME_RE_5_5 = re.compile(
    r"^[A-Za-z]+(\d{2})(\d{2})(\d{2})R[^_]+_(\d{2})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})_Instance\.xml$",
    re.IGNORECASE,
)

# 6.0 — same shape but the reporting date is hyphenated with a 4-digit year
# (YYYY-MM-DD instead of YYMMDD).
# Captures:
#   group 1-3 : reporting YYYY MM DD
#   group 4-9 : generated DD MM YY HH MI SS
_FNAME_RE_6_0 = re.compile(
    r"^[A-Za-z]+(\d{4})-(\d{2})-(\d{2})R[^_]+_(\d{2})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})_Instance\.xml$",
    re.IGNORECASE,
)


def parse_instance_filename(fname: str) -> dict | None:
    """Parse a standard XBRL instance filename into its date/time components.

    Tries the 5.5 (compact YYMMDD) pattern first, then the 6.0 (hyphenated
    YYYY-MM-DD) pattern — both formats can appear side by side in the same
    6.0 tenant, so the format is auto-detected per file rather than switched
    on tenant_id.

    Returns a dict on success::

        {
            "reporting_date": "22-May-2020",
            "generated_dt":   "30-Sep-2024 12:43:45 PM",
            "label":          "22-May-2020 | Generated: 30-Sep-2024 12:43:45 PM",
            "sort_key":       datetime(2024, 9, 30, 12, 43, 45),   # for sorting
        }

    Returns ``None`` if the filename does not match either expected pattern.
    """
    m = _FNAME_RE_5_5.match(fname)
    if m:
        ryy, rmm, rdd, gdd, gmm, gyy, ghh, gmi, gss = (int(x) for x in m.groups())
        reporting_year = 2000 + ryy
    else:
        m = _FNAME_RE_6_0.match(fname)
        if not m:
            return None
        ryyyy, rmm, rdd, gdd, gmm, gyy, ghh, gmi, gss = (int(x) for x in m.groups())
        reporting_year = ryyyy

    # ── Reporting date ────────────────────────────────────────────────────────
    try:
        rd_month_abbr  = _MONTH_ABBR[rmm - 1]
        reporting_date = f"{rdd:02d}-{rd_month_abbr}-{reporting_year}"
    except IndexError:
        return None

    # ── Generated datetime ────────────────────────────────────────────────────
    try:
        gd_month_abbr = _MONTH_ABBR[gmm - 1]
    except IndexError:
        return None

    period = "PM" if ghh >= 12 else "AM"
    generated_dt = f"{gdd:02d}-{gd_month_abbr}-{2000 + gyy} {ghh:02d}:{gmi:02d}:{gss:02d} {period}"

    # ── Composite display label ───────────────────────────────────────────────
    label = f"{reporting_date} | Generated: {generated_dt}"

    # ── Sort key (newest generated datetime first) ────────────────────────────
    try:
        sort_key = datetime(2000 + gyy, gmm, gdd, ghh, gmi, gss)
    except ValueError:
        sort_key = datetime.min

    return {
        "reporting_date": reporting_date,
        "generated_dt":   generated_dt,
        "label":          label,
        "sort_key":       sort_key,
    }
