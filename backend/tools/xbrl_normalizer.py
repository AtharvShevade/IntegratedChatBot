# xbrl_normalizer.py — Post-processing normalization and canonicalization layer
# for RBI XBRL variance analysis.
#
# Operates on raw fact dicts produced by load_xbrl_facts() (xbrl_comparator.py).
# Does NOT require Arelle — works from pre-extracted field values only.
#
# Pipeline:
#   resolve_contexts(facts)   → ctx_ref → structured context metadata
#   normalize_fact(fact, ctx) → enriched fact with normalized value + precision
#   canonicalize_facts(facts) → full canonical list (resolve + normalize, once)
#   build_context_key(ctx)    → stable dimensional comparison key
#   detect_anomalies(...)     → list of anomaly flag strings

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Configurable percentage concept list.
#
# Add concept names whose raw XBRL value is stored as a fraction (0.32 → 32 %).
# Values already on the 0-100 scale (abs > 1.05) are passed through unchanged.
# ---------------------------------------------------------------------------

PERCENTAGE_CONCEPTS: frozenset[str] = frozenset({
    # Rate / ratio concepts that RBI stores as fractional values
    "WeightedAverageInterestRate",
    "NetInflowOutflowAsPerStructuralLiquidityStatementToNetOutflowsAsPerStructuralLiquidityStatement",
    "RatioOfNetNpaToNetAdvances",
    "RatioOfGrossNpaToGrossAdvances",
    "CapitalAdequacyRatio",
    "Tier1CapitalRatio",
    "Tier2CapitalRatio",
    "LiquidityCoverageRatio",
    "NetStableFundingRatio",
    "CreditToDepositRatio",
    "ReturnOnAssets",
    "ReturnOnEquity",
    "NetInterestMargin",
    "CostToIncomeRatio",
    "ProvisionCoverageRatio",
})

# ---------------------------------------------------------------------------
# Precision label lookup.
# Maps the integer value of the XBRL 'decimals' attribute to a human label.
# IMPORTANT: decimals indicates rounding precision — do NOT use it to scale values.
# ---------------------------------------------------------------------------

_PRECISION_LABELS: dict[int, str] = {
    -9: "billion",
    -6: "million",
    -3: "thousand",
    -2: "hundred",
    -1: "ten",
     0: "unit",
     2: "cent",
     3: "milli",
     6: "micro",
}

# ---------------------------------------------------------------------------
# Context ID tokenizer helpers
# ---------------------------------------------------------------------------

_ISO8_RE          = re.compile(r'^(\d{4})(\d{2})(\d{2})$')
_PERIOD_PREFIX_RE = re.compile(r'^(asof|fromto)$', re.I)
_MEMBER_SUFFIX_RE = re.compile(r'(?i)Member$')

# Generic dimensional member classification heuristics.
# Keyword lists are intentionally generic — no report-specific names are hardcoded.
_MATURITY_KWS = ("day", "month", "year", "quarter", "week", "overnight", "long", "short")
_AMOUNT_KWS   = ("rupee", "lakh", "lacs", "crore", "thousand", "million",
                 "hundred", "above", "upto", "between")
_RATE_KWS     = ("rate", "ratio", "yield", "coupon", "spread", "return", "margin")
_CURRENCY_KWS = ("currency", "forex", "foreign", "domestic", "inr", "usd", "eur")
_SECTOR_KWS   = ("bank", "branch", "sector", "segment", "industry", "category",
                 "priority", "agriculture", "msme", "retail", "corporate")


def _classify_member(token: str) -> tuple[str, str]:
    """Return (dimension_hint, value) for a CamelCase XBRL member token.

    Heuristics are generic (keyword-based) — not tied to any specific report.
    The 'Member' suffix is stripped from the returned value for cleaner keys.

    Examples:
        "UptoTwentyEightDaysMember"  → ("maturity_bucket", "UptoTwentyEightDays")
        "AboveRupeesTenLakhsMember"  → ("amount_slab",     "AboveRupeesTenLakhs")
        "USDMember"                  → ("currency_type",   "USD")
        "RetailSectorMember"         → ("sector",          "RetailSector")
    """
    name  = _MEMBER_SUFFIX_RE.sub("", token)
    lower = name.lower()
    if any(k in lower for k in _AMOUNT_KWS):
        return ("amount_slab", name)
    if any(k in lower for k in _MATURITY_KWS):
        return ("maturity_bucket", name)
    if any(k in lower for k in _RATE_KWS):
        return ("rate_type", name)
    if any(k in lower for k in _CURRENCY_KWS):
        return ("currency_type", name)
    if any(k in lower for k in _SECTOR_KWS):
        return ("sector", name)
    return ("dimension", name)


# ---------------------------------------------------------------------------
# Context resolution
# ---------------------------------------------------------------------------

def resolve_contexts(facts: list[dict]) -> dict[str, dict]:
    """Build a map of contextRef → structured metadata from a list of raw facts.

    Uses pre-extracted fields ('ctx_ref', 'dim_key', 'period_type',
    'period_end', 'period_start') already stored in each fact dict by
    load_xbrl_facts().  Falls back to tokenising the ctx_ref ID string
    generically when dim_key is unavailable or empty.

    Returns:
        { ctx_ref_string: context_metadata_dict }

    context_metadata_dict:
        period_type  : "instant" | "duration" | "unknown"
        start_date   : ISO date string or ""
        end_date     : ISO date string or ""
        instant_date : ISO date string or ""  (same as end_date for instant)
        dimensions   : { dimension_hint: member_value }

    Example for ctx_ref "fromto_20200425_20200522_UptoTwentyEightDaysMember_...":
        {
            "period_type":  "duration",
            "start_date":   "2020-04-25",
            "end_date":     "2020-05-22",
            "instant_date": "",
            "dimensions":   {"maturity_bucket": "UptoTwentyEightDays", ...},
        }
    """
    result: dict[str, dict] = {}

    for fact in facts:
        ctx_ref = fact.get("ctx_ref", "")
        if not ctx_ref or ctx_ref in result:
            continue

        period_type  = fact.get("period_type", "unknown")
        period_end   = fact.get("period_end", "")
        period_start = fact.get("period_start", "")
        dim_key      = fact.get("dim_key", "")

        meta: dict[str, Any] = {
            "period_type":  period_type,
            "start_date":   period_start,
            "end_date":     period_end,
            "instant_date": period_end if period_type == "instant" else "",
            "dimensions":   {},
        }

        # ── Build dimensions from dim_key (Arelle-extracted, most reliable) ──
        # dim_key format: "axis1=member1;axis2=member2"
        dimensions: dict[str, str] = {}
        if dim_key:
            for pair in dim_key.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    axis, member = pair.split("=", 1)
                    dim_hint, value = (
                        _classify_member(member) if member else (axis.strip(), "")
                    )
                    # Prefer the axis name as key (more precise than the heuristic hint)
                    key = axis.strip() if axis.strip() else dim_hint
                    dimensions[key] = value

        # ── Supplement with ctx_ref token parsing (handles cases dim_key is empty) ──
        # Skip prefix tokens (asof/fromto) and 8-digit date tokens; classify the rest.
        if not dimensions:
            dup_counter: dict[str, int] = {}
            for part in ctx_ref.split("_"):
                if not part:
                    continue
                if _PERIOD_PREFIX_RE.match(part):
                    continue
                if _ISO8_RE.match(part):
                    continue
                # CamelCase member token (starts with uppercase or has 'Member' suffix)
                if part and (part[0].isupper() or _MEMBER_SUFFIX_RE.search(part)):
                    dim_hint, value = _classify_member(part)
                    if dim_hint in dimensions:
                        cnt = dup_counter.get(dim_hint, 0) + 1
                        dup_counter[dim_hint] = cnt
                        dim_hint = f"{dim_hint}_{cnt}"
                    dimensions[dim_hint] = value

        meta["dimensions"] = dimensions
        result[ctx_ref] = meta

    return result


def build_context_key(context_data: dict) -> str:
    """Generate a stable, sorted dimensional comparison key string.

    Facts with the same dimensional memberships but different contextRef IDs
    across two XBRL instances produce the same context_key and are therefore
    aligned correctly during comparison.

    Base contexts (no dimensions) return "BASE" so they can be distinguished
    from dimensional contexts and still match one another across both instances.

    Key format: "Axis1=Member1|Axis2=Member2" (alphabetically sorted axes).

    Example:
        {"CurrencyMismatchDurationDimension": "OneMonth"}
        → "CurrencyMismatchDurationDimension=OneMonth"

        {} → "BASE"
    """
    dims = context_data.get("dimensions", {})
    if not dims:
        return "BASE"
    parts = sorted(f"{k}={v}" for k, v in dims.items() if v)
    return "|".join(parts)


# ---------------------------------------------------------------------------
# Precision and value normalization
# ---------------------------------------------------------------------------

def _decimals_precision(decimals_str: str) -> tuple[int | None, str]:
    """Parse XBRL 'decimals' attribute → (int_value_or_None, precision_label).

    'INF' / '' → (None, "exact")
    '-3'       → (-3,  "thousand")
    '-6'       → (-6,  "million")
    """
    if not decimals_str or decimals_str.strip().upper() in ("INF", "INFINITE"):
        return None, "exact"
    try:
        d = int(decimals_str.strip())
        return d, _PRECISION_LABELS.get(d, f"10^{d}")
    except ValueError:
        return None, "unknown"


def normalize_percentage(concept: str, value: float) -> float:
    """Normalize percentage concepts to the 0 – 100 % scale.

    For concepts in PERCENTAGE_CONCEPTS that store fractional values (0.32):
    multiply by 100 → 32.0.

    For values that appear to already be on the 0-100 scale (abs > 1.05):
    return as-is to avoid double-conversion.

    CONSERVATIVE: only converts when abs(value) <= 1.05.
    """
    if concept not in PERCENTAGE_CONCEPTS:
        return value
    if abs(value) <= 1.05:
        return round(value * 100, 6)
    return value


def normalize_fact(fact: dict, ctx_map: dict[str, dict]) -> dict:
    """Normalize a single raw fact dict using its resolved context metadata.

    Returns an enriched copy of the fact dict with added keys:
        normalized_value  : float — value after percentage normalization
        decimals_int      : int | None — parsed decimals attribute
        precision_label   : str  — e.g. "million", "exact", "unknown"
        context_meta      : dict — resolved context metadata
        context_key       : str  — stable dimensional key
        is_percentage     : bool
    """
    out        = dict(fact)
    concept    = fact.get("concept", "")
    raw_val    = fact.get("value_num")
    decimals   = fact.get("decimals", "")
    ctx_ref    = fact.get("ctx_ref", "")

    # Resolved context — fall back to a minimal dict if ctx_ref not found
    ctx_meta = ctx_map.get(ctx_ref, {
        "period_type":  fact.get("period_type", "unknown"),
        "start_date":   fact.get("period_start", ""),
        "end_date":     fact.get("period_end", ""),
        "instant_date": "",
        "dimensions":   {},
    })
    out["context_meta"] = ctx_meta
    out["context_key"]  = build_context_key(ctx_meta)

    # Decimals: metadata only — do NOT use to scale values
    d_int, d_label         = _decimals_precision(str(decimals) if decimals else "")
    out["decimals_int"]    = d_int
    out["precision_label"] = d_label

    # Percentage normalization (conservative, configurable)
    is_pct           = concept in PERCENTAGE_CONCEPTS
    out["is_percentage"] = is_pct
    if raw_val is not None and is_pct:
        out["normalized_value"] = normalize_percentage(concept, raw_val)
    else:
        out["normalized_value"] = raw_val

    return out


def canonicalize_facts(facts: list[dict]) -> list[dict]:
    """Full normalization pipeline: resolve → normalize → canonical structure.

    Processes a list of raw facts from load_xbrl_facts() and returns a list
    of canonical fact dicts.  Context resolution is performed once and cached
    in a local map to avoid repeated ctx_ref parsing.

    The canonical structure preserves all original fields for backward
    compatibility and adds:
        value         : float | None  — normalized value (percentage-corrected)
        context       : dict          — structured context metadata
        context_key   : str           — stable dimensional key for comparison
        precision     : str           — human-readable precision label
        is_percentage : bool

    Performance: O(N) single pass for context resolution, O(N) second pass
    for normalization.  No repeated context parsing.
    """
    if not facts:
        return []

    ctx_map   = resolve_contexts(facts)  # one-shot: ctx_ref → metadata
    canonical: list[dict] = []

    for fact in facts:
        nf = normalize_fact(fact, ctx_map)
        canonical.append({
            # Canonical enrichment fields
            "concept":        nf.get("concept", ""),
            "value":          nf.get("normalized_value"),
            "unit":           nf.get("unit", ""),
            "context_data":   nf.get("context_meta", {}),
            "context_key":    nf.get("context_key", "BASE"),
            "dimensions":     nf.get("context_meta", {}).get("dimensions", {}),
            "decimals":       nf.get("decimals", ""),      # raw string: "INF", "-6", etc.
            "precision":      nf.get("precision_label", "unknown"),
            "is_percentage":  nf.get("is_percentage", False),
            "is_dimensional": nf.get("is_dimensional", False),
            # Original fields preserved (backward compatibility)
            "value_str":      nf.get("value_str", ""),
            "value_num":      nf.get("value_num"),
            "period_type":    nf.get("period_type", ""),
            "period_end":     nf.get("period_end", ""),
            "period_start":   nf.get("period_start", ""),
            "ctx_ref":        nf.get("ctx_ref", ""),
            "dim_key":        nf.get("dim_key", ""),
        })

    return canonical


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

def detect_anomalies(
    concept:    str,
    val_a:      float,
    val_b:      float,
    unit_a:     str,
    unit_b:     str,
    is_pct:     bool,
    pct_change: float | None,
) -> list[str]:
    """Return a list of anomaly flag strings for a variance row.

    Flags produced:
        unit_mismatch      : unit strings are non-empty and differ
        negative_rate      : percentage/rate concept has a negative value
        extreme_spike      : |pct_change| > 500 %
        new_large_value    : val_a == 0 and val_b > 1 M (new large position)
        large_value_zeroed : val_a > 1 M and val_b == 0 (large position dropped)
    """
    flags: list[str] = []
    if unit_a and unit_b and unit_a.upper() != unit_b.upper():
        flags.append(f"unit_mismatch:{unit_a}\u2194{unit_b}")
    if is_pct and (val_a < 0 or val_b < 0):
        flags.append("negative_rate")
    if pct_change is not None and abs(pct_change) > 500:
        flags.append(f"extreme_spike:{pct_change:+.0f}%")
    if val_a == 0 and abs(val_b) > 1_000_000:
        flags.append("new_large_value")
    if val_b == 0 and abs(val_a) > 1_000_000:
        flags.append("large_value_zeroed")
    return flags
