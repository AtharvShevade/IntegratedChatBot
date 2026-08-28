"""Business-readable explanations for the highest-priority variance facts.

WHAT THIS DOES

--------------

Turns the top-ranked variance rows into one plain-English sentence each:
    Doubtful Assets One — Domestic increased from ₹29.5 Cr to ₹23,978 Cr,

    raising its share of Amount Outstanding (Domestic) from 0.6% to 4.7%.

DIVISION OF LABOUR — this is the whole design

---------------------------------------------

PYTHON decides and computes EVERYTHING factual:
  · which facts are explained (priority ranking that already exists)

  · every number, share, percentage and currency format

  · a complete, correct sentence for each fact

THE LLM WRITES THE EXPLANATIONS. It receives structured facts - never a
draft sentence - and decides for itself what is worth saying about each and
how to say it. It never picks which facts matter, never computes a ratio,
and never sees a number it is allowed to change.

Python's template_sentence() is an EMERGENCY FALLBACK ONLY, used per-fact
when a model line is missing or fails validation. It is not the normal
output path: an earlier version showed it first and had the LLM reword it,
which made every explanation read the same.

WHAT THIS DOES NOT DO

---------------------

No importance is computed here. Regulatory importance, the movement score and

the 60/40 priority blend all already exist in xbrl_comparator /

xbrl_importance and are simply read:
    priority = 0.6 * regulatory_importance + 0.4 * movement_score

             (xbrl_comparator._tag_rows_with_importance)

compute_variance has already ranked EVERY comparable fact by that score before

anything here runs, so selection is a slice of an existing ordering, never a

second ranking system.

"""

from __future__ import annotations

import logging
import math

import os

import re

logger = logging.getLogger(__name__)

# ── Selection ────────────────────────────────────────────────────────────────

# How many facts get an explanation. Deliberately NOT xbrl_comparator's

# SUMMARY_ROWS (10): that one is tied to the chart's default Top-N view, and

# the two are now separate concerns — the chart shows 10 bars, the narrative

# explains 20 facts.

SUMMARY_CONCEPT_LIMIT = int(os.getenv("VARIANCE_EXPLAIN_LIMIT", "20"))

# A single concept can hold hundreds of dimensional rows (AmountOutstanding

# alone fills the whole top of the ranking), which would produce twenty

# near-identical sentences. Cap the variants per base concept so the list

# spans more of the return. Highest priority wins within each concept.

MAX_DIMS_PER_CONCEPT = int(os.getenv("VARIANCE_EXPLAIN_MAX_DIMS", "3"))

# Tiers eligible for an explanation — the same set the chat table shows.

ELIGIBLE_TIERS = ("Critical", "High")

# One business section can hold hundreds of eligible facts. Capping per
# section spreads the output across the return rather than letting a single
# supervisory area account for every sentence.
MAX_PER_SECTION = int(os.getenv("VARIANCE_EXPLAIN_MAX_PER_SECTION", "6"))

# Sibling dimensional values must reconcile to their parent within this

# fraction before a share-of-total is trusted. Dimensions are not always

# additive (overlapping exposure categories are not a partition), and a share

# computed against a denominator that is not a total is simply wrong.

SHARE_TOLERANCE = 0.02

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# Acronyms that must survive CamelCase splitting intact. Without this,

# "NettingItemforNPAs" becomes "Netting Itemfor NP As": the splitter fires

# between the P and the As because "As" looks like the start of a new word.

# Longest first so NNPA is matched before NPA.

_ACRONYMS = (
    "GNPAs", "NNPAs", "GNPA", "NNPA", "NPAs", "NPA",
    "CRAR", "SLR", "CRR", "LCR", "NSFR", "RWA", "LTV", "CASA",
    "MSME", "SME", "KCC", "DRI", "NULM", "NRLM", "SCST", "PSL",
    "INR", "RBI", "FCNRB", "FCNR", "NRE", "NRO", "EEFC", "FEMA",
    "HTM", "AFS", "HFT", "OBS", "ALM", "ROA", "ROE", "EMI",
    "KYC", "AML", "CFT", "LEI", "CIN", "PAN", "ATM", "UPI",
    "NEFT", "RTGS", "IMPS", "AUC", "IRR", "ID", "IT",
)

# Lowercase joiners that get glued to the previous word in XBRL names

# ("Itemfor", "Provisionof"). Split them back out.

_JOINERS = ("for", "and", "with", "from", "under", "against", "of")

_JOINER_RE = re.compile(
    r"(?<=[a-z]{3})(" + "|".join(_JOINERS) + r")(?=[A-Z])"
)

# ── Naming ───────────────────────────────────────────────────────────────────

def humanise(name: str) -> str:
    """CamelCase XBRL name -> readable words, acronyms intact.

    'DoubtfulAssetsOne'   -> 'Doubtful Assets One'
    'NettingItemforNPAs'  -> 'Netting Item for NPAs'
    'NetNPAs'             -> 'Net NPAs'

    Only a fallback — the taxonomy's own label is used whenever one exists
    (see business_name), because a label is authored text and this is a guess.
    """
    text = str(name or "").replace("_", " ")
    if not text:
        return ""
    # Split glued joiners FIRST, while the acronym after them is still a
    # capital letter. Doing it after acronym protection would leave "for" in
    # "NettingItemforNPAs" followed by a sentinel and no longer matchable.
    text = _JOINER_RE.sub(lambda m: " " + m.group(1) + " ", text)
    # Then protect acronyms behind sentinels the CamelCase splitter cannot
    # break: without this "NPAs" splits into "NP As".
    keep: list[str] = []
    for ac in _ACRONYMS:
        while ac in text:
            text = text.replace(ac, "%d" % len(keep), 1)
            keep.append(ac)
    text = _CAMEL_RE.sub(" ", text)
    for idx, ac in enumerate(keep):
        text = text.replace("%d" % idx, " " + ac + " ")
    return re.sub(r"\s+", " ", text).strip()

def _members(context_key: str) -> list[str]:
    """Dimension member values, most-general first.

    'RegionOfBusinessAxis=Domestic|RiskTypeDimension=DoubtfulAssetsOne'

        -> ['Domestic', 'DoubtfulAssetsOne']

    """

    if not context_key or context_key == "BASE":
        return []

    out = []

    for part in context_key.split("|"):
        raw = part.split("=", 1)[1] if "=" in part else part

        if raw.endswith("Member"):
            raw = raw[:-6]

        if raw:
            out.append(raw)

    return out

def _label_or_humanise(local: str, label: str | None) -> str:
    """Taxonomy label when the return supplies one, else a best-effort split.

    A label is text an author wrote ("Amount of provisions for NPAs"); the
    splitter is a guess at what a machine name meant. Always prefer the label.
    """
    lbl = (label or "").strip()
    return lbl if lbl else humanise(local)

def business_name(
    concept_base: str,
    context_key: str,
    concept_label: str = "",
    member_labels: list[str] | None = None,
) -> str:
    """The subject of the sentence, in business words.

    ALWAYS names the concept. An earlier version let the most specific
    dimension member stand alone as the subject whenever there were two or
    more members, which read well for one fact and was wrong across a set:
    AmountOutstanding, ExposureAmount and CreditExposure under the same two
    members ("Total Credit And Investment", "Domestic") all rendered as the
    identical string "Domestic - Total Credit And Investment". Three different
    figures looked like the same concept repeated with different numbers.

    The concept is what was measured and the members say which slice of it, so
    the concept leads and the members qualify:

        AmountOutstanding [Domestic, DoubtfulAssetsOne]
            -> 'Amount outstanding - Domestic, Doubtful assets one'
    """
    mem = _members(context_key)
    labels = list(member_labels or [])
    concept = _label_or_humanise(concept_base, concept_label)
    if not mem:
        return concept
    parts = [
        _label_or_humanise(m, labels[k] if k < len(labels) else "")
        for k, m in enumerate(mem)
    ]
    return f"{concept} — {', '.join(parts)}"



def parent_label(
    concept_base: str,
    context_key: str,
    concept_label: str = "",
    member_labels: list[str] | None = None,
) -> str:
    """How the denominator is named inside a share clause.

    Parenthesised rather than dashed: it appears mid-sentence after "share
    of", where a dash would read as a break.
    """
    mem = _members(context_key)
    labels = list(member_labels or [])
    concept = _label_or_humanise(concept_base, concept_label)
    if not mem:
        return concept
    parts = [
        _label_or_humanise(m, labels[k] if k < len(labels) else "")
        for k, m in enumerate(mem)
    ]
    return f"{concept} ({', '.join(parts)})"

# ── Value formatting ─────────────────────────────────────────────────────────

def _is_inr(unit: str) -> bool:
    """Only money gets money formatting.

    These returns carry ratios, counts and percentages alongside amounts;

    rendering a capital-adequacy ratio as '₹4.7 Cr' would be nonsense.

    """

    u = str(unit or "").strip().upper()

    return u in ("INR", "RUPEES", "RS", "INR_CRORE", "ISO4217:INR") or u.endswith(":INR")

def format_value(v: float | None, unit: str = "") -> str:
    """Business-readable value, unit-aware.

    INR uses the Indian scale a reviewer reads in (Cr / Lakh); everything else

    keeps plain grouped digits so a count stays a count.

    """

    if v is None:
        return "—"

    if not _is_inr(unit):
        # Non-monetary: no currency symbol, no Cr/Lakh.

        if abs(v) >= 1000:
            return f"{v:,.0f}"

        return f"{v:,.2f}".rstrip("0").rstrip(".")

    a = abs(v)

    sign = "-" if v < 0 else ""

    if a >= 1_00_00_000:                      # >= 1 crore

        cr = a / 1_00_00_000

        return f"{sign}₹{cr:,.0f} Cr" if cr >= 100 else f"{sign}₹{cr:,.1f} Cr"

    if a >= 1_00_000:                         # >= 1 lakh

        return f"{sign}₹{a / 1_00_000:,.1f} Lakh"

    return f"{sign}₹{a:,.0f}"

def format_pct(v: float | None) -> str:
    if v is None:
        return "N/A"

    s = "+" if v > 0 else ""

    a = abs(v)

    if a >= 1000:
        return f"{s}{v:,.0f}%"

    return f"{s}{v:,.1f}%"

# ── Selection ────────────────────────────────────────────────────────────────

# Structural taxonomy elements — dimension members, axes, domains, tables.
# They carry importance scores because they sit in a mandated section, but
# they are scaffolding, not reported figures, and a sentence about "Domestic"
# or "Standard assets" as a subject says nothing a reader can act on.
_STRUCTURAL_SUFFIXES = (
    "Member", "Axis", "Domain", "Table", "LineItems", "Hypercube", "Abstract",
)


def _is_structural(concept: str) -> bool:
    return str(concept or "").endswith(_STRUCTURAL_SUFFIXES)


def _adds_information(cand: dict, already: list[dict], label_a: str, label_b: str) -> bool:
    """Does this variant say something its already-selected siblings did not?

    A second or third dimension of the same concept earns its slot only when
    it carries distinct business information — a different direction, a
    materially different size, or a share that the earlier one lacked.
    Otherwise it produces a sentence that reads as a restatement, which is
    exactly the repetition this filter exists to stop.

    Applied ONLY to 2nd/3rd variants: the highest-priority fact for a concept
    is always kept, so priority still wins.
    """
    if not already:
        return True
    d = cand.get("diff") or 0
    for prev in already:
        pd = prev.get("diff") or 0
        # Different direction is always informative.
        if (d > 0) != (pd > 0):
            return True
    # Materially different magnitude (2x or more) against every sibling.
    mag = abs(cand.get(label_a) or 0)
    if mag and all(
        mag >= 2 * abs(p.get(label_a) or 0) or abs(p.get(label_a) or 0) >= 2 * mag
        for p in already
    ):
        return True
    return False

def select_facts(
    rows: list[dict],
    limit: int = SUMMARY_CONCEPT_LIMIT,
    max_per_concept: int = MAX_DIMS_PER_CONCEPT,
    max_per_section: int = MAX_PER_SECTION,
    label_a: str = "",
    label_b: str = "",
) -> list[dict]:
    """The facts that get explained, in priority order.

    *rows* must already be compute_variance's output — ranked by priority over
    EVERY comparable fact. This only re-orders and filters that ranking; it
    never re-scores, so there is one definition of "important" in the system.

    Diversity is applied in ROUNDS rather than by walking the list top-down.
    Round 1 takes the single highest-priority fact of each distinct concept,
    round 2 takes each concept's second, round 3 its third. That is what stops
    one concept (AmountOutstanding has hundreds of dimensional rows) from
    filling the output before any other concept is reached, while still giving
    every slot to the highest-priority fact available for it.

    *limit* is a MAXIMUM. When fewer facts survive the filters, fewer are
    returned — padding the list with restatements would defeat the point.
    """
    eligible = [
        r for r in rows
        if r.get("importance_matched")
        and r.get("importance_tier") in ELIGIBLE_TIERS
        # Scaffolding is never the subject of a business sentence.
        and not _is_structural(r.get("concept_base") or r.get("concept", ""))
    ]
    if not eligible:
        return []

    # Group by base concept, preserving the incoming priority order.
    groups: dict[str, list[dict]] = {}
    for r in eligible:
        groups.setdefault(r.get("concept_base") or r.get("concept", ""), []).append(r)

    # Concepts are visited in order of their own best fact, so a higher-priority
    # concept is always reached first.
    order = sorted(groups, key=lambda k: -(groups[k][0].get("priority") or 0.0))

    picked: list[dict] = []
    taken: dict[str, list[dict]] = {k: [] for k in order}
    per_section: dict[str, int] = {}

    for rnd in range(max_per_concept):
        for key in order:
            if len(picked) >= limit:
                break
            bucket = groups[key]
            if rnd >= len(bucket):
                continue
            cand = bucket[rnd]
            # A single section flooding the list is the same repetition
            # problem one concept causes, one level up.
            sec = cand.get("section_code") or ""
            if sec and per_section.get(sec, 0) >= max_per_section:
                continue
            # Rounds 2+ must justify themselves.
            if rnd > 0 and not _adds_information(cand, taken[key], label_a, label_b):
                continue
            picked.append(cand)
            taken[key].append(cand)
            if sec:
                per_section[sec] = per_section.get(sec, 0) + 1
        if len(picked) >= limit:
            break

    # Restore priority order for presentation — round-robin was a selection
    # device, not the order a reader should see.
    picked.sort(key=lambda r: -(r.get("priority") or 0.0))
    return picked[:limit]

# ── Share of total ───────────────────────────────────────────────────────────

def _parent_key(context_key: str) -> str | None:
    """The context one dimension less specific, or None at the top.

    'a=1|b=2' -> 'a=1';  'a=1' -> 'BASE';  'BASE' -> None

    """

    if not context_key or context_key == "BASE":
        return None

    parts = context_key.split("|")

    return "|".join(parts[:-1]) if len(parts) > 1 else "BASE"

def _index_rows(rows: list[dict]) -> dict[tuple, dict]:
    return {
        ((r.get("concept_base") or r.get("concept", "")), r.get("context_key") or "BASE"): r
        for r in rows
    }

# Bounds on the roll-up search below. Detecting a roll-up is a subset-sum,
# which is combinatorial - these keep it bounded on wide dimensions where a
# parent can have dozens of children. Beyond them the group is left as "not
# additive", which is the safe answer.
_ROLLUP_MAX_SIBLINGS = 12
_ROLLUP_MAX_COMBO = 5


def _rollup_members(sibs: list[dict], label: str) -> set[int]:
    """Siblings that are totals OF other siblings, identified by id().

    A dimension domain is often two levels deep. Under
    'AmountOutstanding [Domestic]' the real partition is four risk categories,
    but the instance also reports the three sub-categories of one of them:

        StandardAssets + SubStandardAssets + DoubtfulAssets + LossAssets
            = the parent, exactly, in both periods

        DoubtfulAssetsOne + Two + Three = DoubtfulAssets      <- roll-up

    Summing all seven double-counts DoubtfulAssets and lands at 113% of the
    parent, so the additivity gate was rejecting a denominator that is
    provably correct. Excluding the roll-up is what lets the gate see the
    genuine partition.

    Only matches within SHARE_TOLERANCE count, so this cannot invent a
    hierarchy the numbers do not already show.
    """
    import itertools

    positives = [s for s in sibs if (s.get(label) or 0) > 0]
    if len(positives) > _ROLLUP_MAX_SIBLINGS:
        return set()

    found: set[int] = set()
    for s in positives:
        target = s.get(label) or 0
        others = [o for o in positives if o is not s]
        if not others:
            continue
        # 2+ components: a "roll-up" of a single member is just that member.
        for n in range(2, min(len(others), _ROLLUP_MAX_COMBO) + 1):
            if any(
                abs(sum(x.get(label) or 0 for x in combo) - target)
                <= abs(target) * SHARE_TOLERANCE
                for combo in itertools.combinations(others, n)
            ):
                found.add(id(s))
                break
    return found



# Units that mark a fact as already-normalised: a percentage, ratio or rate.
# A share OF one of these is meaningless — "0.05% of the book, which is 4.7% of
# the book" restates the same quantity twice — so no denominator is sought.
# These returns use exactly two units: INR for amounts, PURE for the rest.
_NON_ADDITIVE_UNITS = frozenset({
    "PURE", "PERCENT", "PERCENTAGE", "RATIO", "RATE", "BASISPOINT", "BPS",
})


def _is_share_eligible(row: dict) -> bool:
    """Can a share-of-total be meaningful for this fact?

    Judged on the UNIT, never the concept name. Name matching looked tempting
    but is wrong here: 'MeanEffectiveInterestRateCharged' reads like a rate and
    is declared monetaryItemType with unit INR in this taxonomy, so a
    name-based rule would strip a share it is entitled to.

    A fact with no unit at all is left eligible — the additivity gate is still
    the thing that decides, and this guard only removes cases where a share
    could not be meaningful even if the arithmetic worked.
    """
    unit = str(row.get("unit") or "").strip().upper()
    if not unit:
        return True
    return unit not in _NON_ADDITIVE_UNITS



def compute_share(
    row: dict, all_rows: list[dict], index: dict, label_a: str, label_b: str,
) -> dict | None:
    """Share of the parent total for both periods, or None when unsafe.

    The denominator is the SAME concept one dimension less specific — for

    'AmountOutstanding [Domestic, DoubtfulAssetsOne]' that is

    'AmountOutstanding [Domestic]'. Verified against real data:
        239,779,280,000 / 5,061,076,134,000 = 4.7%

            295,025,000 /    48,550,659,000 = 0.6%

    Returned ONLY when the siblings actually partition the parent (within
    SHARE_TOLERANCE). Dimensions are not always additive — overlapping

    exposure categories sum well past 100% — and a share taken against a

    denominator that is not a total is a wrong number stated confidently.

    No denominator is ever invented: unsafe means omitted.

    """

    base = row.get("concept_base") or row.get("concept", "")

    ck = row.get("context_key") or "BASE"

    # A percentage or ratio is already normalised; a share of it says nothing.
    if not _is_share_eligible(row):
        return None
    pk = _parent_key(ck)

    if pk is None:
        return None

    parent = index.get((base, pk))

    if parent is None:
        return None

    pa, pb = parent.get(label_a), parent.get(label_b)

    va, vb = row.get(label_a), row.get(label_b)

    if not isinstance(pa, (int, float)) or not isinstance(va, (int, float)):
        return None

    if pa == 0:
        return None

    # Additivity gate: every sibling under this parent must sum to it.

    sibs = [
        r for r in all_rows
        if (r.get("concept_base") or r.get("concept", "")) == base
        and _parent_key(r.get("context_key") or "BASE") == pk
    ]

    if len(sibs) < 2:
        return None

    tot_a = sum(r.get(label_a) or 0 for r in sibs)

    if abs(tot_a - pa) > abs(pa) * SHARE_TOLERANCE:
        # The straight sum overshot. That is usually a roll-up sibling being
        # counted alongside its own children - drop those and retest once,
        # against the same tolerance. If it still does not reconcile, the
        # parent is not a total and no share is produced.
        rolled = _rollup_members(sibs, label_a)
        if not rolled:
            return None
        tot_a = sum(r.get(label_a) or 0 for r in sibs if id(r) not in rolled)
        if abs(tot_a - pa) > abs(pa) * SHARE_TOLERANCE:
            return None
        logger.debug(
            "[EXPLAIN] share for %s[%s]: excluded %d roll-up sibling(s) to "
            "reconcile with the parent", base, ck, len(rolled),
        )

    share_a = 100.0 * va / pa

    share_b = (
        100.0 * vb / pb
        if isinstance(pb, (int, float)) and isinstance(vb, (int, float)) and pb
        else None
    )

    return {
        "share_a": round(share_a, 1),
        "share_b": round(share_b, 1) if share_b is not None else None,
        "share_delta_pp": (
            round(share_a - share_b, 1) if share_b is not None else None
        ),
        "parent_name": parent_label(
            base, pk, parent.get("concept_label", ""), parent.get("member_labels"),
        ),
    }

# ── Fact assembly ────────────────────────────────────────────────────────────

def build_facts(
    selected: list[dict], all_rows: list[dict], label_a: str, label_b: str,
) -> list[dict]:
    """Everything the sentence needs, all computed here. The LLM adds nothing."""

    index = _index_rows(all_rows)

    facts: list[dict] = []

    for i, r in enumerate(selected, 1):
        base = r.get("concept_base") or r.get("concept", "")

        ck = r.get("context_key") or "BASE"

        unit = r.get("unit") or ""

        va, vb = r.get(label_a), r.get(label_b)

        pct = r.get("pct_change")

        f = {
            "id": i,
            "concept": base,
            "context_key": ck,
            "dimension": ", ".join(humanise(m) for m in _members(ck)),
            "business_name": business_name(
                base, ck, r.get("concept_label", ""), r.get("member_labels"),
            ),
            "unit": unit,
            "val_a": va,
            "val_b": vb,
            "fmt_a": format_value(va, unit),
            "fmt_b": format_value(vb, unit),
            "pct_change": pct,
            "fmt_pct": format_pct(pct),
            "direction": (
                "increased" if (r.get("diff") or 0) > 0
                else "decreased" if (r.get("diff") or 0) < 0
                else "was unchanged"
            ),
            "section": r.get("section") or "",
            "section_code": r.get("section_code") or "",
            "tier": r.get("importance_tier") or "",
            "regulatory_score": r.get("importance"),
            "priority": r.get("priority"),
            "zero_baseline": pct is None,
        }

        try:
            f["movement_score"] = _movement_of(r)

        except Exception:
            f["movement_score"] = None

        share = compute_share(r, all_rows, index, label_a, label_b)

        if share:
            f.update(share)

        facts.append(f)

    return facts

def _movement_of(row: dict) -> float | None:
    """The movement half of the 60/40 blend, read from the existing scorer."""

    try:
        from backend.tools.xbrl_importance import _movement_score

        return round(_movement_score(row), 1)

    except Exception:
        return None

# ── Deterministic sentence ───────────────────────────────────────────────────

def template_sentence(f: dict) -> str:
    """A correct, complete sentence built from the facts alone.

    FALLBACK ONLY - not the normal output. Used for a single fact when the
    model omitted it or its line failed validation, so the explanation count
    always matches the selection even when the model misbehaves.
    it returns that fails validation is replaced by this.

    Composition preference, per the requested style:
      1. absolute movement (always)

      2. share/composition change (when a safe denominator exists)

      3. percentage (only when it adds something — a five-digit percentage
         communicates less than the two values already do)

    """

    name = f["business_name"]

    a, b = f["fmt_a"], f["fmt_b"]

    if f["zero_baseline"]:
        head = f"{name} was first reported at {a}, with no value in the previous period"

    elif f["direction"] == "was unchanged":
        head = f"{name} was unchanged at {a}"

    else:
        head = f"{name} {f['direction']} from {b} to {a}"

    # Percentage earns its place only in the readable middle range; below that

    # the absolute numbers say it, above it the figure is just noise.

    pct = f.get("pct_change")

    if pct is not None and abs(pct) < 1000 and not f["zero_baseline"]:
        head += f" ({f['fmt_pct']})"

    if f.get("share_a") is not None and f.get("share_b") is not None:
        verb = "raising" if f["share_a"] >= f["share_b"] else "reducing"

        head += (
            f", {verb} its share of {f['parent_name']} "
            f"from {f['share_b']}% to {f['share_a']}%"
        )

    elif f.get("share_a") is not None:
        head += f", taking a {f['share_a']}% share of {f['parent_name']}"

    return head + "."

# ── Factual pattern (optional extra line) ────────────────────────────────────

def pattern_line(facts: list[dict]) -> str:
    """One factual observation across the selected set, or ''.

    Describes only what is counted here. It never names a cause — a uniform

    magnitude across unrelated categories is a fact about the numbers, and any

    explanation for it is outside what this data can support.

    """

    if len(facts) < 3:
        return ""

    bits: list[str] = []

    ups = sum(1 for f in facts if f["direction"] == "increased")

    downs = sum(1 for f in facts if f["direction"] == "decreased")

    if ups == len(facts):
        bits.append(f"all {len(facts)} selected facts increased")

    elif downs == len(facts):
        bits.append(f"all {len(facts)} selected facts decreased")

    else:
        bits.append(f"{ups} increased and {downs} decreased")

    zeros = sum(1 for f in facts if f["zero_baseline"])

    if zeros:
        bits.append(f"{zeros} had no value in the previous period")

    pcts = [abs(f["pct_change"]) for f in facts if f.get("pct_change") is not None]

    if pcts and min(pcts) >= 1000:
        bits.append(
            f"every measured change exceeded {min(pcts):,.0f}%"
        )

    secs = {f["section_code"] for f in facts if f["section_code"]}

    if len(secs) == 1 and facts[0]["section"]:
        bits.append(f"all fall within {facts[0]['section']}")

    return "; ".join(bits).capitalize() + "."

# ── LLM output validation ────────────────────────────────────────────────────

# The model may put the id and its sentence on ONE line ("[1] Text.") or split
# them across two ("[1]" then "Text." beneath). Both are matched: requiring the
# single-line form silently rejected every line llama3.1 produced.
_ID_INLINE_RE = re.compile(r"^\s*(?:[•\-*]\s*)?\[(\d+)\]\s*(.*)$")


def _parse_llm_lines(raw: str) -> dict[int, str]:
    """id -> sentence, tolerant of the layouts a model actually returns.

    Skips any preamble ("Here are the reworded sentences:") because only lines
    carrying an id are considered, and keeps the FIRST sentence for an id so a
    repeated id cannot overwrite an earlier good line.
    """
    out: dict[int, str] = {}
    lines = raw.splitlines()
    k = 0
    while k < len(lines):
        m = _ID_INLINE_RE.match(lines[k])
        if not m:
            k += 1
            continue
        fid, text = int(m.group(1)), m.group(2).strip()
        if not text:
            # Bare "[1]" — the sentence is on the next non-empty line.
            j2 = k + 1
            while j2 < len(lines) and not lines[j2].strip():
                j2 += 1
            if j2 < len(lines) and not _ID_INLINE_RE.match(lines[j2]):
                text = lines[j2].strip()
                k = j2
        if text and fid not in out:
            out[fid] = text
        k += 1
    return out


def _numbers_in(text: str) -> set[str]:
    """Numeric tokens as written, commas removed."""
    return {t.replace(",", "") for t in re.findall(r"\d[\d,]*\.?\d*", str(text))}


def _floats_in(text: str) -> list[float]:
    out: list[float] = []
    for t in _numbers_in(text):
        try:
            out.append(float(t))
        except ValueError:
            continue
    return out


def _allowed_values(f: dict, template: str) -> list[float]:
    """Every number the model is permitted to write for this fact.

    Includes the raw values AND their rendered forms, because a sentence
    quotes "₹4,855 Cr" (4855) while the underlying figure is 48550659000 —
    both are the same fact stated at different scales.
    """
    vals: list[float] = []
    for k in ("val_a", "val_b", "pct_change", "share_a", "share_b",
              "share_delta_pp", "regulatory_score", "priority"):
        v = f.get(k)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    vals.extend(_floats_in(template))
    vals.extend(_floats_in(f.get("fmt_a", "")))
    vals.extend(_floats_in(f.get("fmt_b", "")))
    vals.extend(_floats_in(f.get("fmt_pct", "")))
    return vals


def _is_supported(n: float, allowed: list[float]) -> bool:
    """Is this number one of the fact's own, allowing for rounding?

    The check must be NUMERIC, not textual. A model that writes the percentage
    as "+10,324%" is quoting 10324.320160103285 correctly — comparing the digit
    strings rejected it as invented, which is why every polished line was being
    thrown away. 1% relative tolerance covers any sane rounding; a genuinely
    fabricated figure still matches nothing.
    """
    for a in allowed:
        if a == n:
            return True
        if a and abs(n - a) <= abs(a) * 0.01:
            return True
        # A power-of-ten allowance was tried here and removed: it accepted
        # 103,486 as a "scaling" of 10,324, which is exactly the kind of
        # order-of-magnitude error this check exists to catch. The Cr/Lakh
        # renderings are already in `allowed` via fmt_a/fmt_b, so nothing
        # legitimate needs it.
    return False


# Multiplier words assert a RATIO. The model wrote "more than quadrupled" for a
# 162x increase — no new number appears, so the numeric check cannot see it,
# but the claim is wrong. Python already supplies both values; describing the
# ratio in words adds nothing and can only be inaccurate.
_MULTIPLIER_RE = re.compile(
    r"\b(doubl\w*|tripl\w*|quadrupl\w*|quintupl\w*|halv\w*|"
    r"[a-z]+-?fold|twice|thrice)\b",
    re.I,
)


def validate_and_merge(raw: str, facts: list[dict]) -> tuple[list[str], int]:
    """Per-fact merge of LLM output over the deterministic templates.

    Returns (sentences, n_from_llm). Every fact ALWAYS gets exactly one

    sentence: a validated LLM line where one exists, its own template

    otherwise. The count can therefore never drift from the selection, and no

    output is ever truncated to fit a bullet quota.

    A line is rejected when it is missing, duplicated, empty, or introduces a

    number that was not in that fact's own figures — the last check is what

    stops a reworded sentence from quietly changing an amount.

    """

    templates = [template_sentence(f) for f in facts]

    if not raw:
        return templates, 0

    by_id = _parse_llm_lines(raw)

    # Facts and their permitted figures, computed once.
    allowed_by_id = {
        f["id"]: _allowed_values(f, t) for f, t in zip(facts, templates)
    }

    def _supports(fid: int, text: str) -> bool:
        """Is every number in `text` one of fact `fid`'s own figures?"""
        al = allowed_by_id.get(fid) or []
        return all(_is_supported(n, al) for n in _floats_in(text))

    # ── Re-home mislabelled lines ────────────────────────────────────────────
    # llama3.1 frequently returns correct sentences under SHIFTED ids — fact 1's
    # slot carrying fact 2's figures. Rejecting on the claimed id threw away
    # good work and fell back to templates for almost every line. So when a
    # line does not fit the fact it claims, look for the fact it DOES fit; if
    # exactly one qualifies, that is where it belongs. Ambiguous or unmatched
    # lines are still discarded — this relaxes the ID, never the numbers.
    resolved: dict[int, str] = {}
    homeless: list[str] = []
    for fid, text in by_id.items():
        if fid in allowed_by_id and _supports(fid, text):
            resolved.setdefault(fid, text)
        else:
            homeless.append(text)

    for text in homeless:
        candidates = [
            f["id"] for f in facts
            if f["id"] not in resolved and _supports(f["id"], text)
        ]
        if len(candidates) == 1:
            resolved[candidates[0]] = text
        else:
            logger.info(
                "[EXPLAIN] discarding line matching %d fact(s): %.60s",
                len(candidates), text,
            )

    out: list[str] = []
    used = 0
    for f, tmpl in zip(facts, templates):
        cand = resolved.get(f["id"], "")
        if not cand or len(cand) < 15:
            out.append(tmpl)
            continue
        mult = _MULTIPLIER_RE.search(cand)
        if mult:
            logger.info(
                "[EXPLAIN] fact %s: unsupported ratio claim %r — using template",
                f["id"], mult.group(0),
            )
            out.append(tmpl)
            continue
        out.append(cand if cand.endswith(".") else cand + ".")
        used += 1
    return out, used

# ── Prompt ───────────────────────────────────────────────────────────────────

def _context_hint(f: dict) -> str:
    """Which extra context, if any, is worth putting in this sentence.

    Not a sentence and not a template — a one-line steer naming the field that
    adds the most for this particular fact, or saying plainly that there is
    none. Ordered by how much each adds to a business reader:

      first-time reporting > share of parent > readable percentage > nothing

    A six-digit percentage is deliberately called out as NOT worth including:
    it is true, but it tells a reader less than the two amounts already do.
    """
    if f.get("zero_baseline"):
        return "this is the first period it has been reported - say so"
    if f.get("share_a") is not None and f.get("share_b") is not None:
        return (
            f"share of {f['parent_name']} moved from {f['share_b']}% to "
            f"{f['share_a']}% - this is the composition shift, use it"
        )
    pct = f.get("pct_change")
    if pct is not None and abs(pct) < 1000:
        return f"the percentage ({f['fmt_pct']}) is readable at this size - worth including"
    if pct is not None:
        return "none - the percentage is too large to be informative, use the amounts alone"
    return "none - the two amounts are the whole story"


def build_prompt(facts: list[dict], label_a: str, label_b: str, report_name: str) -> str:
    """The LLM writes the explanations; Python only supplies the facts.

    Deliberately presents each fact as a labelled BLOCK OF FIELDS, not as a
    draft sentence. An earlier version handed the model a finished sentence and
    asked it to reword it — it echoed the sentence back, so every line came out
    in the same shape. Giving it only the data, and telling it which choices
    are its to make, is what produces varied, genuinely written explanations.

    The model decides what to SAY. Python decides what is TRUE: every number
    here is pre-computed, and validate_and_merge rejects any line that departs
    from them.
    """
    blocks = []
    for f in facts:
        parts = [f"FACT [{f['id']}]"]
        # Hint FIRST. It was last, and llama3.1 read the values at the top of
        # the block and skimmed the rest — supplied shares went unused every
        # time. Leading with it is what actually changes the output.
        parts.append(f"  MUST INCLUDE: {_context_hint(f)}")
        parts.append(f"  concept: {f['business_name']}")
        if f.get("dimension"):
            parts.append(f"  dimension / category: {f['dimension']}")
        parts.append(f"  previous value ({label_b}): {f['fmt_b']}")
        parts.append(f"  current value ({label_a}): {f['fmt_a']}")
        parts.append(f"  direction: {f['direction']}")
        parts.append(f"  percentage change: {f['fmt_pct']}")
        if f.get("share_a") is not None and f.get("share_b") is not None:
            parts.append(f"  previous share of parent total: {f['share_b']}%")
            parts.append(f"  current share of parent total: {f['share_a']}%")
            parts.append(f"  parent total: {f['parent_name']}")
        if f.get("section"):
            parts.append(f"  section: {f['section']}")
        if f.get("tier"):
            parts.append(f"  regulatory importance: {f['tier']}")
        if f["zero_baseline"]:
            parts.append("  note: nothing was reported for this in the previous period")
        # An explicit steer on WHICH context matters for this fact. Listing the
        # fields was not enough — the model read them and still wrote only the
        # two amounts, leaving a supplied share unused. Python decides what is
        # AVAILABLE and worth using; the model still decides how to say it.
        blocks.append("\n".join(parts))
    data = "\n\n".join(blocks)

    return (
        "You are a banking analyst explaining a regulatory return comparison "
        "to a business reader.\n\n"
        f"Report: {report_name or 'RBI Banking Report'}\n"
        f"Current period: {label_a}\n"
        f"Previous period: {label_b}\n\n"
        "Below are facts that have already been calculated. Write ONE short "
        "explanation for each, in your own words.\n\n"
        f"{data}\n\n"
        "WHAT YOU DECIDE\n"
        "Each fact below lists only the context that exists for it. Read that "
        "list and ask: what is the most useful factual takeaway here for a "
        "business reader? Write that, and nothing more.\n"
        "- The two amounts are the backbone of every explanation. Lead with "
        "them.\n"
        "- If a SHARE OF THE PARENT TOTAL is listed, it usually earns its "
        "place: it says how the composition shifted, which the amounts alone "
        "cannot. Use it unless it genuinely adds nothing.\n"
        "- If the fact was FIRST REPORTED this period, say so plainly. That is "
        "more useful than any percentage.\n"
        "- The PERCENTAGE is optional. Use it when it tells the reader "
        "something the amounts do not - a moderate move is easier to grasp as "
        "a percentage. On very large moves it says less than the amounts "
        "already do, so leave it out.\n"
        "- Name the category or section only where it genuinely helps identify "
        "what moved.\n\n"
        "IF A FACT HAS NO EXTRA CONTEXT, A SHORT SENTENCE IS THE RIGHT "
        "ANSWER.\n"
        "Nothing is missing from the list - if only two amounts are given, "
        "then two amounts are the whole story, and 'X increased from A to B.' "
        "is a complete and correct explanation. Never pad a line to make it "
        "look more considered, and never speculate to fill space.\n\n"
        "TONE\n"
        "Write like an analyst stating a fact, not like a headline. Let the "
        "numbers carry the magnitude.\n"
        "- Do NOT use: staggering, enormous, massive, dramatic, dramatically, "
        "substantial, significant, extraordinary, skyrocketed, soared, "
        "plummeted, alarming, remarkable, notable, sharp spike.\n"
        "- Plain verbs are right: increased, rose, grew, expanded, reached, "
        "moved from, fell, declined, held steady, was first reported at, "
        "accounted for.\n"
        "- Do not reach for a synonym just to sound different. Accuracy and "
        "plain wording matter more than variety; vary the sentence SHAPE "
        "rather than hunting for unusual verbs.\n"
        "- Do not open every line the same way, and do not end every line with "
        "a percentage.\n"
        "- Shorter is better when it carries the same facts. A longer sentence "
        "must earn its length with information, not adjectives.\n\n"        "WHAT YOU MUST NOT DO\n"
        "- Never invent, change, round differently or re-scale any number. "
        "Use only the figures given for that fact.\n"
        "- Never compute anything, including a share or a ratio.\n"
        "- Never describe a change as a multiple ('doubled', 'tripled', "
        "'fourfold'). Give the values instead.\n"
        "- Never give a reason or cause. No business strategy, management "
        "intent, economic conditions, market stress, liquidity problems, "
        "credit deterioration, regulatory breach, non-compliance or "
        "supervisory consequence.\n"
        "- Never use: due to, because, indicates, suggests, reflects, likely, "
        "may attract supervisory attention.\n"
        "- Never merge two facts into one sentence.\n"
        "- Never write a field dump such as "
        "'Name: X to Y; share: A% to B%; section: Z'.\n\n"
        "THE 'MUST INCLUDE' LINE\n"
        "Each fact opens with a MUST INCLUDE line. When it names a share "
        "movement or first-time reporting, your sentence for that fact HAS TO "
        "carry that information - a sentence with only the two amounts is "
        "wrong for that fact. When it says 'none', the two amounts ARE the "
        "answer and you must not add anything else.\n\n"
        "FORMAT\n"
        f"- Exactly {len(facts)} lines, one per fact, in the order given.\n"
        "- Start each line with the fact id in brackets: [1], [2], ...\n"
        "- One sentence per line. No heading, introduction or conclusion.\n\n"
        "The lines below show the RANGE expected - some use extra context "
        "because it was supplied, others correctly use none. They are not "
        "templates; do not copy their structure:\n"
        "[1] Doubtful Assets One in domestic operations increased from "
        "₹29.5 Cr to ₹23,978 Cr, raising its share of the domestic book from "
        "0.6% to 4.7%.   (share was given, and it is the useful point)\n"
        "[2] Loss provisioning reached ₹5,260 Cr, up from ₹32.4 Cr.   "
        "(no share was given - two amounts are the whole story)\n"
        "[3] Restructured standard advances grew from ₹6.3 Cr to ₹261 Cr "
        "(+4,042%).   (a moderate move reads well as a percentage)\n"
        "[4] Net NPAs rose from ₹29 Cr to ₹30,040 Cr.   (percentage omitted "
        "- at six digits it says less than the amounts)\n"
        "[5] Overseas netting for NPAs was first reported this period, at "
        "₹1,495 Cr.   (first-time reporting is the useful fact)\n"
        "[6] Standard assets accounted for 90.9% of the domestic book, down "
        "from 96.0%, on a rise from ₹4,659 Cr to ₹460,291 Cr.   "
        "(share-led, because the composition shift is the point)\n"
        "Write the sentence only - never the parenthetical note.\n"
    )


# ── Generation ──────────────────────────────────────────────────
async def generate_explanations(
    rows: list[dict],
    label_a: str,
    label_b: str,
    report_name: str = "",
    timeout: float | None = None,
    limit: int = SUMMARY_CONCEPT_LIMIT,
    all_rows: list[dict] | None = None,
    polish: bool = True,
) -> str:
    """One business sentence per selected high-priority fact.

    Python selects the facts and computes every number; the LLM writes the
    prose. Templates are prepared alongside but used only where a model line
    is missing or fails validation.

    Never raises and never returns fewer sentences than facts.
    """
    import httpx

    if not rows:
        return ""

    source = all_rows or rows
    selected = select_facts(rows, limit=limit, label_a=label_a, label_b=label_b)
    if not selected:
        logger.info("[EXPLAIN] no Critical/High facts to explain")
        return ""

    facts = build_facts(selected, source, label_a, label_b)
    templates = [template_sentence(f) for f in facts]
    pattern = pattern_line(facts)

    def _render(sentences: list[str], via: str) -> str:
        # One bullet per selected fact - and nothing else in that list. The
        # cross-cutting observation is appended as its own labelled block so
        # it can never be mistaken for, or displace, a concept explanation.
        body = "\n".join(f"• {s}" for s in sentences)
        if pattern:
            body += f"\n\nOverall pattern: {pattern}"
        logger.info(
            "[EXPLAIN] rendered %d explanation(s) via %s (limit=%d)",
            len(sentences), via, limit,
        )
        return "AI Summary:\n" + body

    # polish=False is the INLINE path: return the deterministic text at once
    # rather than holding the comparison response open for a model call. The
    # frontend then requests the polished version from /compare-summary, which
    # has a realistic budget.
    if not polish:
        return _render(templates, "template(draft)")

    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    model    = os.getenv("OLLAMA_COMPARE_MODEL", "llama3.1:latest")

    if timeout is None:
        timeout = float(os.getenv("OLLAMA_SUMMARY_TIMEOUT", "8"))

    prompt = build_prompt(facts, label_a, label_b, report_name)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
        "options": {
            "temperature": 0.45,
            # Room for one sentence per fact plus overhead. The old 450 was
            # sized for five bullets and would truncate twenty.
            "num_predict": max(600, 90 * len(facts)),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            resp = await client.post(f"{base_url}/api/chat", json=payload)

            resp.raise_for_status()

            content = (resp.json().get("message", {}).get("content") or "").strip()

    except Exception as exc:
        logger.info("[EXPLAIN] LLM unavailable (%s) — using Python templates", exc)

        return _render(templates, "template")

    sentences, n_llm = validate_and_merge(content, facts)

    return _render(sentences, f"llm({n_llm}/{len(facts)})")
