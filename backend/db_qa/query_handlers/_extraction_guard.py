"""One question: does this extracted entity name look like a NAME the user
typed, or like a fragment of their sentence that the parser mis-captured?

Internal parser output must never be quoted back to the user. "Department
'has most return' was not found." reads as though the system searched for a
department literally called "has most return" and came up empty — it
advertises that a regex mis-fired, and it sends the user off looking for a
name they never typed. The honest response in that case is that the QUESTION
wasn't understood.

This is deliberately only consulted AFTER a lookup has already failed, so
the worst case is choosing the wrong one of two error messages. It never
suppresses a real answer.
"""
from __future__ import annotations

import re

UNDERSTAND_FAILURE_MSG = (
    "Sorry, I couldn't understand your request. Could you please rephrase it?"
)

# Sentence grammar: auxiliaries, question words, prepositions, quantifiers,
# determiners. None of these ever START a real department/role/return name.
_FUNCTION_WORDS = frozenset({
    "a", "an", "the", "this", "that", "these", "those", "any", "all", "some",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "has", "have", "had", "do", "does", "did", "can", "could", "will",
    "would", "shall", "should", "may", "might", "must",
    "which", "what", "who", "whom", "whose", "where", "when", "why", "how",
    "of", "in", "on", "at", "to", "for", "from", "by", "with", "about",
    "into", "over", "under", "and", "or", "but", "not", "no",
    "my", "our", "your", "their", "its", "his", "her",
    "most", "least", "fewest", "maximum", "minimum", "highest", "lowest",
    "many", "much", "more", "less", "each", "every", "along", "than", "then",
    "there", "here", "currently", "still", "also", "only", "just",
})

# Question vocabulary that is never, on its own, a name. Deliberately does
# NOT include the entity type nouns: this data has a department called
# "Dept 1", a role called "Admin User" and 30-odd returns called "Form ..."
# / "... Return". Checked against all 405 real names before narrowing —
# treating a type noun as a garbage signal flagged 39 of them.
_QUESTION_WORDS = frozenset({
    "access", "accessible", "assigned", "assign", "system", "list", "lists",
    "active", "inactive", "profile", "detail", "details", "status",
    "permission", "permissions", "modules", "count", "counts", "number",
})

# A type noun governed by a preposition is a captured sentence fragment, not
# a name — "ID of department Ghost", "in role Tester". A real name may well
# contain "of" ("Form I (SLR of StCB/DCCBs)"), just never in this shape.
_FRAGMENT_RE = re.compile(
    r"\b(?:of|in|for|to|from|by|with|under)\s+"
    r"(?:departments?|depts?|roles?|returns?|forms?|modules?|users?)\b",
    re.IGNORECASE,
)


def not_found_summary(template: str, name: str | None, empty_msg: str) -> str:
    """The three-way not-found message every entity lookup should produce.

    `template` keeps each call site's existing wording and takes one {name}
    placeholder. Nothing extracted -> the caller's own "please specify"
    prompt; extracted grammar -> the generic rephrase message; a real name
    -> that name, quoted.
    """
    n = (name or "").strip()
    if not n:
        return empty_msg
    if looks_like_extraction_garbage(n):
        return UNDERSTAND_FAILURE_MSG
    return template.format(name=n)


def looks_like_extraction_garbage(name: str | None) -> bool:
    """True when `name` should NOT be quoted back to the user.

    Three signals, any one of which is enough:

      1. It STARTS with a function word — "has most return", "are currently
         active", "does my department". A real name does not.
      2. Every word is grammar or question vocabulary — "along", "in the
         system".
      3. It contains a preposition-governed type noun — "ID of department
         Ghost".

    A real name that merely CONTAINS a function word is kept, so a genuine
    miss on "Bank of India" still reports that name rather than pretending
    the question was unparseable. Digits count as word characters here:
    without that, "Dept 1" tokenises to just ["dept"] and reads as pure
    grammar.
    """
    text = (name or "").strip()
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    if not words:
        return True
    # Signal 1 reads the first WHITESPACE-delimited token, not the first
    # alphanumeric run: four real returns are named "Not_in_Use_CIMS_..."
    # and splitting on the underscore made "not" their first word.
    first = re.split(r"\s+", text.lower())[0].strip(".,;:'\"?!()[]")
    if first in _FUNCTION_WORDS:
        return True
    if all(w in _FUNCTION_WORDS or w in _QUESTION_WORDS for w in words):
        return True
    return bool(_FRAGMENT_RE.search(name or ""))
