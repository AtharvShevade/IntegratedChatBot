"""Centralised query normalisation for the DBQA module.

Pipeline (in order):
  1. Lowercase
  2. Punctuation → space
  3. Typo correction   (whole-word, compiled regex, fast path)
  4. Synonym expansion (whole-word, abbreviation → canonical)
  5. Collapse whitespace
  6. Optionally strip stopwords

Public API::

    normalize(query)              → canonical string  (stopwords stripped by default)
    normalize(query, strip_stops=False)  → with prepositions kept (entity extraction)
    tokenize(query)               → list of meaningful tokens
"""
from __future__ import annotations

import re

# ── Synonym / abbreviation map ────────────────────────────────────────────────
# Maps short forms to canonical words.  Applied as whole-word substitutions.
_SYNONYMS: dict[str, str] = {
    # Structural abbreviations
    "dept":         "department",
    "depts":        "departments",
    "usr":          "user",
    "usrs":         "users",
    "ret":          "return",
    "rets":         "returns",
    "rpt":          "report",
    "rpts":         "reports",
    "mgr":          "manager",
    "sys":          "system",
    "info":         "information",
    "cfg":          "configuration",
    "config":       "configuration",
    "auth":         "authentication",
    "perms":        "permissions",
    "perm":         "permission",
    "priv":         "privilege",
    "privs":        "privileges",
    # Status shortcuts
    "actv":         "active",
    "inactv":       "inactive",
    "dis":          "disabled",
    "ena":          "enabled",
    # Action shortcuts
    "chk":          "check",
    "lst":          "list",
    "shw":          "show",
    "fnd":          "find",
    # Domain-specific
    "nonxbrl":      "non_xbrl",
    "lvl":          "level",
    "lvls":         "levels",
    "grp":          "group",
    "org":          "organisation",
    "organization": "organisation",
    # Common two-word contractions written as one
    "userid":       "user id",
    "loginid":      "login id",
    "deptid":       "department id",
    "roleid":       "role id",
}

# ── Typo-correction map ───────────────────────────────────────────────────────
_TYPO_MAP: dict[str, str] = {
    "departement":  "department",
    "deparment":    "department",
    "departemnt":   "department",
    "useer":        "user",
    "uuser":        "user",
    "satus":        "status",
    "statis":       "status",
    "statuss":      "status",
    "rolee":        "role",
    "roel":         "role",
    "rolles":       "roles",
    "permision":    "permission",
    "permisions":   "permissions",
    "permisison":   "permission",
    "assigend":     "assigned",
    "assinged":     "assigned",
    "acces":        "access",
    "aceess":       "access",
    "activee":      "active",
    "actve":        "active",
    "inactve":      "inactive",
    "submision":    "submission",
    "submisson":    "submission",
    "instace":      "instance",
    "instanc":      "instance",
    "loging":       "login",
    "loggin":       "login",
    "faild":        "failed",
    "failedd":      "failed",
    "recod":        "record",
    "reocrd":       "record",
    "retrn":        "return",
    "retrun":       "return",
    "aproved":      "approved",
    "approvd":      "approved",
    "pendig":       "pending",
    "penidng":      "pending",
    "adminstrator": "administrator",
    "adminstration":"administration",
}

# ── Stopwords ─────────────────────────────────────────────────────────────────
_STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall",
    "i", "me", "my", "we", "our", "you", "your",
    "it", "its", "this", "that", "these", "those",
    "and", "or", "but", "if", "then", "so", "yet",
    "please", "can", "tell", "give", "want", "need", "know",
    "what", "who", "which", "where", "when", "how", "why",
})

# ── Compiled patterns (built once at import time for performance) ─────────────
_PUNCT_RE = re.compile(r"[?!.,;:()\[\]{}/\\\"'`]")
_MULTI_SPACE_RE = re.compile(r"\s{2,}")

_SYNONYM_RES: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v)
    for k, v in _SYNONYMS.items()
]
_TYPO_RES: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v)
    for k, v in _TYPO_MAP.items()
]


# ── Public API ────────────────────────────────────────────────────────────────

def normalize(query: str, *, strip_stops: bool = True) -> str:
    """Return a cleaned, canonical form of *query*.

    Args:
        query:        Raw user input string.
        strip_stops:  When True (default), stopwords are removed.
                      Pass False when prepositions are needed to anchor
                      entity names (e.g. "users in Finance").

    Returns:
        Normalised string suitable for regex intent matching.
    """
    if not query:
        return ""

    s = query.strip().lower()
    s = _PUNCT_RE.sub(" ", s)

    # Typo correction first so synonyms match corrected words
    for pattern, replacement in _TYPO_RES:
        s = pattern.sub(replacement, s)

    for pattern, replacement in _SYNONYM_RES:
        s = pattern.sub(replacement, s)

    s = _MULTI_SPACE_RE.sub(" ", s).strip()

    if strip_stops:
        words = [w for w in s.split() if w not in _STOP_WORDS]
        s = " ".join(words)

    return s


def tokenize(query: str) -> list[str]:
    """Return non-trivial normalised tokens from *query*."""
    return [w for w in normalize(query).split() if len(w) > 1]
