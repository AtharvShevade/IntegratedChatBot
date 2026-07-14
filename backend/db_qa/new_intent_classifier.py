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
    "failed_login_count": r"\bfailed\s+(login|password)\b",
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
                     r"which\s+(xbrl|non-xbrl)?\s*returns?", r"does\s+.{0,20}department",
                     r"xbrl\s+returns?", r"non-xbrl\s+returns?"),),
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
                     r"provider\w*", r"non-?xbrl\s+upload", r"maker-?checker"),),
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
    _mk(Intent.RETURN_PROFILE, ("return",),
        r"\breturn\s+id\s+for\b", r"\btaxonomy\s+(version|does)\b", r"\bxsd\s+path\b",
        r"\bdue\s+days?\s+.*submission\s+of\s+return\b", r"\balternate\s+name\s+for\s+return\b"),
    _mk(Intent.RETURN_LIST, ("self", "system_wide"),
        r"\ball\s+(the\s+)?xbrl\s+returns?\b", r"\bhow\s+many\s+xbrl\s+returns?\b",
        r"\bwhich\s+xbrl\s+returns?\s+(are|is)\b", r"\bcims-enabled\s+returns?\b"),
    _mk(Intent.NONXBRL_RETURN_PROFILE, ("self", "return"),
        r"\bbase\s+(file\s+)?template\s+for\s+non-xbrl\b", r"\bjob\s+processing\s+id\b"),
    _mk(Intent.NONXBRL_RETURN_LIST, ("self", "department", "system_wide"),
        r"\bnon-xbrl\s+returns?\b", r"\bhow\s+many\s+non-xbrl\b"),
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
        params = _extract_new_params(intent, q)
        params["target_type"] = target_type
        return intent, params, target_type

    for intent, target_types, patterns in _NEW_RULES:
        for pat in patterns:
            if pat.search(q):
                target_type = _infer_target_type(q, target_types)
                params = _extract_new_params(intent, q)
                params["target_type"] = target_type
                return intent, params, target_type
    return None, {}, None


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
    ("inactive", _kw(r"inactive", r"disabled", r"deactivated")),
    ("active", _kw(r"active", r"enabled")),
]

_DEPARTMENT_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("count", _HOW_MANY_PAT),
    ("no_returns", _kw(r"no\s+returns?", r"without\s+any\s+returns?", r"zero\s+returns?")),
    ("most", _kw(r"most\s+returns?", r"maximum\s+returns?")),
    ("fewest", _kw(r"fewest\s+returns?", r"least\s+returns?", r"minimum\s+returns?")),
    ("with_counts", _kw(r"return\s+counts?", r"with\s+their\s+return", r"assigned\s+return\s+counts?")),
    ("inactive", _kw(r"inactive", r"disabled", r"deactivated")),
    ("active", _kw(r"active", r"enabled")),
]

_ROLE_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("count", _HOW_MANY_PAT),
    ("exists", _kw(r"is\s+there\s+a\s+role", r"does\s+.*role.*exist", r"role\s+.*exist")),
    ("most_users", _kw(r"most\s+users", r"largest", r"biggest")),
    ("with_counts", _kw(r"user\s+counts?", r"number\s+of\s+users\s+in\s+each")),
    ("inactive", _kw(r"inactive", r"disabled", r"deactivated")),
    ("active", _kw(r"active", r"enabled")),
]

_ACTIVE_PAT = _kw(r"active", r"enabled")
_INACTIVE_PAT = _kw(r"inactive", r"disabled", r"deactivated")


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
        params["target_return"] = explicit or _extract_after_kw(q, "return", "form", "report")

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
            r"\b(sdmx|cross-?validation|nxquerybuilder|balance\s+sheet|data\s+preparation|"
            r"audit\s+log|non-?xbrl\s+upload(?:s)?|maker-?checker|provider\w*|department\s+settings?)\b",
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
