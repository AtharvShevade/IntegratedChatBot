"""Scoring for STT output.

Five accuracy metrics and one latency aggregator. Two design rules run through
all of them:

  * **No fuzzy correction anywhere.** We are measuring raw STT behaviour. If the
    harness quietly snapped "seems ror" to "CIMS_ROR" it would score the
    correction, not the model, and we would choose a model on the strength of
    our own post-processing.

  * **Normalization is for WER/CER only.** Entity preservation runs on the RAW
    strings, because case and punctuation are exactly what distinguishes
    "CIMS_ROR" from "cims ror".

Latency helpers are imported from the multilingual harness rather than
reimplemented -- percentile() and latency_summary() already do this job and a
second copy would drift.
"""
from __future__ import annotations

import re
import unicodedata

from rapidfuzz.distance import Levenshtein

# Reused rather than duplicated. Nearest-rank percentile and the p50/p95/max
# summary shape are already settled in the multilingual harness.
from eval.multilingual.metrics import percentile, latency_summary  # noqa: F401

from eval.stt import config

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

# Punctuation to drop before scoring. Devanagari danda and Arabic comma/
# question mark are included: they are punctuation, and counting them as
# character errors would inflate CER for exactly the two languages where CER
# is the headline metric.
#
# UNDERSCORE IS DELIBERATELY ABSENT. In this domain it is part of the word --
# CIMS_ROR, FMRD09_FTD -- so stripping it would split one token into two and
# charge the model an insertion for spelling an identifier correctly.
_PUNCT = r"""!"#$%&'()*+,\-./:;<=>?@\[\\\]^`{|}~“”‘’«»—–…।॥،؛؟"""
_PUNCT_RE = re.compile(f"[{re.escape(_PUNCT)}]")
_WS_RE = re.compile(r"\s+")

# Arabic diacritics (harakat). Whisper is inconsistent about emitting them and
# they carry no meaning for our purposes, so they are stripped from both sides.
_ARABIC_DIACRITICS_RE = re.compile(r"[ً-ٰٟۖ-ۭ]")

# Indic and Arabic-Indic digits -> ASCII, so "31" and "٣١" and "३१" compare
# equal. Digit SHAPE is checked separately by entity preservation.
_DIGIT_MAP = {}
for _base, _zero in (("arabic", 0x0660), ("extended_arabic", 0x06F0), ("devanagari", 0x0966)):
    for _i in range(10):
        _DIGIT_MAP[chr(_zero + _i)] = str(_i)


def normalize(text: str, lang: str = "en") -> str:
    """Lowercase, strip punctuation/diacritics, unify digits, collapse spaces.

    Applied IDENTICALLY to reference and hypothesis, and identically across
    every model under comparison -- otherwise the comparison measures the
    normalizer.
    """
    if not text:
        return ""
    out = unicodedata.normalize("NFKC", text)
    out = "".join(_DIGIT_MAP.get(ch, ch) for ch in out)
    if lang == "ar":
        out = _ARABIC_DIACRITICS_RE.sub("", out)
    out = _PUNCT_RE.sub(" ", out)
    out = out.lower()
    return _WS_RE.sub(" ", out).strip()


# ---------------------------------------------------------------------------
# WER / CER
# ---------------------------------------------------------------------------

def wer(reference: str, hypothesis: str, lang: str = "en") -> float | None:
    """Word error rate as a percentage, or None when there is no reference.

    Levenshtein over TOKEN sequences (rapidfuzz accepts lists), which is the
    standard definition: (S + D + I) / N.
    """
    ref = normalize(reference, lang).split()
    hyp = normalize(hypothesis, lang).split()
    if not ref:
        return None
    return 100.0 * Levenshtein.distance(ref, hyp) / len(ref)


def cer(reference: str, hypothesis: str, lang: str = "en") -> float | None:
    """Character error rate as a percentage.

    The headline metric for Hindi and Arabic. Word-level scoring is unstable
    there: Devanagari compounds and Arabic clitics mean a single perceptual
    word may be written joined or split, so WER swings on orthography rather
    than on what was heard. Spaces are dropped so that a differently-segmented
    but identical transcription scores 0.
    """
    ref = normalize(reference, lang).replace(" ", "")
    hyp = normalize(hypothesis, lang).replace(" ", "")
    if not ref:
        return None
    return 100.0 * Levenshtein.distance(ref, hyp) / len(ref)


def headline_metric(lang: str) -> str:
    """Which number leads for this language. EN/FR -> WER, HI/AR -> CER."""
    return "cer" if lang in ("hi", "ar") else "wer"


# ---------------------------------------------------------------------------
# Entity preservation
# ---------------------------------------------------------------------------

def _protected(text: str) -> list[str]:
    """Identifiers/numbers/dates in a string, via the app's own definition.

    Imported lazily so the metrics module can be used (and tested) without
    pulling in the backend package.
    """
    from backend.i18n import protect
    return protect.protected_tokens(text)


def entities_in(text: str) -> list[str]:
    """The entity list for a reference, when the dataset does not declare one.

    Reuses backend/i18n/protect.py, which is the same definition the
    translation boundary protects -- so "an entity" means the same thing in
    both halves of the system rather than being invented twice.
    """
    return _protected(text)


def entity_preservation(reference: str, hypothesis: str,
                        declared: list[str] | None = None) -> dict:
    """Fraction of reference entities reproduced EXACTLY in the hypothesis.

    Exact, case-sensitive substring containment. No fuzzy matching: the
    question is whether the raw transcript can be trusted to carry
    "CIMS_ROR" through to a pipeline that will match on it, and "cims ror"
    cannot. Where the pipeline's own fuzzy resolution saves a near-miss is a
    separate question, deliberately not conflated with this one.

    ``declared`` lets a dataset record pin the entities that matter for that
    clip; otherwise they are derived from the reference.
    """
    wanted = list(declared) if declared else entities_in(reference)
    # De-duplicate while preserving order, so a term said twice is not
    # double-counted.
    seen: set[str] = set()
    unique = [e for e in wanted if not (e in seen or seen.add(e))]
    if not unique:
        return {"total": 0, "preserved": 0, "missing": [], "pct": None}
    missing = [e for e in unique if e not in hypothesis]
    preserved = len(unique) - len(missing)
    return {
        "total": len(unique),
        "preserved": preserved,
        "missing": missing,
        "pct": 100.0 * preserved / len(unique),
    }


# ---------------------------------------------------------------------------
# Translation leakage
# ---------------------------------------------------------------------------

_SCRIPT_RANGES = {
    "devanagari": (0x0900, 0x097F),
    "arabic": (0x0600, 0x06FF),
}

# Frequent French function words. Used only for French, where script cannot
# separate a translation from a transcription because both are Latin.
_FRENCH_MARKERS = {
    "le", "la", "les", "de", "des", "du", "un", "une", "je", "il", "elle",
    "est", "et", "que", "qui", "pour", "dans", "mon", "ma", "mes", "vous",
    "nous", "sur", "avec", "au", "aux", "ce", "cette", "quel", "quelle",
    "statut", "rapport", "voudrais", "connaitre", "connaître",
}


def _script_share(text: str, script: str) -> float:
    """Share of letters belonging to a script, ignoring digits and punctuation."""
    lo, hi = _SCRIPT_RANGES[script]
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if lo <= ord(ch) <= hi) / len(letters)


def translation_leak(reference: str, hypothesis: str, lang: str,
                     min_script_share: float = 0.30) -> bool | None:
    """True when non-English speech came back as English.

    STT must transcribe, never translate: the text pipeline expects the user's
    own language and does its own translation, with entity masking. A Whisper
    deployment left on task="translate" would silently defeat all of that.

    Decidable exactly for Hindi and Arabic -- a Devanagari or Arabic reference
    whose transcript is essentially all Latin letters is a leak, whatever the
    words are.

    For FRENCH this is a HEURISTIC, and is reported as such: both languages use
    Latin script, so the test is the absence of any common French function word
    in a transcript that has words in it. Returns None for English (nothing to
    leak to) and None when the heuristic cannot decide.
    """
    if lang == "en":
        return None
    hyp = (hypothesis or "").strip()
    if not hyp:
        return None                      # empty is a hallucination question

    script = config.SCRIPTS.get(lang)
    if script in _SCRIPT_RANGES:
        # If the REFERENCE is not in its own script the clip is mislabelled;
        # do not score it rather than report a false leak.
        if _script_share(reference, script) < min_script_share:
            return None
        return _script_share(hyp, script) < min_script_share

    if lang == "fr":
        tokens = set(normalize(hyp, "fr").split())
        if not tokens:
            return None
        return not (tokens & _FRENCH_MARKERS)

    return None


# ---------------------------------------------------------------------------
# Hallucination
# ---------------------------------------------------------------------------

def is_hallucination(hypothesis: str, condition: str) -> bool | None:
    """True when a non-speech clip produced words.

    Explicit because the deployed service already does this: measured, silence
    returned "You" and a 220Hz tone returned "." and "Thank you.". A single
    stray full stop is not a hallucination, so scoring is done on the
    normalized text -- punctuation-only output normalizes to empty.

    Returns None for clips that DO contain speech, where the concept does not
    apply.
    """
    if condition not in config.NON_SPEECH_CONDITIONS:
        return None
    return bool(normalize(hypothesis or "", "en"))


# ---------------------------------------------------------------------------
# Real-time factor
# ---------------------------------------------------------------------------

def rtf(processing_ms: float | None, audio_seconds: float | None) -> float | None:
    """processing time / audio duration. Below 1.0 is faster than real time."""
    if not processing_ms or not audio_seconds:
        return None
    return (processing_ms / 1000.0) / audio_seconds


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def _pct(numerator: int, denominator: int) -> float | None:
    return 100.0 * numerator / denominator if denominator else None


def aggregate(records: list[dict]) -> dict:
    """Roll per-clip records up into the numbers the acceptance table needs."""
    scored = [r for r in records if not r.get("_meta") and not r.get("error")]

    by_lang: dict[str, dict] = {}
    for lang in config.LANGUAGES:
        rows = [r for r in scored if r.get("language") == lang]
        if not rows:
            continue
        by_lang[lang] = {
            "n": len(rows),
            "wer": _mean([r.get("wer") for r in rows]),
            "cer": _mean([r.get("cer") for r in rows]),
            "headline": headline_metric(lang),
            "latency_ms": latency_summary([r.get("latency_ms") for r in rows]),
        }

    # Headline accuracy, split the way the acceptance table asks for it.
    en_fr = [r.get("wer") for r in scored if r.get("language") in ("en", "fr")]
    hi_ar = [r.get("cer") for r in scored if r.get("language") in ("hi", "ar")]

    # Entity preservation is pooled over ENTITIES, not averaged over clips: a
    # clip with six identifiers should weigh more than a clip with one.
    ent_total = sum(r.get("entity_total") or 0 for r in scored)
    ent_kept = sum(r.get("entity_preserved") or 0 for r in scored)

    leaks = [r.get("translation_leak") for r in scored if r.get("translation_leak") is not None]
    halls = [r.get("hallucination") for r in scored if r.get("hallucination") is not None]

    by_condition: dict[str, dict] = {}
    for condition in config.CONDITIONS:
        rows = [r for r in scored if r.get("condition") == condition]
        if rows:
            by_condition[condition] = {
                "n": len(rows),
                "wer": _mean([r.get("wer") for r in rows]),
                "cer": _mean([r.get("cer") for r in rows]),
            }

    return {
        "clips_scored": len(scored),
        "clips_errored": len([r for r in records if r.get("error")]),
        "wer_en_fr_pct": _mean(en_fr),
        "cer_hi_ar_pct": _mean(hi_ar),
        "entity_total": ent_total,
        "entity_preserved": ent_kept,
        "entity_preservation": _pct(ent_kept, ent_total),
        "translation_leak_pct": _pct(sum(1 for v in leaks if v), len(leaks)),
        "translation_leak_n": len(leaks),
        "hallucination_pct": _pct(sum(1 for v in halls if v), len(halls)),
        "hallucination_n": len(halls),
        "latency_ms": latency_summary([r.get("latency_ms") for r in scored]),
        "rtf": _mean([r.get("rtf") for r in scored]),
        "by_language": by_lang,
        "by_condition": by_condition,
    }


def aggregate_latency(records: list[dict]) -> dict:
    """Roll the latency sweep up per audio duration.

    Kept separate from aggregate() because the sweep has no transcript to
    score -- it answers "how long does N seconds of audio take", which is the
    question the acceptance table's p95 rows ask.
    """
    out: dict[str, dict] = {}
    rows = [r for r in records if not r.get("_meta") and r.get("audio_seconds")]
    for seconds in sorted({r["audio_seconds"] for r in rows}):
        group = [r for r in rows if r["audio_seconds"] == seconds]
        warm = [r for r in group if not r.get("cold")]
        cold = [r for r in group if r.get("cold")]
        out[str(seconds)] = {
            "n": len(group),
            "audio_seconds": seconds,
            "wall_ms": latency_summary([r.get("latency_ms") for r in group]),
            "warm_ms": latency_summary([r.get("latency_ms") for r in warm]),
            "cold_ms": latency_summary([r.get("latency_ms") for r in cold]),
            "server_ms": latency_summary([r.get("processing_ms") for r in group
                                          if r.get("processing_ms")]),
            "rtf": _mean([r.get("rtf") for r in warm]) or _mean([r.get("rtf") for r in group]),
        }
    return out
