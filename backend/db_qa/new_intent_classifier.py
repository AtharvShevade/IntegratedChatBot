"""Regex classifier for the new ~48-intent taxonomy (backend.db_qa.intents.
taxonomy.Intent). Kept as a SEPARATE module from intent_classifier.py
(the legacy db_* rule set) rather than interleaved into it — this keeps the
already-large legacy rule set untouched (486 lines, ~90 rules) while giving
the new taxonomy its own focused home. Both classifiers run independently;
db_qa_router.check_new_taxonomy_intent() is tried first, and only falls
back to the legacy check_db_qa_intent() if nothing here matches.

Two rule mechanisms coexist:
  - _KeywordRule (USER/DEPARTMENT/ROLE/ROLE_ACCESS only): word-order- and
    filler-independent — a rule matches if every required keyword GROUP has
    at least one alternative present anywhere in the question, regardless
    of order or intervening words. This is what makes "who works in
    Finance", "Finance department users", "list Finance users" all resolve
    identically without enumerating each phrasing.
  - _mk/_NEW_RULES (everything else): literal ordered-phrase regexes, as
    before — representative coverage, not exhaustive. Left untouched;
    accuracy hardening for these categories is a separate follow-up.

Rules are tried in this order: _KEYWORD_RULES first (most specific member
wins — see _match_keyword_rules), then _NEW_RULES (first literal match
wins, as before).
"""
from __future__ import annotations

import re

from rapidfuzz import process as _fuzz

from backend.db_qa.intent_classifier import (
    _extract_action, _extract_after_kw, _extract_period,
    _extract_quoted_or_bracketed, _self_ref, ACTION_MAP, PERIOD_ALIASES,
)
from backend.db_qa.intents.taxonomy import Intent

_USER_FIELD_PATTERNS: dict[str, str] = {
    "email": r"\bemail\b",
    "mobile": r"\b(mobile|phone|contact)\s*(number)?\b",
    "login_id": r"\b(login\s*id|username|user\s*name)\b",
    "user_code": r"\buser\s*code\b",
    "created_date": r"\b(created|creation\s+date)\b",
    "created_by": r"\bwho\s+creat\w*\b",
    "last_login": r"\blast\s+(log|login|logged|signed)\b",
    "failed_login_count": r"\bfailed\s+(logins?|log\s*in\s*(attempts?|count)?|password)\b",
    "status": r"\b(active|status|enabled|disabled)\b",
    "password_date": r"\bpassword\s+(update|change|reset)\b",
}


# Sentence-initial question/list words that can precede/follow a noun word
# ("department", "users", "role") but are never themselves an entity name
# (e.g. "What department am I in" — "What" must never be extracted as the
# department name; "Which users belong to department Finance" — "Which"
# must be skipped so "Finance" wins instead).
_NOT_AN_ENTITY_NAME = {
    "which", "who", "what", "show", "list", "give", "display",
    "all", "the", "does", "is", "are",
}


# ── keyword-group matching engine (word-order independent) ────────────────

def _kw(*alternatives: str) -> re.Pattern:
    """One keyword GROUP: matches if ANY alternative is present, as a whole
    word/phrase, anywhere in the text. Alternatives are plain regex
    fragments (already tolerant of singular/plural/optional-article where
    written), not full sentences."""
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)


# "non-xbrl" / "non xbrl" / "nonxbrl" — users type this with a hyphen, a
# space, or nothing at all, and case varies too (_kw/_XBRL_TYPE_RE already
# apply IGNORECASE). Every pattern that needs to recognise the non-XBRL
# variant should embed this fragment rather than hardcoding "non-xbrl", so
# a fix to the separator tolerance here doesn't need to be repeated at
# each call site.
_NON_XBRL = r"non[\s-]?xbrl"


class _KeywordRule:
    """Matches when every group in `all_of` has >=1 hit, AND (if `any_of` is
    non-empty) at least one group in `any_of` also has a hit. Group order in
    the question is irrelevant — this is what gives "who works in Finance"
    vs "Finance department users" vs "list users in Finance" the same match.

    `priority` (default 0) is added on top of the satisfied-group count to
    break ties when multiple rules match the same question. Structural/
    proper-noun rules (e.g. USERS_BY_DEPARTMENT's "Finance users" pattern)
    set priority=10 so they always outrank a generic keyword-count rule
    (e.g. USER_LIST's user-noun + list-verb) even when the generic rule
    happens to satisfy more groups — group count alone isn't a reliable
    specificity signal once structural (name-anchored) rules are involved.
    """

    __slots__ = ("intent", "target_types", "all_of", "any_of", "excludes", "priority")

    def __init__(self, intent: Intent, target_types: tuple[str, ...],
                 all_of: tuple[re.Pattern, ...], any_of: tuple[re.Pattern, ...] = (),
                 excludes: tuple[re.Pattern, ...] = (), priority: int = 0):
        self.intent = intent
        self.target_types = target_types
        self.all_of = all_of
        self.any_of = any_of
        self.excludes = excludes
        self.priority = priority

    def match_score(self, q: str) -> int | None:
        if any(pat.search(q) for pat in self.excludes):
            return None
        if not all(pat.search(q) for pat in self.all_of):
            return None
        if self.any_of and not any(pat.search(q) for pat in self.any_of):
            return None
        return self.priority * 100 + len(self.all_of) + (1 if self.any_of else 0)


# Shared keyword-group fragments reused across USER/DEPARTMENT/ROLE rules.
_G_QUESTION = _kw(r"what", r"which", r"who", r"tell me", r"show", r"give me",
                  r"can you tell me", r"list", r"display")
_G_USER_NOUN = _kw(r"users?", r"accounts?", r"people", r"members?")
_G_DEPT_NOUN = _kw(r"departments?", r"depts?")
_G_ROLE_NOUN = _kw(r"roles?")
_G_LIST_VERB = _kw(r"list", r"show", r"display", r"give me", r"who are", r"which are", r"who")
_G_HOW_MANY = _kw(r"how many", r"count of", r"total number of", r"number of")
_G_ACTIVE = _kw(r"active", r"enabled")
_G_INACTIVE = _kw(r"inactive", r"disabled", r"deactivated")
_G_ALL = _kw(r"all", r"every", r"complete list of")


def _self_group_hit(q: str) -> bool:
    return _self_ref(q)


class _UsersByDeptStructuralPattern:
    """Duck-typed like a compiled re.Pattern (only .search() is called by
    _KeywordRule.match_score) — matches USERS_BY_DEPARTMENT's structural
    phrasings ("Finance users", "users in Finance", "who works/belongs in/
    to Finance", "Finance department") while excluding cases where the
    capitalized word immediately involved is actually a sentence-initial
    question/list word (What/Which/Who/Show/List/Give/Display), which
    Python's re can't express as pure regex (no variable-width lookbehind).
    """

    _TRIGGER = re.compile(
        r"(?:(?P<verb>[Ww]ho\s+(?:works?|belongs?)\s+(?:in|to))\s+(?P<name1>[A-Z]\w*))"
        r"|(?:[Uu]sers?\s+in\s+(?P<name2>[A-Z]\w*))"
        r"|(?:[Mm]embers?\s+of\s+(?P<name3>[A-Z]\w*))"
        r"|(?:(?P<name4>[A-Z]\w*)\s+users?\b)"
        r"|(?:(?P<name5>[A-Z]\w*)\s+department\s+users?)"
        r"|(?:(?P<name6>[A-Z]\w*)\s+department\b)"
    )
    def search(self, q: str):
        for m in self._TRIGGER.finditer(q):
            name = next((v for v in m.groupdict().values() if v), None)
            if name and name.lower() not in _NOT_AN_ENTITY_NAME:
                return m
        return None


# ── USER keyword rules ──────────────────────────────────────────────────

_KEYWORD_RULES: list[_KeywordRule] = [

    # user_field: a field-word + self-reference (any order, any filler).
    # "status"/"created"/"password" alone are too generic (they also occur
    # in submission/return questions) — for those, require an explicit
    # account/user/login qualifier nearby; the unambiguous field words
    # (email/mobile/phone/login id/username/user code/failed login) need
    # no extra qualifier since they aren't used elsewhere in this taxonomy.
    _KeywordRule(
        Intent.USER_FIELD, ("self", "other_user"),
        all_of=(_kw(r"email", r"mobile", r"phone", r"contact", r"login\s*id",
                     r"user\s*name", r"username", r"user\s*code",
                     r"(account|profile|user)\s+status", r"is\s+my\s+account",
                     r"(account|user)\s+password", r"password\s+(update|change|reset)",
                     r"last\s*log\w*", r"account\s+creat\w*", r"who\s+creat\w*\s+my",
                     r"failed\s*log\w*"),),
        excludes=(_kw(r"submission", r"instance", r"return\b", r"report\b"),),
    ),

    # user_profile: profile/account/details + self-ref, or "who am I"
    _KeywordRule(
        Intent.USER_PROFILE, ("self", "other_user"),
        all_of=(_kw(r"profile", r"account\s*details?", r"my\s*details?",
                     r"who\s+am\s+i", r"details?\s+of\s+user"),),
    ),

    # users_by_department: either (a) the literal word "department"/"dept"
    # is present alongside a user-noun, or (b) a structural "who
    # works/belongs in <Name>" / "<Name> department" / "users in <Name>"
    # pattern names a department WITHOUT the word "department" appearing at
    # all (the classifier can't know "Finance" is a department name from
    # regex alone — that's a job for the real department list at lookup
    # time — so it matches on structure: user-noun/who + in/of/belonging-to
    # + a following capitalized word, or a capitalized word immediately
    # preceding "users"/"department").
    _KeywordRule(
        Intent.USERS_BY_DEPARTMENT, ("department",),
        all_of=(_G_USER_NOUN, _G_DEPT_NOUN),
        any_of=(_kw(r"in", r"belong\w*", r"work\w*", r"member\w*", r"of", r"from"),),
    ),
    _KeywordRule(
        Intent.USERS_BY_DEPARTMENT, ("department",),
        # Case-sensitive by design: the trigger phrase is matched
        # case-insensitively via [Ww]/[Uu]/[Mm] alternation on its own
        # first letter (covers sentence-initial capitalization), but the
        # NAME that follows must be capitalized — that's what distinguishes
        # a real proper-noun department name from an ordinary lowercase
        # filler word like "the"/"is". Question/list words that are
        # themselves sentence-initial-capitalized (What/Which/Who/Show/
        # List/...) are excluded via _users_by_department_structural_match
        # (a Python-level check — Python's re has no variable-width
        # lookbehind, so this can't be done as one regex).
        all_of=(_UsersByDeptStructuralPattern(),),
        priority=1,
    ),

    # users_by_role: role-noun + "assigned"/"with"/"have" + user-noun
    _KeywordRule(
        Intent.USERS_BY_ROLE, ("role",),
        all_of=(_G_USER_NOUN, _G_ROLE_NOUN),
        any_of=(_kw(r"assigned", r"with", r"have", r"has", r"holding"),),
    ),

    # user_list: user-noun + (list-verb OR how-many OR active/inactive/
    # never-logged-in/failed-login/duplicate-email) — deliberately the
    # lowest-specificity USER rule so more specific ones above win first
    # via match_score when both match.
    _KeywordRule(
        Intent.USER_LIST, ("system_wide",),
        all_of=(_G_USER_NOUN,),
        any_of=(_G_LIST_VERB, _G_HOW_MANY, _G_ACTIVE, _G_INACTIVE, _G_ALL,
                 _kw(r"never\s+logged\s*in", r"never\s+log\w*", r"duplicate\s+email",
                     r"failed\s+log\w*", r"stale\s+password", r"not\s+updated\s+password")),
        excludes=(_kw(r"\bmy\b"),),  # avoid stealing "my ... users" self-phrasings
    ),

    # ── DEPARTMENT ───────────────────────────────────────────────────────

    _KeywordRule(
        Intent.DEPARTMENT_HAS_RETURN, ("self", "department"),
        all_of=(_G_DEPT_NOUN, _kw(r"access", r"have\s+access")),
        any_of=(_kw(r"return", r"form", r"report"),),
    ),

    _KeywordRule(
        Intent.DEPARTMENTS_WITH_RETURN_ACCESS, ("return",),
        all_of=(_G_DEPT_NOUN, _kw(r"access", r"submit\w*")),
        any_of=(_kw(r"which", r"how many"),),
        excludes=(_kw(r"\bmy\b"),),
    ),

    _KeywordRule(
        Intent.DEPARTMENT_RETURNS, ("self", "department"),
        all_of=(_G_DEPT_NOUN, _kw(r"returns?", r"forms?", r"reports?")),
        any_of=(_kw(r"department.{0,30}access", r"access.{0,30}(return|form|report)",
                     rf"which\s+(xbrl|{_NON_XBRL})?\s*returns?", r"does\s+.{0,20}department",
                     r"xbrl\s+returns?", rf"{_NON_XBRL}\s+returns?"),),
        excludes=(_kw(r"summary\s+of\s+my\s+access", r"full\s+summary", r"full\s+profile"),),
    ),

    _KeywordRule(
        Intent.DEPARTMENT_PROFILE, ("self", "department"),
        all_of=(_G_DEPT_NOUN,),
        any_of=(_kw(r"email", r"\bid\b", r"identifier", r"what\s+department\s+am\s+i",
                     r"which\s+department"),),
    ),

    _KeywordRule(
        Intent.DEPARTMENT_LIST, ("system_wide",),
        all_of=(_G_DEPT_NOUN,),
        any_of=(_G_LIST_VERB, _G_HOW_MANY, _G_ACTIVE, _G_INACTIVE, _G_ALL,
                 _kw(r"most", r"fewest", r"least", r"no\s+returns")),
        excludes=(_kw(r"\bmy\b"),),
    ),

    # ── ROLE ─────────────────────────────────────────────────────────────

    _KeywordRule(
        Intent.ROLE_PEER_COUNT, ("self",),
        all_of=(_kw(r"how\s+many", r"other"), _kw(r"same\s+role", r"share.*role")),
    ),

    _KeywordRule(
        Intent.ROLE_PROFILE, ("self", "role"),
        all_of=(_G_ROLE_NOUN,),
        any_of=(_kw(r"my", r"i\s+have", r"i\s+am\s+assigned", r"am\s+i\s+assigned",
                     r"do\s+i\s+have", r"assigned\s+to\s+me"),),
        # "is there a role called X"/"does role X exist" are existence
        # checks -> ROLE_LIST(query_type=exists), not ROLE_PROFILE; excluded
        # here so that rule (lower in this list, same all_of group) wins.
        excludes=(_kw(r"is\s+there\s+a\s+role", r"\bexist\w*\b"),),
    ),

    _KeywordRule(
        Intent.ROLE_USERS, ("role",),
        all_of=(_G_ROLE_NOUN, _G_USER_NOUN),
        any_of=(_kw(r"assigned", r"have", r"has", r"with", r"how\s+many"),),
    ),

    _KeywordRule(
        Intent.ROLE_LIST, ("system_wide",),
        all_of=(_G_ROLE_NOUN,),
        any_of=(_G_LIST_VERB, _G_HOW_MANY, _G_ACTIVE, _G_INACTIVE, _G_ALL,
                 _kw(r"most\s+users", r"largest", r"biggest",
                     r"is\s+there\s+a\s+role", r"exist\w*")),
        excludes=(_kw(r"\bmy\b"),),
    ),

    # ── ROLE_ACCESS ──────────────────────────────────────────────────────

    _KeywordRule(
        Intent.ROLE_PERMISSION_DIFF, ("role",),
        all_of=(_kw(r"difference", r"differ\w*", r"compare\w*", r"vs\.?", r"versus"),
                 _kw(r"permission\w*", r"access", r"role\w*")),
    ),

    _KeywordRule(
        Intent.ROLES_WITH_PERMISSION, ("system_wide",),
        all_of=(_G_ROLE_NOUN, _kw(r"create", r"edit", r"view", r"approve", r"access",
                                     r"full\s+access", r"no\s+edit", r"no\s+create")),
        any_of=(_kw(r"which", r"what", r"can", r"have"),),
        excludes=(_kw(r"\bmy\b", r"\bi\b"),),
    ),

    _KeywordRule(
        Intent.ROLE_MODULE_ACCESS, ("role", "system_wide"),
        all_of=(_kw(r"module\w*", r"sdmx", r"cross-?validation", r"nxquerybuilder",
                     r"balance\s+sheet", r"data\s+preparation", r"audit\s+log",
                     r"provider\w*", rf"{_NON_XBRL}\s+upload", r"maker-?checker"),),
        any_of=(_kw(r"access\w*", r"role\w*"),),
        excludes=(_kw(r"\bmy\b", r"\bcan\s+i\b"),),
    ),

    _KeywordRule(
        Intent.PERMISSION_CHECK, ("self", "role"),
        all_of=(_kw(r"can\s+i", r"can\s+(the\s+)?role", r"am\s+i\s+allowed",
                     r"do\s+i\s+have\s+(the\s+)?(permission|right|access)\s+to"),
                 _kw(r"create", r"edit", r"update", r"modify", r"view", r"see",
                     r"approve", r"add", r"upload", r"access", r"disable",
                     r"delete", r"run", r"generate", r"do", r"manage", r"perform")),
    ),

    _KeywordRule(
        Intent.PERMISSION_PROFILE, ("self", "role"),
        all_of=(_kw(r"permission\w*", r"access\w*", r"modules?\s+am\s+i\s+allowed",
                     r"not\s+have\s+access"),),
        any_of=(_kw(r"my", r"i\s+have", r"do\s+i\s+have", r"what\s+can\s+i",
                     r"role\w*"),),
        excludes=(_kw(r"\bcan\s+i\b"),),  # PERMISSION_CHECK owns "can I ..."
    ),
]


# Phrasings that belong to CROSS_ENTITY intents (outside the 4 hardened
# categories) and legitimately mention role/department/return together —
# excluded globally from keyword-rule matching so a broad any_of clause in
# one of the 4 categories can't accidentally steal them. USER_ACCESS_SUMMARY
# and CROSS_ENTITY_QUERY's own literal patterns (in _NEW_RULES) still match
# normally since keyword rules simply decline to match here.
_GLOBAL_KEYWORD_EXCLUDE = _kw(
    r"full\s+(profile\s+)?summary\s+of\s+(my\s+)?access",
    r"full\s+profile\s+summary\s+of\s+user",
)


def _match_keyword_rules(q: str) -> tuple[Intent, tuple[str, ...]] | None:
    if _GLOBAL_KEYWORD_EXCLUDE.search(q):
        return None
    best: tuple[int, _KeywordRule] | None = None
    for rule in _KEYWORD_RULES:
        score = rule.match_score(q)
        if score is None:
            continue
        if best is None or score > best[0]:
            best = (score, rule)
    if best is None:
        return None
    return best[1].intent, best[1].target_types


def _mk(intent: Intent, target_types: tuple[str, ...], *patterns: str):
    return (intent, target_types, [re.compile(p, re.IGNORECASE) for p in patterns])


# Literal-pattern rules for everything OUTSIDE USER/DEPARTMENT/ROLE/
# ROLE_ACCESS (those 4 categories now live entirely in _KEYWORD_RULES
# above). Left as representative-coverage patterns per the original
# design — hardening these is a separate follow-up task.
_NEW_RULES: list[tuple[Intent, tuple[str, ...], list[re.Pattern]]] = [

    # ── USER_LEVEL ───────────────────────────────────────────────────────
    _mk(Intent.USER_LEVEL_SELF, ("self",),
        r"\bmy\s+(user\s+)?level\b", r"\bwhat\s+level\s+am\s+i\b"),
    _mk(Intent.USER_LEVEL_LIST, ("system_wide",),
        r"\buser\s+levels?\b.*(defin|exist|list|active)",
        r"\busers?\s+at\s+level\s+l\d\b"),

    # ── BANK / SEGMENT / NOTIFICATION (specific, check early) ───────────────
    _mk(Intent.BANK_INFO, ("self",),
        r"\bbank\b.*(name|code|type|crr|ifsc|detail)", r"\bwhich\s+bank\b"),
    _mk(Intent.SEGMENT_INFO, ("self",),
        r"\bsegment\s+(type|list|defin)", r"\bwhat\s+segments?\s+are\b"),
    _mk(Intent.NOTIFICATION_QUERY, ("self", "return", "system_wide"),
        r"\bnotifications?\b", r"\bsms\s+(reminder|enabled)\b", r"\badvance\s+notifications?\b"),

    # ── XBRL_RETURNS / NON_XBRL_RETURNS / PERIOD / DEPT_RETURN_MAPPING ──
    _mk(Intent.RETURNS_BY_FREQUENCY, ("self", "system_wide"),
        r"\bwhich\s+returns?\s+are\s+filed\s+(on\s+a\s+)?(monthly|quarterly|annual|yearly)\b"),
    # RETURN_FIELD is checked BEFORE PERIOD_LOOKUP/PERIOD_LIST so a
    # return-scoped question like "what is the reporting frequency of
    # CIMS_ROR" (asking about ONE return) doesn't fall through to the
    # system-wide period intents (which dump every configured period,
    # ignoring the return name entirely).
    _mk(Intent.RETURN_FIELD, ("return",),
        r"\breturn\s+id\s+(for|of)\b", r"\binternal\s+form\s+id\s+(for|of)\b",
        r"\b(reporting\s+)?(period|frequency)\s+(for|of)\s+(the\s+)?(return|form|report)?\s*\S",
        r"\bwhat\s+(period|frequency)\s+is\b.{0,40}\breturn\b",
        r"\bhow\s+often\s+is\b.{0,40}\bfiled\b"),
    _mk(Intent.PERIOD_LOOKUP, ("system_wide",),
        r"\bperiod\s+(name|id)\s+for\b", r"\bebr\s+frequency\s+code\b",
        r"\badvance\s+notification\s+days?\s+for\b"),
    _mk(Intent.PERIOD_LIST, ("system_wide",),
        r"\ball\s+(the\s+)?(reporting\s+)?periods?\b", r"\breporting\s+frequenc\w*\b",
        r"\bhow\s+many\s+(reporting\s+)?frequenc\w*\b", r"\bperiods?/frequenc\w*\s+(defined|are)\b"),
    _mk(Intent.RETURNS_SUBMITTABLE_BY_DEPT, ("self", "department", "return"),
        r"\bwhich\s+xbrl\s+returns?\s+can\s+i\s+submit\b", r"\bwhich\s+departments?\s+can\s+submit\b"),
    _mk(Intent.RETURN_VALIDATION_CONFIG, ("self", "system_wide"),
        r"\b(formula|schema|rbi)\s+validation\b", r"\bcross-report\s+validation\b",
        r"\bbusiness\s+rules?\s+for\b", r"\bvalidation\s+rules?\s+(apply|for)\b"),
    # REPORTS_FILED_IN_RANGE / REPORTS_UPCOMING_IN_RANGE are checked BEFORE
    # NEXT_REPORTING_DATE: both mention "due"/"reporting date" too, but a
    # date-range span is the more specific signal and must win over
    # NEXT_REPORTING_DATE's broader "when is X due" patterns.
    #
    # "file[ds]?"/"filing[s]?"/"submit(ted|s)?"/"generat(e|ed)"/"creat(e|ed)"/
    # "produc(e|ed)" are all treated as synonyms for "filed" here — users
    # describe an already-submitted report as filed/filing/submitted/
    # generated/created interchangeably — and each tolerates common
    # verb-form slips ("files"/"file" instead of "filed") without
    # loosening the match enough to catch unrelated words.
    #
    # The range connector itself is also phrased multiple ways:
    # "between X and Y", "from X to Y", "for the period X to Y" — the
    # \s+\S in the middle covers the date span without re-deriving the
    # exact date grammar here (that's _DATE_RANGE_RE's job); this is a
    # cheap 0-40-char gap, not a real date parse.
    _mk(Intent.REPORTS_FILED_IN_RANGE, ("self", "department", "system_wide"),
        r"\b(file[ds]?|filing[s]?|submit(?:ted|s)?|generat(?:ed?|es)|creat(?:ed?|es)|produc(?:ed?|es))"
        r"(?:\s+\S.{0,30})?\s+(?:between|from|during|for\s+the\s+period(?:\s+of)?)\b",
        r"\breports?\s+(file[ds]?|filing[s]?|generat(?:ed?|es)|creat(?:ed?|es)|produc(?:ed?|es))"
        r"(?:\s+\S.{0,30})?\s+(?:between|from|during|for\s+the\s+period(?:\s+of)?)\b",
        r"\breturns?\s+(file[ds]?|filing[s]?|generat(?:ed?|es)|creat(?:ed?|es)|produc(?:ed?|es))"
        r"(?:\s+\S.{0,30})?\s+(?:between|from|during|for\s+the\s+period(?:\s+of)?)\b",
        r"\bshow\s+me\s+all\b.{0,40}\b(file[ds]?|filing[s]?|generat(?:ed?|es)|creat(?:ed?|es)|produc(?:ed?|es))"
        r"(?:\s+\S.{0,30})?\s+(?:between|from|during|for\s+the\s+period(?:\s+of)?)\b"),
    _mk(Intent.REPORTS_UPCOMING_IN_RANGE, ("self", "department", "system_wide"),
        r"\b(coming\s+up|upcoming|due)(?:\s+\S.{0,30})?\s+(?:between|from|during|for\s+the\s+period(?:\s+of)?)\b",
        r"\bwhich\s+.{0,40}\bare\s+due(?:\s+\S.{0,30})?\s+(?:between|from)\b",
        r"\bwhat\s+.{0,40}\b(coming\s+up|are\s+due)(?:\s+\S.{0,30})?\s+(?:between|from)\b",
        r"\bupcoming\s+(returns?|reports?|forms?)\b", r"\bwhat\s+.{0,40}\bupcoming\s+next\s+month\b"),
    _mk(Intent.NEXT_REPORTING_DATE, ("return",),
        r"\bnext\s+report(ing)?\s+date\b", r"\bnext\s+due\s+date\b",
        r"\bwhen\s+is\b.{0,40}\bdue\b", r"\bwhen\s+(is|does)\b.{0,40}\bnext\s+(report|reporting|submission|due)\b",
        r"\bwhen\s+(should|do)\s+i\s+(submit|file|report)\b", r"\bdue\s+date\s+for\b",
        r"\bnext\s+period[\s-]?end\b"),
    _mk(Intent.RETURN_PROFILE, ("return",),
        r"\btaxonomy\s+(version|does)\b", r"\bxsd\s+path\b",
        r"\bdue\s+days?\s+.*submission\s+of\s+return\b", r"\balternate\s+name\s+for\s+return\b"),
    _mk(Intent.RETURN_LIST, ("self", "system_wide"),
        r"\ball\s+(the\s+)?xbrl\s+returns?\b", r"\bhow\s+many\s+xbrl\s+returns?\b",
        r"\bwhich\s+xbrl\s+returns?\s+(are|is)\b", r"\bcims-enabled\s+returns?\b"),
    _mk(Intent.NONXBRL_RETURN_PROFILE, ("self", "return"),
        rf"\bbase\s+(file\s+)?template\s+for\s+{_NON_XBRL}\b", r"\bjob\s+processing\s+id\b"),
    _mk(Intent.NONXBRL_RETURN_LIST, ("self", "department", "system_wide"),
        rf"\b{_NON_XBRL}\s+returns?\b", rf"\bhow\s+many\s+{_NON_XBRL}\b"),
    _mk(Intent.DEPT_FULL_RETURN_LIST, ("department",),
        r"\bcomplete\s+list\s+of\s+returns?\s+for\s+department\b"),
    _mk(Intent.MY_RETURN_ACCESS, ("self",),
        r"\bwhich\s+returns?\s+does\s+my\s+department\s+have\s+access\b",
        r"\bcomplete\s+list\s+of\s+returns?\s+i\s+can\s+work\s+with\b",
        r"\bhow\s+many\s+returns?\s+can\s+i\s+access\b"),
    _mk(Intent.DEPT_RETURN_ACCESS_MATRIX, ("system_wide",),
        r"\breturn\s+.*accessible\s+by\s+the\s+(maximum|most)\b",
        r"\bdepartment\s+has\s+access\s+to\s+the\s+most\s+returns?\b"),

    # ── INSTANCE_LOG ─────────────────────────────────────────────────────
    _mk(Intent.MY_SUBMISSION_HISTORY, ("self",),
        r"\bwhich\s+returns?\s+have\s+i\s+submitted\b", r"\bhave\s+i\s+ever\s+submitted\b"),
    _mk(Intent.SUBMISSIONS_FOR_RETURN, ("return",),
        r"\bwho\s+submitted\s+returns?\b", r"\bwho\s+submitted\s+.*\breturns?\b"),
    _mk(Intent.SUBMISSION_DETAIL, ("self", "other_user"),
        r"\binstance\s+document\s+path\s+for\b", r"\bcims\s+upload\s+status\s+for\s+my\s+submission\b",
        r"\brejection\s+reason\b"),
    _mk(Intent.SUBMISSION_STATUS, ("self", "other_user"),
        r"\bstatus\s+of\s+(my\s+)?submission\b", r"\bwas\s+my\s+submission\b.*\brejected\b"),
    _mk(Intent.SUBMISSION_LIST, ("self", "other_user", "return", "system_wide"),
        r"\bwhich\s+(of\s+my\s+)?submissions?\s+are\s+pending\b",
        r"\bsubmissions?\s+.*(approved|audited|rejected|cims)\b",
        r"\ball\s+recent\s+submissions?\s+made\s+for\s+return\b"),

    # ── MENU_OPTIONS ─────────────────────────────────────────────────────
    _mk(Intent.MODULE_CHILDREN, ("system_wide",),
        r"\bchild\s+modules?\s+under\b"),
    _mk(Intent.MODULE_DETAIL, ("self", "system_wide"),
        r"\bmenu\s+rank\b", r"\bresource\s+label\s+for\s+module\b", r"\bicon\s+for\s+module\b",
        r"\bparent\s+module\s+of\b", r"\bis\s+the\s+.*\s+module\s+available\s+to\s+me\b"),
    _mk(Intent.MENU_LIST, ("self", "system_wide"),
        r"\bmodules?\s+am\s+i\s+able\s+to\s+see\b", r"\btop-level\s+menu\b",
        r"\bwhat\s+modules?\s+are\s+available\b"),

    # ── AUDIT_SECURITY ───────────────────────────────────────────────────
    _mk(Intent.LOG_QUERY, ("self", "other_user", "return", "system_wide"),
        r"\bfile\s+uploads?\s+fail\w*\b", r"\bsdmx\s+(generation\s+)?logs?\s+for\b",
        r"\bcross-validation\s+errors?\s+(logged\s+)?for\b"),
    _mk(Intent.SECURITY_EVENTS, ("self", "other_user", "system_wide"),
        r"\bpassword\s+(been\s+)?reset\b", r"\bpending\s+password\s+reset\b",
        r"\bexceeded\s+.*failed\s+login\b", r"\bdeactivated\s+and\s+when\b",
        r"\baccount\s+.*locked\b"),
    _mk(Intent.AUDIT_ENTITY_TRAIL, ("department", "return", "system_wide"),
        r"\baudit\s+trail\s+for\b", r"\bwho\s+last\s+modified\b", r"\bwho\s+last\s+approved\b"),
    _mk(Intent.AUDIT_HISTORY, ("self", "other_user"),
        r"\bwhat\s+changes\s+have\s+i\s+made\b", r"\bmy\s+activity\s+history\b",
        r"\bwhat\s+changes\s+were\s+made\s+by\s+user\b"),

    # ── CROSS_ENTITY ─────────────────────────────────────────────────────
    _mk(Intent.CROSS_ENTITY_QUERY, ("department", "role", "return", "system_wide"),
        r"\bwho\s+in\s+department\b.*\bapprove\b", r"\bboth\s+.*\s+role\s+and\s+belong\s+to\s+department\b",
        r"\bnot\s+logged\s+in\s+for\s+more\s+than\b", r"\bmost\s+recently\s+submitted\b",
        r"\bwho\s+has\s+approval\s+rights\b"),
    _mk(Intent.USER_ACCESS_SUMMARY, ("self", "other_user"),
        r"\bfull\s+(profile\s+)?summary\s+of\s+(my\s+)?access\b", r"\bwhat\s+can\s+i\s+do\s+based\s+on\s+my\s+role\b",
        r"\bfull\s+profile\s+summary\s+of\s+user\b"),
]


def classify_new(question: str) -> tuple[Intent | None, dict, str | None]:
    """Return (Intent, params, target_type) or (None, {}, None) if no new-
    taxonomy rule matches. Callers should fall back to the legacy
    intent_classifier.classify()/check_db_qa_intent() when this returns None.

    Keyword-group rules (USER/DEPARTMENT/ROLE/ROLE_ACCESS) are tried first
    since they're the accuracy-hardened categories; literal-pattern rules
    (everything else) are tried second, exactly as before.
    """
    q = question.strip()

    kw_match = _match_keyword_rules(q)
    if kw_match is not None:
        intent, target_types = kw_match
        target_type = _infer_target_type(q, target_types)
        target_type = _refine_range_target_type(intent, q, target_types, target_type)
        params = _extract_new_params(intent, q)
        params["target_type"] = target_type
        return intent, params, target_type

    for intent, target_types, patterns in _NEW_RULES:
        for pat in patterns:
            if pat.search(q):
                target_type = _infer_target_type(q, target_types)
                target_type = _refine_range_target_type(intent, q, target_types, target_type)
                params = _extract_new_params(intent, q)
                params["target_type"] = target_type
                return intent, params, target_type
    return None, {}, None


_SYSTEM_WIDE_RANGE_RE = re.compile(
    r"\b(system[\s-]?wide|across\s+all\s+departments?|all\s+departments?|every\s+department)\b",
    re.IGNORECASE,
)


def _refine_range_target_type(
    intent: Intent, q: str, accepted: tuple[str, ...], inferred: str,
) -> str:
    """Correct _infer_target_type's generic 2-way guess for
    REPORTS_FILED_IN_RANGE / REPORTS_UPCOMING_IN_RANGE, whose accepted set
    is ("self", "department", "system_wide") — three options, not the
    usual two _infer_target_type is designed for.

    _infer_target_type only ever returns "self" (self-referential
    phrasing like "show ME") or the first non-self accepted entry
    ("department", for ANY other phrasing) — it has no way to tell
    "department" and "system_wide" apart, and no way to recognise that a
    self-referential phrasing like "show me ... system-wide" is actually
    an explicit admin-scope request, not a self-service one. This
    function re-derives the correct scope directly from explicit signals
    in the question text, checked in this order regardless of what
    _infer_target_type guessed:

      1. Explicit "system-wide"/"across all departments" wording -> system_wide
      2. An explicit named department -> department
      3. Neither signal present -> self (never default to "department"
         with no department actually named — that would force an
         ordinary, non-admin-intended question through an admin-gated
         branch with nothing to resolve, always failing with "that
         department could not be found").
    """
    if intent not in (Intent.REPORTS_FILED_IN_RANGE, Intent.REPORTS_UPCOMING_IN_RANGE):
        return inferred

    if _SYSTEM_WIDE_RANGE_RE.search(q) and "system_wide" in accepted:
        return "system_wide"

    explicit_dept = _extract_named_entity_before_or_after(q, ("department", "dept"))
    if explicit_dept and "department" in accepted:
        return "department"

    return "self" if "self" in accepted else inferred


async def classify_new_with_semantic_tiers(question: str) -> tuple[Intent | None, dict, str | None, str]:
    """Full tiered intent classification: regex -> embedding similarity ->
    narrow LLM disambiguation -> no match.

    Returns (Intent, params, target_type, tier) — same shape as
    classify_new() plus a 4th "tier" field recording which stage produced
    the result ("regex", "embedding", "llm_disambiguation", "none"), so
    callers can log outcomes per-tier (see backend.utils.intent_log).

    Once an Intent is known (from any tier), params/target_type are built
    via the SAME _extract_new_params()/_infer_target_type() helpers the
    regex path already uses — entity extraction doesn't depend on how the
    intent was determined, only on the question text and the intent
    itself.
    """
    intent, params, target_type = classify_new(question)
    if intent is not None:
        return intent, params, target_type, "regex"

    # A bare word or short fragment (e.g. "cims", a partial report name
    # mid disambiguation flow) is never a genuine natural-language
    # question — embedding similarity against single-word/fragment input
    # is unreliable (a short token can score deceptively close to
    # unrelated exemplars), and an LLM asked to disambiguate a bare
    # fragment tends to force-pick a candidate rather than decline. Skip
    # the semantic tiers entirely below this length; such input should
    # fall through to whatever non-DB-QA flow the caller has (e.g. the
    # compare/status/generate disambiguation-reply handling in decide()).
    if len(question.split()) < 3:
        return None, {}, None, "none"

    from backend.db_qa.intents.embedding_index import classify_by_embedding
    from backend.db_qa.intents.taxonomy import INTENT_SPECS

    embedding_result = classify_by_embedding(question)
    tier = embedding_result["tier"]

    resolved_intent: Intent | None = None
    if tier == "embedding_confident":
        resolved_intent = embedding_result["intent"]
        tier = "embedding"
    elif tier == "embedding_ambiguous":
        from backend.services.llm_service import disambiguate_intent

        candidates = [
            (c_intent.value, INTENT_SPECS[c_intent].description)
            for c_intent, _score, _text in embedding_result["candidates"]
        ]
        chosen_value = await disambiguate_intent(question, candidates)
        if chosen_value is not None:
            resolved_intent = Intent(chosen_value)
        tier = "llm_disambiguation"
    else:
        tier = "none"

    if resolved_intent is None:
        return None, {}, None, tier

    spec = INTENT_SPECS[resolved_intent]
    resolved_target_type = _infer_target_type(question, spec.target_types)
    resolved_params = _extract_new_params(resolved_intent, question)
    resolved_params["target_type"] = resolved_target_type
    return resolved_intent, resolved_params, resolved_target_type, tier


def _infer_target_type(q: str, accepted: tuple[str, ...]) -> str:
    """Pick a target_type from *accepted* based on self-reference phrasing.

    If the question reads as self-referential ("my", "I") and "self" is an
    accepted type, use it. Otherwise fall back to the first non-self
    accepted type (the caller/access_control layer enforces admin rights
    for that type; if the caller isn't authorized, scope_query raises and
    the router returns a helpful denial rather than silently misrouting).
    """
    if not accepted:
        return "self"
    if _self_ref(q) and "self" in accepted:
        return "self"
    non_self = [t for t in accepted if t != "self"]
    return non_self[0] if non_self else accepted[0]


_STATUS_FUZZY_THRESHOLD = 82  # 0-100; tolerates typos like "incative" without matching unrelated words


class _FuzzyStatusPattern:
    """Duck-typed as a re.Pattern (only .search() is called) — matches the
    literal keywords via regex first, then falls back to word-level fuzzy
    matching so typos (e.g. "incative" for "inactive") are still caught,
    per the requirement that phrasing must not depend on exact spelling.

    Plain edit-distance alone scores "active" vs "inactive" at ~86/100 —
    well above a typo-tolerant threshold — which would make the two
    polarities fuzzy-match each other in BOTH directions. Two guards fix
    this without disabling fuzzy matching:

    *required_prefixes*: only words starting with one of these (e.g.
    "in"/"dis"/"deact") may fuzzy-match this pattern's keywords — lets
    "incative" still match "inactive" while blocking "active" itself.

    *excluded_prefixes*: words starting with one of these are never
    accepted as a fuzzy match for this pattern — lets "active" itself
    stay unmatched against the "inactive" keyword set even though
    edit-distance alone would accept it.
    """

    def __init__(self, literal_pattern: re.Pattern, fuzzy_keywords: tuple[str, ...],
                 required_prefixes: tuple[str, ...] = (), excluded_prefixes: tuple[str, ...] = ()):
        self._literal = literal_pattern
        self._fuzzy_keywords = fuzzy_keywords
        self._required_prefixes = required_prefixes
        self._excluded_prefixes = excluded_prefixes

    def search(self, q: str):
        m = self._literal.search(q)
        if m:
            return m
        for w in re.findall(r"[a-zA-Z]{4,}", q.lower()):
            if self._required_prefixes and not any(w.startswith(p) for p in self._required_prefixes):
                continue
            if any(w.startswith(p) for p in self._excluded_prefixes):
                continue
            if _fuzz.extractOne(w, self._fuzzy_keywords, score_cutoff=_STATUS_FUZZY_THRESHOLD):
                return True
        return None


_ACTIVE_PAT = _FuzzyStatusPattern(
    _kw(r"active", r"enabled"), ("active", "enabled"),
    excluded_prefixes=("in", "dis", "deact"),
)
_INACTIVE_PAT = _FuzzyStatusPattern(
    _kw(r"inactive", r"disabled", r"deactivated"),
    ("inactive", "disabled", "deactivated"),
    required_prefixes=("in", "dis", "deact"),
)


# ── query_type keyword tables (USER_LIST / DEPARTMENT_LIST / ROLE_LIST) ──

# "how many" combined with a status qualifier ("active"/"inactive") means
# "give me just that count", not the full total/active/inactive breakdown
# — active_count/inactive_count are handled specially in
# _extract_query_type below (checked before bare "count").
_HOW_MANY_PAT = _kw(r"how\s+many", r"count\s+of", r"total\s+number\s+of", r"number\s+of")

_USER_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("count", _HOW_MANY_PAT),
    ("duplicate_email", _kw(r"duplicate\s+email", r"same\s+email", r"shared\s+email")),
    ("never_login", _kw(r"never\s+logged\s*in", r"never\s+log\w*", r"not\s+logged\s*in")),
    ("failed_login", _kw(r"failed\s+log\w*", r"failed\s+password")),
    ("inactive", _INACTIVE_PAT),
    ("active", _ACTIVE_PAT),
]

_DEPARTMENT_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("count", _HOW_MANY_PAT),
    ("no_returns", _kw(r"no\s+returns?", r"without\s+any\s+returns?", r"zero\s+returns?")),
    ("most", _kw(r"most\s+returns?", r"maximum\s+returns?")),
    ("fewest", _kw(r"fewest\s+returns?", r"least\s+returns?", r"minimum\s+returns?")),
    ("with_counts", _kw(r"return\s+counts?", r"with\s+their\s+return", r"assigned\s+return\s+counts?")),
    ("inactive", _INACTIVE_PAT),
    ("active", _ACTIVE_PAT),
]

_ROLE_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("count", _HOW_MANY_PAT),
    ("exists", _kw(r"is\s+there\s+a\s+role", r"does\s+.*role.*exist", r"role\s+.*exist")),
    ("most_users", _kw(r"most\s+users", r"largest", r"biggest")),
    ("with_counts", _kw(r"user\s+counts?", r"number\s+of\s+users\s+in\s+each")),
    ("inactive", _INACTIVE_PAT),
    ("active", _ACTIVE_PAT),
]



# Canonical verb per HasXxx group, checked before its synonyms so
# "create new users" reports back "create" (natural) rather than "new"
# (grammatically awkward in "You can new.") — both map to the same
# HasNew attribute, so this only affects response phrasing, not correctness.
_CANONICAL_ACTION_ORDER = ("create", "edit", "view", "approve",
                           "add", "update", "modify", "see", "read",
                           "approval", "new")


def _extract_raw_action_word(q: str) -> str | None:
    """Return the raw action keyword (e.g. "approve", "create") — NOT the
    mapped HasNew/HasEdit/... attribute name that intent_classifier.
    _extract_action() returns. The new-taxonomy handlers do their own
    ACTION_MAP lookup on this raw word (see role_handlers.py's local
    _ACTION_MAP, which mirrors ACTION_MAP), so it must stay unmapped here.
    When multiple synonyms are present (e.g. "create new users" has both
    "create" and "new"), the canonical/most natural verb wins.
    """
    for kw in _CANONICAL_ACTION_ORDER:
        if re.search(rf"\b{re.escape(kw)}\b", q, re.IGNORECASE):
            return kw
    for kw in ACTION_MAP:
        if re.search(rf"\b{re.escape(kw)}\b", q, re.IGNORECASE):
            return kw
    return None


def _extract_query_type(q: str, table: list[tuple[str, re.Pattern]]) -> str | None:
    # "how many active X" / "how many inactive X" -> just that one number,
    # not the full total/active/inactive breakdown a bare "count" gives.
    if _HOW_MANY_PAT.search(q):
        if _ACTIVE_PAT.search(q):
            return "active_count"
        if _INACTIVE_PAT.search(q):
            return "inactive_count"
    for value, pat in table:
        if pat.search(q):
            return value
    return None


def _extract_named_entity_before_or_after(q: str, noun_words: tuple[str, ...]) -> str | None:
    """Extract a proper-noun-looking token immediately before OR after any
    of *noun_words* (e.g. "department"/"dept"). Handles both "Finance
    department" (before) and "department of Finance"/"in Finance" (after),
    which _extract_after_kw alone (after-only) cannot. A sentence-initial
    question/list word (What/Which/Who/...) is never returned as the name.
    """
    for word in noun_words:
        # Before: "<Name> department" / "<Name> dept users"
        for m in re.finditer(
            rf"\b([A-Z][A-Za-z0-9_.\-]{{1,40}})\s+{re.escape(word)}\b",
            q,
        ):
            candidate = m.group(1).strip()
            if candidate.lower() not in _NOT_AN_ENTITY_NAME:
                return candidate
    # After: reuse the existing after-keyword extractor with common prepositions.
    return _extract_after_kw(q, *[f"in {w}" for w in noun_words], *noun_words,
                              *[f"of {w}" for w in noun_words],
                              *[f"belonging to {w}" for w in noun_words])


def _extract_department_name_loose(q: str) -> str | None:
    """USERS_BY_DEPARTMENT-specific: the department name often appears with
    no literal "department"/"dept" word at all (e.g. "Users in Finance",
    "who works in Finance", "Finance users", "show members of Finance").
    Tries, in order: name-before-"users" ("Finance users"), name-after-
    "in"/"of"/"belonging to" ("in Finance"), then falls back to the
    noun-word-anchored extractor for phrasings that DO say "department".
    A leading question/list word (Which/Who/Show/List/...) directly before
    "users" is never itself the department name — skip it and keep
    searching rather than returning it.
    """
    for m in re.finditer(r"\b([A-Z][A-Za-z0-9_.\-]{1,40})\s+(?:department\s+)?users?\b", q):
        candidate = m.group(1).strip()
        if candidate.lower() not in _NOT_AN_ENTITY_NAME:
            return candidate
    m = re.search(r"\b(?:in|of|belonging\s+to|belongs?\s+to)\s+([A-Z][A-Za-z0-9_.\-]{1,40})\b", q)
    if m:
        return m.group(1).strip()
    return _extract_named_entity_before_or_after(q, ("department", "dept"))


# Trailing filler words that _extract_after_kw's generic stop-set doesn't
# cover — "due"/"next"/"date" etc. commonly trail the return name in
# NEXT_REPORTING_DATE phrasings ("return DBR01 due", "return CIMS RoR next")
# and would otherwise be captured as part of the name.
_TRAILING_FILLER_RE = re.compile(
    r"\s+(?:due|next|date|soon|now|please|today)\b.*$", re.IGNORECASE,
)

# Leading filler _extract_after_kw(q, "return", "form", "report") can
# capture when "return"/"form"/"report" appears earlier in a longer phrase
# than the actual name — e.g. "what is the RETURN id for CIMS_ROR" anchors
# on the bare word "return" and (with no more-specific phrase tried first)
# captures "id for CIMS_ROR" as the whole target. Stripped from the FRONT
# of whatever was captured, for every return-scoped intent that shares this
# extractor (return_profile, return_validation_config, submissions_for_
# return, notification_query, ...) — not just next_reporting_date.
_LEADING_FILLER_RE = re.compile(
    r"^(?:id|code|number|version|detail|details|info|information|status|"
    r"config|configuration)\s+(?:for|of)\s+", re.IGNORECASE,
)


def _clean_extracted_return_name(name: str | None) -> str | None:
    if not name:
        return None
    name = _LEADING_FILLER_RE.sub("", name).strip()
    name = _TRAILING_FILLER_RE.sub("", name).strip()
    return name or None


def _extract_return_name_for_due_date(q: str) -> str | None:
    """Return-name extraction for NEXT_REPORTING_DATE/RETURN_FIELD — handles
    both "return/form/report X" anchoring (shared with the other
    return-scoped intents) and "X for/of Y" phrasings that have no literal
    return/form/report keyword immediately before the name (e.g. "reporting
    date for CIMS_ROR", "reporting frequency of CIMS_ROR", "return id for
    CIMS_ROR")."""
    name = _extract_after_kw(q, "return", "form", "report")
    if not name:
        name = _extract_after_kw(
            q, "reporting date for", "due date for", "period end for",
            "period end date for", "reporting frequency of", "reporting frequency for",
            "frequency of", "frequency for", "reporting period of", "reporting period for",
            "period of", "return id for", "return id of", "internal form id for",
            "internal form id of", "submit", "file",
        )
    return _clean_extracted_return_name(name)


# field-word -> canonical RETURN_FIELD value, checked in this order so more
# specific phrases (matched first) win over generic ones.
_RETURN_FIELD_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("return_id", _kw(r"return\s+id", r"internal\s+form\s+id")),
    ("frequency", _kw(r"frequency", r"period\b", r"how\s+often")),
]


def _extract_return_field(q: str) -> str | None:
    for field, pat in _RETURN_FIELD_PATTERNS:
        if pat.search(q):
            return field
    return None


# Recognises "DD-Mon-YYYY", "DD/MM/YYYY", "DD-MM-YYYY", "YYYY-MM-DD",
# "DD.MM.YYYY", "DD Mon YYYY" (space-separated), or a bare month-year like
# "June 2025"/"Jun 2025" — the same date vocabulary instance_generator.py's
# _DATE_FMT/_EXTRA_FMTS already accept for a single date, extended here to
# find TWO dates in one "between X and Y" question.
_DATE_TOKEN = (
    r"\d{1,2}[-/.](?:[A-Za-z]{3,9}|\d{1,2})[-/.]\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}"
    r"|\d{4}-\d{1,2}-\d{1,2}"
    r"|[A-Za-z]{3,9}\s+\d{4}"
)
# Accepts "between X and Y", "from X to Y", "for the period X to Y", and
# "during X to Y" — all common ways users phrase a date range; the
# opening connector ("between"/"from"/"during"/"for the period") and the
# joining word ("and"/"to"/"-") are independent so any combination works
# (e.g. "between X to Y", "during X and Y"). Tried BEFORE the bare-month
# fallback below, so "during January 2026 to December 2026" resolves to
# the full Jan-Dec span, not just January (the bare-month fallback only
# ever extracts ONE month and would silently truncate a two-month range
# if it ran first).
_DATE_RANGE_RE = re.compile(
    rf"\b(?:between|from|during|for\s+the\s+period(?:\s+of)?)\s+({_DATE_TOKEN})\s+(?:and|to|-)\s+({_DATE_TOKEN})\b",
    re.IGNORECASE,
)


def _extract_date_range(q: str) -> tuple[str | None, str | None]:
    """Return (date_from, date_to) as raw matched strings from a "between
    X and Y" phrase (left unparsed — handler-layer parsing owns turning
    these into actual date objects, same separation as every other entity
    extractor in this module), or from a relative phrase ("next month" /
    "this month") resolved here into a concrete "DD-Mon-YYYY".."DD-Mon-YYYY"
    pair, since only the classifier sees the raw question text — by the
    time a handler runs it only has already-extracted entities, not q."""
    m = _DATE_RANGE_RE.search(q)
    if m:
        return m.group(1), m.group(2)

    import calendar
    from datetime import date as _date
    today = _date.today()
    if re.search(r"\bnext\s+month\b", q, re.IGNORECASE):
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        last_day = calendar.monthrange(year, month)[1]
        return f"01-{_date(year, month, 1).strftime('%b')}-{year}", f"{last_day:02d}-{_date(year, month, 1).strftime('%b')}-{year}"
    if re.search(r"\bthis\s+month\b", q, re.IGNORECASE):
        year, month = today.year, today.month
        last_day = calendar.monthrange(year, month)[1]
        return f"01-{_date(year, month, 1).strftime('%b')}-{year}", f"{last_day:02d}-{_date(year, month, 1).strftime('%b')}-{year}"

    # A bare "during/for/in <Month> <Year>" with no explicit range at all —
    # the whole named month is the implied span (mirrors
    # return_handlers.resolve_date_range's identical bare-month handling
    # on the extraction side).
    bare_month = re.search(
        r"\b(?:during|for|in)\s+([A-Za-z]{3,9}\s+\d{4})\b", q, re.IGNORECASE,
    )
    if bare_month:
        try:
            from dateutil import parser as _du_parser
            dt = _du_parser.parse(f"1 {bare_month.group(1)}", dayfirst=True)
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            return (
                f"01-{dt.strftime('%b')}-{dt.year}",
                f"{last_day:02d}-{dt.strftime('%b')}-{dt.year}",
            )
        except (ValueError, OverflowError):
            pass

    return None, None


_XBRL_TYPE_RE = _kw(_NON_XBRL, r"nx\b")


def _extract_xbrl_type(q: str) -> str | None:
    """"xbrl" or "non_xbrl", or None if the question doesn't specify —
    handlers treat None as "both"."""
    if _XBRL_TYPE_RE.search(q):
        return "non_xbrl"
    if re.search(r"\bxbrl\b", q, re.IGNORECASE):
        return "xbrl"
    return None


def _extract_new_params(intent: Intent, q: str) -> dict:
    params: dict = {}
    explicit = _extract_quoted_or_bracketed(q)

    if intent in (Intent.USER_PROFILE, Intent.USER_FIELD, Intent.USERS_BY_DEPARTMENT,
                  Intent.AUDIT_HISTORY, Intent.SUBMISSION_STATUS, Intent.SUBMISSION_DETAIL,
                  Intent.USER_ACCESS_SUMMARY, Intent.SECURITY_EVENTS):
        params["target_user"] = explicit or _extract_after_kw(q, "user", "for user", "of user", "about user")

    if intent == Intent.USERS_BY_DEPARTMENT:
        params["target_department"] = explicit or _extract_department_name_loose(q)
    elif intent in (Intent.DEPARTMENT_PROFILE, Intent.DEPARTMENT_RETURNS,
                    Intent.DEPARTMENT_HAS_RETURN, Intent.DEPT_FULL_RETURN_LIST, Intent.CROSS_ENTITY_QUERY,
                    Intent.AUDIT_ENTITY_TRAIL, Intent.NONXBRL_RETURN_LIST, Intent.RETURNS_SUBMITTABLE_BY_DEPT):
        params["target_department"] = explicit or _extract_named_entity_before_or_after(q, ("department", "dept"))

    if intent in (Intent.USERS_BY_ROLE, Intent.ROLE_PROFILE, Intent.ROLE_USERS, Intent.PERMISSION_CHECK,
                  Intent.PERMISSION_PROFILE, Intent.ROLES_WITH_PERMISSION, Intent.ROLE_MODULE_ACCESS,
                  Intent.ROLE_PERMISSION_DIFF, Intent.CROSS_ENTITY_QUERY):
        params["target_role"] = explicit or _extract_named_entity_before_or_after(q, ("role",))

    if intent in (Intent.RETURN_PROFILE, Intent.RETURN_VALIDATION_CONFIG, Intent.NONXBRL_RETURN_PROFILE,
                  Intent.SUBMISSIONS_FOR_RETURN, Intent.SUBMISSION_LIST, Intent.MY_SUBMISSION_HISTORY,
                  Intent.DEPARTMENTS_WITH_RETURN_ACCESS, Intent.DEPARTMENT_HAS_RETURN,
                  Intent.MY_RETURN_ACCESS, Intent.RETURNS_SUBMITTABLE_BY_DEPT, Intent.LOG_QUERY,
                  Intent.NOTIFICATION_QUERY, Intent.AUDIT_ENTITY_TRAIL, Intent.CROSS_ENTITY_QUERY):
        params["target_return"] = explicit or _clean_extracted_return_name(_extract_after_kw(q, "return", "form", "report"))
    elif intent in (Intent.NEXT_REPORTING_DATE, Intent.RETURN_FIELD):
        params["target_return"] = explicit or _extract_return_name_for_due_date(q)

    if intent == Intent.RETURN_FIELD:
        params["field"] = _extract_return_field(q)

    if intent in (Intent.REPORTS_FILED_IN_RANGE, Intent.REPORTS_UPCOMING_IN_RANGE):
        date_from, date_to = _extract_date_range(q)
        params["date_from"] = date_from
        params["date_to"] = date_to
        params["xbrl_type"] = _extract_xbrl_type(q)

    if intent in (Intent.PERMISSION_CHECK, Intent.ROLES_WITH_PERMISSION):
        # Raw keyword, NOT the mapped HasNew/HasEdit/... attribute name —
        # query_handlers/role_handlers.py's handle_permission_check() and
        # handle_roles_with_permission() do their own ACTION_MAP lookup on
        # this value (their own local _ACTION_MAP mirrors
        # intent_classifier.ACTION_MAP), so passing the already-mapped
        # attribute here would double-map and fail to match.
        params["action"] = _extract_raw_action_word(q)

    if intent in (Intent.RETURNS_BY_FREQUENCY, Intent.PERIOD_LOOKUP):
        params["period_name"] = _extract_period(q)

    if intent == Intent.USER_FIELD:
        for field, pat in _USER_FIELD_PATTERNS.items():
            if re.search(pat, q, re.IGNORECASE):
                params["field"] = field
                break

    if intent == Intent.USER_LIST:
        params["query_type"] = _extract_query_type(q, _USER_QUERY_TYPE_PATTERNS)

    if intent == Intent.DEPARTMENT_LIST:
        params["query_type"] = _extract_query_type(q, _DEPARTMENT_QUERY_TYPE_PATTERNS)

    if intent == Intent.ROLE_LIST:
        params["query_type"] = _extract_query_type(q, _ROLE_QUERY_TYPE_PATTERNS)
        if params["query_type"] == "exists":
            params["target_role"] = explicit or _extract_named_entity_before_or_after(q, ("role",))

    if intent in (Intent.PERMISSION_CHECK, Intent.ROLE_MODULE_ACCESS, Intent.ROLES_WITH_PERMISSION):
        m = re.search(
            rf"\b(sdmx|cross-?validation|nxquerybuilder|balance\s+sheet|data\s+preparation|"
            rf"audit\s+log|{_NON_XBRL}\s+upload(?:s)?|maker-?checker|provider\w*|department\s+settings?)\b",
            q, re.IGNORECASE,
        )
        if m:
            params["module"] = m.group(1)
        else:
            # Only a bare "... module" phrasing gives a reliable module name
            # this way — "on"/"to" are too generic and swallow the action
            # verb itself (e.g. "edit department settings" -> "edit
            # department settings" instead of just the module).
            params.setdefault("module", _extract_after_kw(q, "module"))

    return {k: v for k, v in params.items() if v is not None}
