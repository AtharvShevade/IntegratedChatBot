"""M-17: shared regex extraction helpers for the DB Q&A intent classifiers.

Moved out of backend/db_qa/intent_classifier.py (the legacy ~90-rule
classifier) verbatim — no logic changes. backend/db_qa/new_intent_classifier.py
previously imported these as private (underscore-prefixed) helpers directly
from intent_classifier.py, coupling the new classifier to the old module's
internals even though the helpers themselves are self-contained (pure regex
functions with no dependency on anything else in either classifier). Both
classifiers now import from here instead.
"""
from __future__ import annotations

import re

# ── constants ────────────────────────────────────────────────────────────────

# Permission action keywords → attribute name in XML_RoleAccess.xml
ACTION_MAP = {
    "new": "HasNew", "create": "HasNew", "add": "HasNew",
    # "upload" has no dedicated RoleAccess flag of its own — the schema
    # only tracks HasNew/HasEdit/HasView/HasApprove — so it's treated as
    # a creation action (closest fit), same as "add"/"new".
    "upload": "HasNew",
    "edit": "HasEdit", "update": "HasEdit", "modify": "HasEdit",
    "view": "HasView", "see": "HasView", "read": "HasView",
    "approve": "HasApprove", "approval": "HasApprove",
    # "generate"/"disable" resolved ONLY via the LLM normalizer before
    # (llm_service.normalize_action_word, whose own docstring uses
    # "generate" -> "create" as its example). That call costs a real
    # round trip -- measured at 19-26s here, since it retries twice --
    # and returns nothing at all when the Ollama proxy is unreachable,
    # so the user waited ~26s to be told the request wasn't understood.
    # Both verbs map unambiguously, so resolve them deterministically and
    # leave the LLM for genuinely ambiguous verbs ("run", "manage",
    # "perform", "delete" -- no HasExecute/HasDelete flag exists).
    "generate": "HasNew",
    "disable": "HasEdit",
}

# Period keywords → PeriodName in XML_Period.xml  (lower → canonical).
# Order matters: _extract_period() below returns on the FIRST alias whose
# keyword appears anywhere in the text, so a multi-word/prefix form that
# could also satisfy a LATER, more generic key must be listed first —
# e.g. "semi annual"/"semi-annual" must precede "annual"/"yearly"/"year",
# since "semi annual" contains the standalone word "annual" and would
# otherwise be wrongly resolved to Yearly instead of HalfYearly.
PERIOD_ALIASES: dict[str, str] = {
    "daily": "Daily", "day": "Daily", "every day": "Daily",
    "fortnightly": "Fortnightly", "biweekly": "Fortnightly", "bi-weekly": "Fortnightly",
    "every fortnight": "Fortnightly", "every two weeks": "Fortnightly",
    "weekly": "Weekly", "week": "Weekly", "every week": "Weekly",
    "monthly": "Monthly", "month": "Monthly", "every month": "Monthly",
    "quarterly": "Quarterly", "quarter": "Quarterly", "every quarter": "Quarterly",
    "semi annual": "HalfYearly", "semi-annual": "HalfYearly", "semiannual": "HalfYearly",
    "semi annually": "HalfYearly", "semi-annually": "HalfYearly",
    "half yearly": "HalfYearly", "half-yearly": "HalfYearly", "halfyearly": "HalfYearly",
    "half": "HalfYearly", "every half year": "HalfYearly", "twice a year": "HalfYearly",
    "yearly": "Yearly", "annually": "Yearly", "annual": "Yearly", "year": "Yearly",
    "every year": "Yearly",
    "bi-monthly": "BiMonthly", "bimonthly": "BiMonthly",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _extract_quoted_or_bracketed(text: str) -> str | None:
    """Return first quoted string or [bracketed] term in *text*."""
    m = re.search(r'"([^"]+)"', text)
    if m:
        return m.group(1).strip()
    m = re.search(r"\[([^\]]+)\]", text)
    if m:
        return m.group(1).strip()
    return None


def _extract_after_kw(text: str, *keywords: str) -> str | None:
    """Return the word(s) following the first matching keyword.

    The captured character class includes parentheses — many real return
    names in this dataset are parenthesized (e.g. "CIMS_RAQ(Annually)",
    "CIMS_RAQ(Monthly)"). Without them, a name containing "(" couldn't
    reach the terminator lookahead at all (that character isn't in the
    class), so the WHOLE match failed rather than just truncating the
    name — e.g. "return CIMS_RAQ(Annually)?" extracted nothing, silently
    falling through to "no target_return" instead of resolving or erroring
    on the specific return.
    """
    for kw in keywords:
        m = re.search(
            rf"\b{re.escape(kw)}\b\s+(?:called\s+|named\s+)?([A-Za-z0-9_.\-\s()]{{1,60}}?)(?:\?|$|\sis\b|\shas\b|\shave\b|\snot\b|\sand\b|\saccess\b|\ssubmit\w*\b|\sacross\b|\sfor\s+(?:the\s+)?(?:this|next|current)\b|\sthis\b|\snext\b|\suse\b|\sCIMS[\s-]?enabled\b)",
            text,
            re.IGNORECASE,
        )
        if m:
            candidate = m.group(1).strip()
            # A query with no trailing "?" (real users often omit it) and no
            # "is"/"has"/"and" terminator falls through to the "$" end-of-
            # string branch, swallowing generic trailing filler into the
            # name — e.g. "is there a role called Tester in the system"
            # (no "?") extracted "Tester in the system" instead of "Tester",
            # producing a false "role not found" against a role that
            # genuinely exists (self-test: doc/INTENT_GAP_ANALYSIS.md).
            # Strip this well-known, never-part-of-a-real-entity-name
            # trailing phrase rather than loosening the shared terminator
            # set itself, which many other intents' extraction also relies on.
            candidate = re.sub(
                r"\s+in\s+(the\s+)?(system|application|app)\s*$", "", candidate,
                flags=re.IGNORECASE,
            )
            return candidate.strip()
    return None


def _extract_period(text: str) -> str | None:
    for kw, canonical in PERIOD_ALIASES.items():
        if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
            return canonical
    return None


def _extract_action(text: str) -> str | None:
    for kw, attr in ACTION_MAP.items():
        if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
            return attr
    return None


def _self_ref(text: str) -> bool:
    """True if the question references the current user (me/my/I/myself).

    "give me"/"tell me"/"show me"/"help me"/"let me" are polite request
    fillers, not a self-reference — "give me the name of role ID 101" is
    asking about role 101, not "my own" role, but bare "me" alone would
    otherwise match. Stripped before the check so they can never trigger a
    false positive; any OTHER genuine self-reference elsewhere in the same
    sentence ("give me my role ID") still matches normally.
    """
    text = re.sub(r"\b(?:give|tell|show|help|let)\s+me\b", "", text, flags=re.IGNORECASE)
    # "I need to know ...", "I'd like to see ..." are the same kind of
    # polite request framing as "show me ..." — the "I" belongs to the ASK,
    # not to the thing being asked about. Left in, they silently narrowed
    # catalogue questions to the caller's own department: "I need to know
    # which Non-XBRL returns have no due days configured" answered 19 while
    # the identical "Can you show me which..." answered 70.
    text = re.sub(
        r"\bi\s*(?:'d|\s+would)?\s*(?:need|want|wish|like|would\s+like)\s+to\s+"
        r"(?:know|see|get|find\s+out|check|understand)\b",
        "", text, flags=re.IGNORECASE,
    )
    return bool(re.search(r"\b(my|me|i|myself|mine|i am|i've|i have)\b", text, re.IGNORECASE))
