import re

# ── Token-level expansion for CIMS table name parts ──────────────────────────
# Keys are lowercase single tokens (split by _). Values are expanded phrases.
_TOKEN_EXPANSIONS = {
    # CIMS naming structure
    "cims":       "CIMS banking supervisory regulatory return",
    "raq":        "Risk Assessment Questionnaire RAQ",
    "q":          "quarterly",
    "m":          "monthly",
    "a":          "annual yearly",
    # Sections
    "sec1":       "section 1 loan assets asset quality classification",
    "sec2":       "section 2",
    "sec3":       "section 3 NPA non performing assets movement",
    "sec4":       "section 4",
    "sec5":       "section 5",
    "sec6":       "section 6",
    "sec7":       "section 7 capital adequacy",
    "sec8":       "section 8 industry breakdown sector exposure",
    "sec9":       "section 9 sensitive sector",
    "sec10":      "section 10",
    "sec11":      "section 11",
    "sec12":      "section 12",
    # Parts
    "parta":      "part A",
    "partb":      "part B",
    "part":       "part",
    # Domain
    "dom":        "domestic",
    "ove":        "overseas",
    "npa":        "NPA non performing assets",
    "sensec":     "sensitive sector real estate capital market commodity",
    "ind":        "industry",
    "brkup":      "breakdown category wise",
    "infra":      "infrastructure",
    "gen":        "general",
    "info":       "information",
    "master":     "master reference lookup",
    "masterrlc":  "master RLC reference lookup",
    "domestic":   "domestic",
    "arrangement":"banking arrangement",
    "borrower":   "borrower classification",
    "branch":     "branch",
    "assets":     "assets classification",
    "ca":         "current account CA",
    "final":      "final",
    # Backup markers
    "bk":         "backup copy",
    "bkup":       "backup copy",
    "bckup":      "backup copy",
    "backup":     "backup copy",
}

# ── Column token expansion ────────────────────────────────────────────────────
_COL_EXPANSIONS = {
    "npa":         "NPA non performing assets",
    "gnpa":        "gross NPA non performing assets",
    "nnpa":        "net NPA non performing assets",
    "sma":         "special mention accounts SMA",
    "car":         "capital adequacy ratio CAR",
    "pcr":         "provision coverage ratio PCR",
    "rwa":         "risk weighted assets RWA",
    "slr":         "statutory liquidity ratio SLR",
    "crr":         "cash reserve ratio CRR",
    "psl":         "priority sector lending PSL",
    "dom":         "domestic",
    "ove":         "overseas",
    "amt":         "amount",
    "os":          "outstanding",
    "rdate":       "reporting date period",
    "code":        "bank entity code identifier",
    "std":         "standard",
    "sub":         "substandard",
    "provision":   "provision provisioning",
    "exposure":    "exposure outstanding amount",
    "gross":       "gross total before deductions",
    "net":         "net after deductions",
    "end":         "end of period closing balance",
    "opening":     "opening beginning of period",
    "addition":    "addition new entries fresh",
    "reduction":   "reduction decrease",
    "recovery":    "recovery recovered amount",
    "restructure": "restructured restructuring",
    "delinquency": "delinquency classification period",
    "movement":    "movement change flow",
    "total":       "total aggregate sum",
    "risk":        "risk category",
    "industry":    "industry sector",
    "impaired":    "impaired NPA",
}


def _expand_table_tokens(table_name: str) -> str:
    """Expand underscore-separated tokens of a table name into readable text."""
    tokens = table_name.lower().split("_")
    expanded = []
    i = 0
    while i < len(tokens):
        # Try two-token combo first (e.g. "ind_brkup")
        two = f"{tokens[i]}_{tokens[i+1]}" if i + 1 < len(tokens) else ""
        if two and two in _TOKEN_EXPANSIONS:
            expanded.append(_TOKEN_EXPANSIONS[two])
            i += 2
        else:
            expanded.append(_TOKEN_EXPANSIONS.get(tokens[i], tokens[i]))
            i += 1
    return " ".join(expanded)


def generate_table_description(table: str, col_excel_names: list = None) -> str:
    """
    Generate a semantically rich description for a table by expanding its
    name tokens and incorporating human-readable column labels when available.
    """
    expanded = _expand_table_tokens(table)
    parts = [f"{table.upper()} — {expanded}."]

    if col_excel_names:
        # Drop generic labels (CODE, RDATE, TYPEID) and take up to 8
        useful = [
            n for n in col_excel_names
            if n and n.strip().upper() not in ("CODE", "RDATE", "TYPEID", "")
        ][:8]
        if useful:
            parts.append(f"Fields include: {', '.join(useful)}.")

    return " ".join(parts)


def generate_column_description(col: str) -> str:
    """Generate a readable description for a column by expanding its tokens."""
    tokens = re.split(r'[_\s]+', col.lower())
    return " ".join(_COL_EXPANSIONS.get(t, t) for t in tokens)
