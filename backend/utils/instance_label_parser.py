# instance_label_parser.py — Parse XBRL instance filenames into display labels.
#
# Filename convention (compact, no separators):
#   {PREFIX}{YY}{MM}{DD}R{serial}_{DD}-{MM}-{YY}_{HH}-{MM}-{SS}_Instance.xml
#   Example: HDFC200522R00002M_30-09-24_12-43-45_Instance.xml
#            → reporting_date : "22-May-2020"
#            → generated_dt   : "30-Sep-2024 12:43:45 PM"
#            → label          : "22-May-2020 | Generated: 30-Sep-2024 12:43:45 PM"

from __future__ import annotations

import re
from datetime import datetime

_MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Captures:
#   group 1-3 : reporting YY MM DD   (digits right after the alpha prefix)
#   group 4-9 : generated DD MM YY HH MI SS  (from _DD-MM-YY_HH-MM-SS_ segment)
_FNAME_RE_5_5 = re.compile(
    r"^[A-Za-z]+(\d{2})(\d{2})(\d{2})R[^_]+_(\d{2})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})_Instance\.xml$",
    re.IGNORECASE,
)


def parse_instance_filename(fname: str) -> dict | None:
    """Parse a standard XBRL instance filename into its date/time components.

    Returns a dict on success::

        {
            "reporting_date": "22-May-2020",
            "generated_dt":   "30-Sep-2024 12:43:45 PM",
            "label":          "22-May-2020 | Generated: 30-Sep-2024 12:43:45 PM",
            "sort_key":       datetime(2024, 9, 30, 12, 43, 45),   # for sorting
        }

    Returns ``None`` if the filename does not match the expected pattern.
    """
    m = _FNAME_RE_5_5.match(fname)
    if not m:
        return None
    ryy, rmm, rdd, gdd, gmm, gyy, ghh, gmi, gss = (int(x) for x in m.groups())
    reporting_year = 2000 + ryy

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
