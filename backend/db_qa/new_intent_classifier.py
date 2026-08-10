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

import logging
import re

from rapidfuzz import process as _fuzz

from backend.db_qa.intent_classifier import (
    _extract_action, _extract_after_kw, _extract_period,
    _extract_quoted_or_bracketed, _self_ref, ACTION_MAP, PERIOD_ALIASES,
)
from backend.db_qa.intents.taxonomy import Intent

logger = logging.getLogger(__name__)

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
    "all", "the", "does", "is", "are", "can", "do", "did", "has", "have",
    "count", "number", "tell", "please", "how", "many",
    # Connector words — matter now that _extract_named_entity_before_or_after's
    # "before" pattern is case-insensitive: "ID of department Dept1" and
    # "belong to department Finance" would otherwise return "of"/"to" as
    # the candidate (the first word immediately before "department"),
    # since neither was excluded when only capitalized candidates could
    # ever reach this set.
    "of", "to", "for", "in", "at", "by", "from", "with", "id",
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

# "submit"/"generate"/"create"/"file" — end users describe filing a return
# with any of these interchangeably (mirrors the synonym set documented
# inline at REPORTS_FILED_IN_RANGE below, extracted here so
# RETURNS_SUBMITTABLE_BY_DEPT's rule can reuse it without duplicating the
# alternation and drifting out of sync).
_RETURN_SUBMIT_VERBS = r"(?:submit(?:ted|s)?|generat(?:ed?|es)?|creat(?:ed?|es)?|file[ds]?|filing[s]?)"


# Natural-language module references -> canonical substring. role_handlers.
# handle_permission_check()/handle_roles_with_permission() filter accesses
# via `module.lower() in OptionName.lower()` (a plain substring test against
# the real XML_RoleAccess OptionName values — see XMLStore.enrich_role_access),
# so each canonical value here must actually be a substring of the real
# name(s) it's meant to select, not just an arbitrary label echoing the
# user's words back (the previous version of this table passed the raw
# regex capture straight through, which is why "returns"/"reports" — not a
# substring of "XBRL Report" or "Non-XBRL Reports" — never matched anything
# and silently fell back to listing every module the role can act on).
#
# Ordered most-specific first: a query naming an exact module ("XBRL Query
# Builder") must resolve to that one before the generic "returns"/"reports"
# catch-all (which matches every Report/Reports/Generation/MISReport module)
# has a chance to swallow it.
_MODULE_SYNONYMS: list[tuple[re.Pattern, str]] = [
    (_kw(r"xbrl\s+query\s+builder"), "xbrl query"),
    (_kw(rf"{_NON_XBRL}\s+query\s+builder", r"nxquerybuilder"), "non-xbrl query"),
    (_kw(rf"{_NON_XBRL}\s+generation", rf"generate\s+{_NON_XBRL}"), "non-xbrl generation"),
    (_kw(rf"{_NON_XBRL}\s+log"), "non-xbrl log"),
    # "NX FileUpload" — the real OptionName for uploading Non-XBRL files.
    # Listed BEFORE the "non-xbrl report(s)" entry and well before the bare
    # "roles?" catch-all near the end: without it, the long-standing
    # exemplar "Which roles can upload Non-XBRL files?" matched nothing
    # specific and fell through to `\broles?\b` -> module="role", filtering
    # the answer by the "Roles" menu module instead of by file upload.
    # ("files" is deliberately part of the alternation — "upload" alone is
    # too generic, and no other OptionName contains "fileupload".)
    (_kw(rf"{_NON_XBRL}\s+files?", rf"upload\s+{_NON_XBRL}", rf"{_NON_XBRL}\s+upload",
         r"nx\s*fileupload", r"file\s*upload"), "fileupload"),
    (_kw(rf"{_NON_XBRL}\s+reports?", rf"{_NON_XBRL}\s+returns?"), "non-xbrl report"),
    (_kw(r"xbrl\s+generation", r"generate\s+xbrl"), "xbrl generation"),
    (_kw(r"xbrl\s+reports?", r"xbrl\s+returns?"), "xbrl report"),
    (_kw(r"sdmx\s+generation"), "sdmx generation"),
    (_kw(r"sdmx\s+log"), "sdmx log"),
    # Bare "sdmx" (no generation/log qualifier) — matches both SDMX
    # Generation and SDMX Log, the right breadth for an unqualified "access
    # to sdmx" the way the generic report/reports entry below covers every
    # Report-family module. Safe as a substring match unlike a hypothetical
    # bare "xbrl" catch-all would be — "xbrl" is also a substring of every
    # Non-XBRL module name, but "sdmx" isn't a substring of anything else.
    (_kw(r"\bsdmx\b"), "sdmx"),
    (_kw(r"report\s+log"), "report log"),
    # Generic "returns"/"reports" catch-all — matches XBRL Report, Non-XBRL
    # Reports, Report, Report Log, and MISReport (all contain "report" as a
    # substring), which is the right breadth for an unqualified "can I
    # generate/edit/view returns?" that doesn't say XBRL vs Non-XBRL.
    (_kw(r"returns?", r"reports?"), "report"),
    (_kw(r"maker[\s/-]?checker"), "maker/checker"),
    (_kw(r"bank\s+details?"), "bank"),
    (_kw(r"data\s+variation"), "data variation"),
    (_kw(r"data\s+preparation"), "data preparation"),
    (_kw(r"balance\s+sheet"), "balance sheet"),
    (_kw(r"cross-?validation"), "cross validation"),
    (_kw(r"user\s+notifications?"), "user notification"),
    (_kw(r"notifications?"), "notification"),
    (_kw(r"departments?"), "department"),
    (_kw(r"\busers?\b"), "user"),
    (_kw(r"\broles?\b"), "role"),
    (_kw(r"providers?"), "provider"),
    (_kw(r"\bgraph\b"), "graph"),
    (_kw(r"duar\s+csv"), "duar"),
]


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


class _NamedRoleActionPattern:
    """Duck-typed like a compiled pattern (only .search() called by
    _KeywordRule.match_score). Matches "<name> role(s) <verb>" with the
    verb immediately adjacent — "the admin role create", "checker role
    approve" — as opposed to "which roles CAN create" where "can"
    separates the role noun from the verb. Used as a ROLES_WITH_PERMISSION
    exclude: an explicitly named role right next to the verb signals a
    role-scoped question, not a system-wide "which roles can do X" one."""

    # Deliberately excludes "access" — ROLE_MODULE_ACCESS's own domain is
    # listing every module a role has ANY access to, so "the admin role
    # access X" should stay there, not be diverted to a single-permission
    # PERMISSION_CHECK just because "access" resembles an action verb.
    _PAT = re.compile(
        r"\b([A-Za-z][A-Za-z0-9_.\-]{1,40})\s+roles?\s+"
        r"(?:create|edit|update|modify|view|see|approve|add|upload|"
        r"disable|delete|run|generate|do|manage|perform)\b",
        re.IGNORECASE,
    )

    def search(self, q: str):
        m = self._PAT.search(q)
        if m and m.group(1).lower() not in _NOT_AN_ENTITY_NAME:
            return m
        return None


class _NamedRoleAccessPattern:
    """Duck-typed like a compiled pattern. Matches "<name> role(s) [have/
    has] access" — a role explicitly named, asking generically about its
    module access (not one specific create/edit/view/approve action).
    Used to exclude ROLES_WITH_PERMISSION so this reaches ROLE_MODULE_ACCESS
    instead (which lists every module the role can touch in any way) —
    ROLES_WITH_PERMISSION's own "access"/"full access" trigger verbs would
    otherwise outscore it and silently discard the named target_role, the
    same class of bug _NamedRoleActionPattern fixes for CRUD verbs.

    Both word orders are matched. "<name> role has access" is the common
    one; "role <name> has access" ("Does role Tester have access to the
    SDMX generation module?" — a verbatim ROLE_MODULE_ACCESS exemplar) is
    just as natural and was previously unmatched, because the word before
    "role" there is the filler "Does" and the real name sits after it. That
    left the exemplar landing on ROLES_WITH_PERMISSION with target_role
    dropped entirely — the exact bug this class exists to prevent."""

    _PATS = (
        re.compile(r"\b([A-Za-z][A-Za-z0-9_.\-]{1,40})\s+roles?\s+(?:have\s+|has\s+)?access\b",
                   re.IGNORECASE),
        re.compile(r"\broles?\s+([A-Za-z][A-Za-z0-9_.\-]{1,40})\s+(?:have\s+|has\s+)?access\b",
                   re.IGNORECASE),
    )

    def search(self, q: str):
        for pat in self._PATS:
            m = pat.search(q)
            if m and m.group(1).lower() not in _NOT_AN_ENTITY_NAME:
                return m
        return None


# Status/quantifier words that can precede "users" without naming a role at
# all ("all users", "active users") — excluded so _RoleUsersStructuralPattern
# doesn't mistake them for a role name.
_ROLE_USERS_STATUS_WORDS = frozenset({
    "all", "active", "inactive", "enabled", "disabled", "new", "existing",
    "current", "total", "every", "some", "few", "many", "other", "external",
    "internal", "registered", "duplicate", "failed", "locked", "deactivated",
    "the", "these", "those", "such", "my", "our", "your", "admin's",
    # USER_LIST's own domain vocabulary ("duplicate EMAIL users", "stale
    # PASSWORD users") — the word directly before "users" in these phrasings
    # is never a role name.
    "email", "password", "login", "stale",
    # Aggregation words ("which role has the MOST/LEAST users") — never a
    # role name themselves, and ROLE_LIST's own aggregation branch owns
    # this phrasing, not a per-role users listing.
    "most", "least", "fewest", "minimum", "maximum", "smallest", "largest",
    "biggest",
    # Action verbs ("can I CREATE users", "DELETE users") — PERMISSION_
    # CHECK's territory, never a role reference.
    "create", "edit", "view", "approve", "delete", "add", "update",
    "remove", "manage", "modify", "disable", "upload",
    # "role"/"roles" itself — "development ROLE users" would otherwise
    # match "<word> users" as "role users" (word="role"), stealing the
    # match before the real name ("development") is even considered.
    "role", "roles",
    # "users belong to DEPARTMENT Finance" — "department"/"dept" is a
    # generic noun, not the name itself (that's USERS_BY_DEPARTMENT's own
    # structural pattern's territory, one word further on).
    "department", "dept",
})


_ROLE_USERS_TOKEN_RE = re.compile(r"\busers?\b", re.IGNORECASE)
_ROLE_USERS_BEFORE_WORD_RE = re.compile(r"([A-Za-z][A-Za-z0-9_\-]*)\s*$")
_ROLE_USERS_AFTER_CONNECTOR_RE = re.compile(
    r"^\s*(?:assigned\s+to|belong(?:ing|s)?\s+to|under|with|having)\s+"
    r"(?:the\s+)?(?P<name>[A-Za-z][A-Za-z0-9_\-]*)",
    re.IGNORECASE,
)
_ROLE_USERS_PREDICATE_RE = re.compile(
    r"\b(?:whose\s+role\s+is|role\s+is)\s+(?P<name>[A-Za-z][A-Za-z0-9_\-]*)\b", re.IGNORECASE,
)
_ROLE_USERS_WHO_HAS_RE = re.compile(
    r"\bwho\s+(?:has|is\s+assigned|belongs?\s+to)\s+(?:the\s+)?(?P<name>[A-Za-z][A-Za-z0-9_\-]*)(?:\s+role)?\b",
    re.IGNORECASE,
)


def _role_users_name_ok(name: str) -> bool:
    word = name.lower()
    return word not in _ROLE_USERS_STATUS_WORDS and word not in _NOT_AN_ENTITY_NAME


class _RoleUsersStructuralPattern:
    """Matches a ROLE name typed with no literal "role" word nearby at all
    (or, for "who has X"/"whose role is X", regardless of whether "role"
    appears), in any of the common orderings — "give me all admin users"
    (name before "users"), "users assigned to Admin" / "users belonging to
    Maker" / "users under Checker" (name after, via a connecting verb),
    "who has Admin role?" / "whose role is Tester" (predicate framing).
    Case-insensitive throughout, since real users type role names in
    lowercase far more often than department names (which
    _UsersByDeptStructuralPattern already handles, capitalized-only).

    Deliberately NOT one single alternation tried via re.finditer: a
    combined pattern's FIRST alternative to match at a given scan position
    wins and consumes those characters, even when its captured word is
    filler — e.g. "Show users assigned to Admin" would match "<word>
    users" as "Show users" (rejected — "show" is filler) and then never
    get a chance to try the "users assigned to <name>" alternative at all,
    since finditer resumes scanning only after the consumed match. Each
    ordering is instead checked independently against the same text.
    """

    def search(self, q: str):
        return self._match(q)

    @staticmethod
    def extract_name(m) -> str | None:
        """The captured role name from a match returned by .search() —
        needed because the underlying sub-patterns use different group
        shapes (a bare group(1) for the before-"users" case, a named
        "name" group for the rest)."""
        if m is None:
            return None
        try:
            return m.group("name")
        except IndexError:
            return m.group(1)

    def _match(self, q: str):
        m = self._first_ok(_ROLE_USERS_PREDICATE_RE, q) or self._first_ok(_ROLE_USERS_WHO_HAS_RE, q)
        if m:
            return m
        for um in _ROLE_USERS_TOKEN_RE.finditer(q):
            bm = _ROLE_USERS_BEFORE_WORD_RE.search(q[: um.start()])
            if bm and _role_users_name_ok(bm.group(1)):
                return bm
            am = _ROLE_USERS_AFTER_CONNECTOR_RE.match(q[um.end():])
            if am and _role_users_name_ok(am.group("name")):
                return am
        return None

    @staticmethod
    def _first_ok(pattern: re.Pattern, q: str):
        for m in pattern.finditer(q):
            if _role_users_name_ok(m.group("name")):
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
    #
    # excludes: bare "profile" alone used to always win here even when the
    # question actually names a RETURN ("give me the full profile for
    # DBR01") — RETURN_PROFILE's patterns live in the lower-priority
    # _NEW_RULES tier (see module docstring: keyword rules are tried first,
    # most-specific-member-wins; literal _mk patterns only run if no
    # keyword rule matched at all), so USER_PROFILE's bare "profile" match
    # was never even giving RETURN_PROFILE a chance to compete (self-test:
    # doc/INTENT_GAP_ANALYSIS.md — "Profile for iris810." instead of DBR01's
    # actual profile, still broken as of Round 5). Excludes the literal word
    # "return"/"filing" and a return-code-shaped token (letters immediately
    # followed by 2+ digits, e.g. "DBR01", "DPSS09" — matches case-
    # insensitively since _kw() compiles with IGNORECASE).
    _KeywordRule(
        Intent.USER_PROFILE, ("self", "other_user"),
        all_of=(_kw(r"profile", r"account\s*details?", r"my\s*details?",
                     r"who\s+am\s+i", r"details?\s+of\s+user"),),
        excludes=(_kw(r"\breturn\b", r"\bfiling\b", r"\b[a-z]+\d{2,}\b"),),
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
        # A sentence naming returns/forms/reports is never actually asking
        # about USERS in a department, no matter how strongly "<Name>
        # department" matches structurally — e.g. "Which returns are
        # available for the Treasury department?" was being misrouted here
        # (score 101, from this rule's priority bump) instead of to
        # DEPARTMENT_RETURNS (score ~3), because this structural pattern
        # doesn't look at the rest of the sentence at all. USERS_BY_
        # DEPARTMENT questions in this taxonomy never mention returns/
        # forms/reports, so this exclude only removes false positives.
        excludes=(_kw(r"returns?", r"forms?", r"reports?"),),
        priority=1,
    ),

    # users_by_role: role-noun + "assigned"/"with"/"have" + user-noun
    _KeywordRule(
        Intent.USERS_BY_ROLE, ("role",),
        all_of=(_G_USER_NOUN, _G_ROLE_NOUN),
        any_of=(_kw(r"assigned", r"with", r"have", r"has", r"holding", r"belong\w*"), _G_LIST_VERB, _G_HOW_MANY),
        # Same rationale as ROLE_USERS' identical exclude below — "which
        # role HAS the most users" / "...number of users in each" are
        # ROLE_LIST aggregation questions, and a self-referential "share
        # the same role as me" is ROLE_PEER_COUNT's, never this intent's.
        excludes=(_kw(r"most\s+users?", r"least\s+users?", r"fewest\s+users?",
                     r"minimum\s+users?", r"maximum\s+users?",
                     r"smallest\s+role", r"largest\s+role", r"biggest\s+role",
                     r"least[\s-]?used\s+role",
                     r"number\s+of\s+users\s+in\s+each",
                     r"\bmy\s+role\b", r"share.{0,20}role", r"as\s+me\b",
                     # A question about MODULES/PERMISSIONS/CONTROL for a
                     # role (e.g. "which modules does the Admin User role
                     # have full control over?") is never actually asking
                     # to list the role's users — but it can still
                     # structurally satisfy this rule's groups whenever the
                     # role's own NAME happens to contain the word "User"
                     # (e.g. "Admin User"), so that alone can't be trusted.
                     r"\bmodules?\b", r"permissions?", r"full\s+control"),),
    ),

    # users_by_role, structural: "<word> users" with no literal "role" word
    # at all ("give me all admin users", "list of all tester users") —
    # mirrors USERS_BY_DEPARTMENT's own structural rule above, but
    # case-insensitive since role names get typed in lowercase far more
    # often in practice than department names do.
    _KeywordRule(
        Intent.USERS_BY_ROLE, ("role",),
        all_of=(_RoleUsersStructuralPattern(),),
        # A per-word exclusion inside the structural pattern itself only
        # catches aggregation/action words directly ADJACENT to "users"
        # ("largest role BY users" has the excluded word elsewhere in the
        # sentence) — these sentence-wide excludes catch the rest: any
        # most/least/aggregation phrasing is ROLE_LIST's question, and a
        # genuine self-reference ("MY role", "share...role...AS ME") is
        # ROLE_PEER_COUNT's — but NOT bare "me"/"my" alone, which would
        # also match harmless polite fillers ("show ME...", "give ME...")
        # that have nothing to do with self-reference.
        excludes=(_kw(r"\bmost\b", r"\bleast\b", r"\bfewest\b", r"\blargest\b",
                     r"\bbiggest\b", r"\bsmallest\b", r"\bminimum\b", r"\bmaximum\b",
                     r"\bmy\s+role\b", r"share.{0,20}role", r"as\s+me\b"),),
        priority=1,
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
        # "number of users in each" only ever describes a PER-ROLE (or
        # per-department) breakdown ("list all roles with the number of
        # users in each") — there's no "each" grouping for a flat list of
        # all users, so this can never be a genuine USER_LIST question;
        # without it, this rule tied on score with ROLE_LIST's own
        # "number of users in each" trigger and won by list position.
        excludes=(_kw(r"\bmy\b", r"number\s+of\s+users\s+in\s+each"),),
    ),

    # ── DEPARTMENT ───────────────────────────────────────────────────────
    # (DEPARTMENT_INTENTS, used by classify_new_with_semantic_tiers() to scope
    # the widened embedding_none -> LLM path, is defined near that function.)

    _KeywordRule(
        Intent.DEPARTMENT_HAS_RETURN, ("self", "department"),
        all_of=(_G_DEPT_NOUN, _kw(r"access", r"have\s+access")),
        any_of=(_kw(r"return", r"form", r"report"),),
        # "every return"/"all returns" is a generic quantifier, not one
        # SPECIFIC named return — "show me every return department X has
        # access to" is a LISTING question (DEPARTMENT_RETURNS' territory),
        # not "does department X have access to return Y". Both rules
        # otherwise tie on the same dept+access+return groups, and this one
        # was defined first, silently winning and leaving target_return
        # extraction to grab "department X has access" instead of a name.
        # "which/what departments ... <type> returns" enumerates DEPARTMENTS
        # for a whole return TYPE — DEPARTMENTS_WITH_RETURN_ACCESS' type-level
        # form — not "does department X have access to return Y".
        excludes=(_kw(r"every\s+returns?", r"all\s+returns?", r"any\s+returns?"),
                  re.compile(r"(?:which|what)\s+departments?.{0,40}(?:non[\s-]?xbrl|xbrl)\s+returns?", re.IGNORECASE)),
    ),

    # priority=1: "Which departments have access to return X?" also matches
    # DEPARTMENT_HAS_RETURN's rule below (same all_of/any_of groups, same
    # score) — both ask about department<->return access, but this one is
    # the right direction for a PLURAL "which/how many departments" framing
    # (checking access across all departments) vs. DEPARTMENT_HAS_RETURN's
    # singular "does department X have access" framing. Without this bump,
    # the tie was resolved by list position, which favoured
    # DEPARTMENT_HAS_RETURN and misrouted every "which departments have
    # access to return X" question to the wrong intent (confirmed live:
    # "Which departments have access to return CIMS_ROR?" -> wrongly
    # classified as department_has_return).
    _KeywordRule(
        Intent.DEPARTMENTS_WITH_RETURN_ACCESS, ("return",),
        # "missed the submission deadline for return X" — a per-department
        # audit question of the same shape as "which departments have
        # access to X" (query_type="missed_deadline" tells the handler to
        # additionally check each accessing department's filing status),
        # so "deadline"/"missed" are accepted alongside access/submit.
        all_of=(_G_DEPT_NOUN, _kw(r"access", r"submit\w*", r"deadline", r"missed",
                                   # "which departments are ASSIGNED non-XBRL
                                   # returns" is the same question with the
                                   # relationship named from the other side.
                                   r"assigned")),
        # "what departments ..." is as common as "which departments ..." and
        # was previously unmatched here, so it fell through to whichever
        # singular-department rule happened to match instead.
        any_of=(_kw(r"which", r"how many", r"what"),),
        # A specific NAMED department ("department Dept1", "Dept1
        # department") means the question is about THAT department's own
        # returns (DEPARTMENT_RETURNS' territory — "which XBRL returns
        # does department Dept1 have access to?"), never "which
        # departments have access to return X" (this intent's own
        # territory, which only ever names a RETURN, not a department).
        # Without this exclude, both phrasings tied on score and were
        # resolved by this rule's priority bump alone, so a named-department
        # question like "Which XBRL returns department Dept1 has access?"
        # was wrongly routed here and left asking for a return name instead
        # of ever looking at "Dept1".
        # "which department HAS ACCESS TO the most returns" is DEPT_RETURN_
        # ACCESS_MATRIX's cross-department ranking question (no specific
        # return named at all), not "which departments have access to
        # RETURN X" — this rule's dept+access+which groups otherwise match
        # both equally.
        excludes=(_kw(r"\bmy\b", r"access\s+to\s+the\s+most\s+returns?"),
                  re.compile(r"\b(?i:department|dept)\s+[A-Z]\w*")),
        priority=1,
    ),

    # Deliberately narrow (see the DEPARTMENT_RETURNS section of
    # backend/db_qa/intents/exemplars.py for the rationale): this rule is
    # meant to catch only the handful of unambiguous, near-templated
    # phrasings — explicit "which XBRL/Non-XBRL returns", "department...
    # access", "access...return(s)", "does <department> have access". A
    # broader order-independent "return(s)...access/assign(ed) in EITHER
    # direction" pattern used to live here and reliably matched real
    # paraphrases, but it also had to be hand-extended for every new synonym
    # ("applicable to", "available for", "can file") forever, and it still
    # missed several — that generalization work now belongs to the
    # embedding tier (classify_by_embedding), which is trained on real
    # paraphrases instead of a growing regex. Anything that doesn't hit one
    # of the templated forms below is expected to fall through to tier 2/3.
    _KeywordRule(
        Intent.DEPARTMENT_RETURNS, ("self", "department"),
        all_of=(_G_DEPT_NOUN, _kw(r"returns?", r"forms?", r"reports?")),
        any_of=(_kw(r"department.{0,30}access", r"access.{0,30}(return|form|report)",
                     rf"which\s+(xbrl|{_NON_XBRL})?\s*returns?", r"does\s+.{0,20}department",
                     r"xbrl\s+returns?", rf"{_NON_XBRL}\s+returns?",
                     # Verb synonyms for "assigned to"/"has access to" a
                     # department's returns — users describe the same
                     # relationship as available/accessible/mapped/linked/
                     # configured just as often as "assigned"/"access".
                     r"available\s+(for|to)", r"accessible\s+(by|to|for)",
                     r"mapped\s+to", r"linked\s+to", r"configured\s+for"),),
        # "accessible by the maximum/most" / "accessible by all departments"
        # / "department has access to the most returns" are DEPT_RETURN_
        # ACCESS_MATRIX's cross-department RANKING questions (system-wide,
        # no single department or return named) — not a specific
        # department's return list, even though they also satisfy this
        # rule's dept+return+"accessible by" groups.
        # "which returns are overdue (for submission) across all
        # departments" asks about SUBMISSION TIMING (REPORTS_UPCOMING_IN_
        # RANGE's "overdue" query_type) — "departments" here is only a
        # scope qualifier, not a request naming/listing a department's
        # own return list.
        excludes=(_kw(r"summary\s+of\s+my\s+access", r"full\s+summary", r"full\s+profile",
                     r"accessible\s+by\s+(the\s+)?(maximum|most)", r"accessible\s+by\s+all\s+departments?",
                     r"department\s+has\s+access\s+to\s+the\s+most\s+returns?",
                     r"overdue"),
                  # Same type-level carve-out as DEPARTMENT_HAS_RETURN above:
                  # a plural "which/what departments" framing asks which
                  # departments hold a TYPE of return, not for one named
                  # department's own return list.
                  re.compile(r"(?:which|what)\s+departments?.{0,40}(?:non[\s-]?xbrl|xbrl)\s+returns?", re.IGNORECASE)),
    ),

    _KeywordRule(
        Intent.DEPARTMENT_PROFILE, ("self", "department"),
        all_of=(_G_DEPT_NOUN,),
        any_of=(_kw(r"email", r"\bid\b", r"identifier", r"what\s+department\s+am\s+i",
                     r"which\s+department",
                     # "is my department currently active" — previously fell
                     # through to the embedding tier, which correctly flagged
                     # it as ambiguous against DEPARTMENT_LIST, but the LLM
                     # disambiguation tie-break sometimes picked the wrong
                     # one ("There are 1 active departments." — a system-wide
                     # count — instead of answering about MY department).
                     # A direct regex match removes the need for that
                     # unreliable tie-break entirely. See
                     # doc/INTENT_GAP_ANALYSIS.md.
                     r"my\s+department.{0,20}(currently\s+)?active",
                     r"is\s+my\s+department"),),
        # "which\s+department" is a broad opener that otherwise swallows
        # aggregation questions too — "Which department has the most/least
        # returns assigned?" was matching THIS rule (tied on score with
        # DEPARTMENT_LIST below and resolved by list position), producing a
        # garbage extracted "department name" of "has the most returns
        # assigned" instead of routing to DEPARTMENT_LIST's own most/fewest
        # aggregation branch. A sentence naming most/fewest/maximum/minimum/
        # top-N returns is unambiguously an aggregation query, never a
        # single-department profile lookup.
        excludes=(_kw(r"most\s+returns?", r"fewest\s+returns?", r"least\s+returns?",
                     r"maximum\s+returns?", r"minimum\s+returns?", r"top\s+\d+",
                     r"few\s+returns?", r"some\s+returns?", r"several\s+returns?",
                     # Same no-returns/ambiguous-quantity synonyms DEPARTMENT_LIST's
                     # own rule recognizes — a singular "which department has zero/
                     # no/without any returns" is exactly as much an aggregation
                     # query as "which departments have no returns" (plural), but
                     # this rule's broad "which department" opener was still
                     # swallowing the singular phrasing first, extracting the
                     # whole clause ("has zero returns assigned") as if it were a
                     # department name.
                     r"no\s+returns?", r"zero\s+returns?", r"without\s+any\s+returns?",
                     r"no\s+assigned\s+returns?",
                     r"don'?t\s+have\s+any\s+returns?", r"doesn'?t\s+have\s+any\s+returns?",
                     r"do\s+not\s+have\s+any\s+returns?", r"does\s+not\s+have\s+any\s+returns?"),),
    ),

    _KeywordRule(
        Intent.DEPARTMENT_LIST, ("system_wide",),
        all_of=(_G_DEPT_NOUN,),
        # "maximum"/"minimum"/"top N" were already recognised one layer
        # deeper by _DEPARTMENT_QUERY_TYPE_PATTERNS (the "most"/"fewest"
        # query_type patterns already match "maximum returns?"/"minimum
        # returns?"), but that table is only ever consulted AFTER this rule
        # has already decided the intent is DEPARTMENT_LIST — so a query
        # using only "maximum"/"minimum"/"top N" (no bare "most"/"fewest"/
        # "least" word) never reached DEPARTMENT_LIST at all. Added here so
        # the two layers agree on what counts as an aggregation trigger.
        any_of=(_G_LIST_VERB, _G_HOW_MANY, _G_ACTIVE, _G_INACTIVE, _G_ALL,
                 _kw(r"most", r"fewest", r"least", r"no\s+returns",
                     r"maximum", r"minimum", r"top\s+\d+",
                     r"few\s+returns?", r"some\s+returns?", r"several\s+returns?",
                     r"zero\s+returns?", r"without\s+any\s+returns?", r"no\s+assigned\s+returns?",
                     r"don'?t\s+have\s+any\s+returns?", r"doesn'?t\s+have\s+any\s+returns?",
                     r"do\s+not\s+have\s+any\s+returns?", r"does\s+not\s+have\s+any\s+returns?")),
        # "complete list of returns FOR DEPARTMENT X" names a SPECIFIC
        # department (DEPT_FULL_RETURN_LIST's territory) — this rule's own
        # "complete list of" trigger (_G_ALL) would otherwise steal it and
        # answer with a plain department listing instead, silently ignoring
        # the named department and the fact that RETURNS, not departments,
        # were actually asked for.
        # "which RETURN is accessible by the maximum number of
        # departments" / "which returns are accessible by all
        # departments" ask about RETURNS (DEPT_RETURN_ACCESS_MATRIX's
        # territory) — not a department listing/count, even though
        # "departments" + "all"/"number of" also satisfy this rule's groups.
        # "submission schedule/reporting calendar FOR RETURN X across all
        # departments" asks about ONE named return's own schedule (which
        # is the same regardless of department — NEXT_REPORTING_DATE's
        # territory) — "across all departments" here is only a scope
        # qualifier ("show me this for every department"), not a request
        # to list/count departments, even though it satisfies this rule's
        # groups on the literal words "all"/"departments".
        excludes=(_kw(r"\bmy\b", r"returns?\s+for\s+department", r"returns?\s+for\s+dept",
                     r"returns?\s+.{0,10}accessible\s+by\s+(the\s+)?(maximum|most)",
                     r"returns?\s+.{0,15}accessible\s+by\s+all\s+departments?",
                     r"(schedule|calendar)\s+for\s+return\b.{0,40}\bdepartments?\b",
                     r"overdue"),),
    ),

    # ── ROLE ─────────────────────────────────────────────────────────────

    _KeywordRule(
        Intent.ROLE_PEER_COUNT, ("self",),
        all_of=(_kw(r"how\s+many", r"other"), _kw(r"same\s+role", r"share.*role")),
        # Without this, USER_LIST's generic "user-noun + how-many" rule
        # ties on score (both satisfy 2 groups) and wins the tie by being
        # defined earlier in the rule list — "how many other users share
        # the same role as me" was resolving to a plain system-wide user
        # count instead of this intent's own peer-count answer.
        priority=1,
    ),

    _KeywordRule(
        Intent.ROLE_PROFILE, ("self", "role"),
        all_of=(_G_ROLE_NOUN,),
        any_of=(_kw(r"my", r"i\s+have", r"i\s+am\s+assigned", r"am\s+i\s+assigned",
                     r"do\s+i\s+have", r"assigned\s+to\s+me",
                     # Non-self-referential ID lookups — "what is the role
                     # ID for Tester?" / "what is the name of role ID 106?"
                     # — previously unmatched entirely (every other any_of
                     # alternative here requires self-reference).
                     r"role\s+id\s+(for|of)", r"name\s+of\s+role\s+id",
                     # A bare "role id <number>" appearing anywhere is a
                     # reliable, order-independent signal on its own —
                     # covers verbose/redundant phrasings like "the name of
                     # role of role ID 101" that the more specific patterns
                     # above (which expect the id-lookup phrase immediately
                     # adjacent to "role") don't match.
                     r"role\s+id\s+\d+"),),
        # "is there a role called X"/"does role X exist" are existence
        # checks -> ROLE_LIST(query_type=exists), not ROLE_PROFILE; excluded
        # here so that rule (lower in this list, same all_of group) wins.
        excludes=(_kw(r"is\s+there\s+a\s+role", r"\bexist\w*\b"),),
    ),

    _KeywordRule(
        Intent.ROLE_USERS, ("role",),
        all_of=(_G_ROLE_NOUN, _G_USER_NOUN),
        any_of=(_kw(r"assigned", r"have", r"has", r"with", r"how\s+many", r"belong\w*"), _G_LIST_VERB, _G_HOW_MANY),
        # "which ROLE has the most users" / "roles ... number of users in
        # each" are aggregation questions across ALL roles (ROLE_LIST's
        # territory) — without this exclude they tied on score with (and
        # by list position lost to) this rule, extracting garbage like
        # target_role="has the most users". A self-referential "how many
        # OTHER users share the same role AS ME" is ROLE_PEER_COUNT's
        # question, never "which users have role X" — excluded here too
        # rather than relying on score alone, since both rules can satisfy
        # the same all_of/any_of groups for that phrasing.
        excludes=(_kw(r"most\s+users?", r"least\s+users?", r"fewest\s+users?",
                     r"minimum\s+users?", r"maximum\s+users?",
                     r"smallest\s+role", r"largest\s+role", r"biggest\s+role",
                     r"least[\s-]?used\s+role",
                     r"number\s+of\s+users\s+in\s+each",
                     r"\bmy\s+role\b", r"share.{0,20}role", r"as\s+me\b",
                     # A question about MODULES/PERMISSIONS/CONTROL for a
                     # role (e.g. "which modules does the Admin User role
                     # have full control over?") is never actually asking
                     # to list the role's users — but it can still
                     # structurally satisfy this rule's groups whenever the
                     # role's own NAME happens to contain the word "User"
                     # (e.g. "Admin User"), so that alone can't be trusted.
                     r"\bmodules?\b", r"permissions?", r"full\s+control"),),
    ),

    _KeywordRule(
        Intent.ROLE_LIST, ("system_wide",),
        all_of=(_G_ROLE_NOUN,),
        any_of=(_G_LIST_VERB, _G_HOW_MANY, _G_ACTIVE, _G_INACTIVE, _G_ALL,
                 _kw(r"most\s+users", r"largest", r"biggest",
                     r"least\s+users?", r"fewest\s+users?", r"minimum\s+users?",
                     r"maximum\s+users?", r"smallest\s+role", r"least[\s-]?used\s+role",
                     r"is\s+there\s+a\s+role", r"exist\w*", r"valid\s+role",
                     r"number\s+of\s+users\s+in\s+each")),
        # A specific NAMED role ("role Tester") means the question is about
        # THAT role (ROLE_MODULE_ACCESS/PERMISSION_PROFILE's territory, e.g.
        # "list all modules accessible to role Tester"), never a system-wide
        # aggregate over every role — this rule's broad list-verb/how-many
        # triggers otherwise tie with (and, by list position, beat) the more
        # specific rule for that phrasing. "is there a role CALLED X" is
        # exempt (lowercase "called", not a capitalized name right after
        # "role") since that idiom belongs to this rule's own exists branch.
        excludes=(_kw(r"\bmy\b"), re.compile(r"\brole\s+[A-Z]\w*")),
    ),

    # ── ROLE_ACCESS ──────────────────────────────────────────────────────

    _KeywordRule(
        Intent.ROLE_PERMISSION_DIFF, ("role",),
        all_of=(_kw(r"difference", r"differ\w*", r"compare\w*", r"vs\.?", r"versus"),
                 _kw(r"permission\w*", r"access", r"role\w*")),
    ),

    _KeywordRule(
        Intent.ROLES_WITH_PERMISSION, ("system_wide",),
        # "who" (without the literal word "role") also counts as the
        # role-noun signal — "who can approve bank details?" is just as
        # much a roles-with-permission question as "which roles can
        # approve bank details?", but self-test found it required the
        # word "role" and fell through to BANK_INFO's loose
        # "bank...detail" pattern instead (a "detail(s)" module reference
        # colliding with BANK_INFO's own-bank-profile phrasing). Requiring
        # this to co-occur with a permission verb (the second all_of
        # group) keeps it from misfiring on a genuine "who is my bank
        # contact"-style question, which wouldn't mention create/edit/
        # view/approve/access at all.
        all_of=(_kw(r"roles?", r"\bwho\b"),
                 _kw(r"create", r"edit", r"view", r"approve", r"access",
                     # "upload" ported from the my-nlp-changes branch: EXEMPLARS
                     # already carried "Which roles can upload Non-XBRL files?" but no
                     # verb here matched it, so it never reached this rule via regex.
                     # intent_classifier.ACTION_MAP/role_handlers._ACTION_MAP map
                     # "upload" -> HasNew, so the handler resolves it.
                     r"full\s+access", r"no\s+edit", r"no\s+create", r"upload")),
        any_of=(_kw(r"which", r"what", r"can", r"have", r"who"),),
        # A NAMED role directly adjacent to the permission verb ("the admin
        # role CREATE", "checker role APPROVE" — no "can" in between) means
        # this is a role-SCOPED question (PERMISSION_CHECK's job — check
        # what a specific role can do), not "which roles (system-wide) can
        # do X". Self-test: "what modules can the admin role create?" was
        # landing here with target_role='admin' extracted but silently
        # discarded (this handler never reads target_role at all), instead
        # of PERMISSION_CHECK correctly checking role='admin' specifically.
        # Deliberately requires the verb immediately after "role(s)" (no
        # "can" between) so genuine system-wide phrasing like "which roles
        # CAN create roles?" (role/roles separated from the verb by "can")
        # still reaches this rule.
        excludes=(_kw(r"\bmy\b", r"\bi\b"), _NamedRoleActionPattern(), _NamedRoleAccessPattern()),
    ),

    _KeywordRule(
        Intent.ROLE_MODULE_ACCESS, ("role", "system_wide"),
        all_of=(_kw(r"module\w*", r"sdmx", r"cross-?validation", r"nxquerybuilder",
                     r"balance\s+sheet", r"data\s+preparation", r"audit\s+log",
                     r"provider\w*", rf"{_NON_XBRL}\s+upload", r"maker-?checker"),),
        any_of=(_kw(r"access\w*", r"role\w*"),),
        # Same PERMISSION_CHECK carve-out as ROLES_WITH_PERMISSION above:
        # "modules can the admin role create" names a role AND a specific
        # action verb — ROLE_MODULE_ACCESS's handler ignores the verb
        # entirely and would return every module the role can touch in ANY
        # way (view/edit/approve/create all lumped together), not
        # specifically what it can create.
        excludes=(_kw(r"\bmy\b", r"\bcan\s+i\b"), _NamedRoleActionPattern()),
    ),

    _KeywordRule(
        Intent.PERMISSION_CHECK, ("self", "role"),
        all_of=(_kw(r"can\s+i", r"can\s+(the\s+)?role",
                     # Reversed word order — the role NAME sits between
                     # "the" and "role" ("can the Tester role edit...")
                     # rather than right after "role" ("can role Tester
                     # ..."). Both orderings mean the same thing. Ported
                     # from my-nlp-changes; supersedes the narrower
                     # "can (the) (\w+ )?role" (one intervening word only)
                     # by allowing multi-word role names ("the Admin User
                     # role").
                     r"can\s+(the\s+)?\w+(?:\s+\w+){0,2}\s+role\b",
                     r"am\s+i\s+allowed", r"am\s+i\s+able\s+to",
                     r"do\s+i\s+have\s+(the\s+)?(permission|right|access)\s+to",
                     r"do\s+i\s+have\s+approval\s+rights?"),
                 _kw(r"create", r"edit", r"update", r"modify", r"view", r"see",
                     r"approve", r"add", r"upload", r"access", r"disable",
                     r"delete", r"run", r"generate", r"do", r"manage", r"perform")),
        # "How many returns can I access in total?" (a MY_RETURN_ACCESS
        # exemplar, department module) matched this rule's "can I" + "access"
        # combo before ever reaching MY_RETURN_ACCESS's own pattern — a
        # pre-existing collision the department-module accuracy pass
        # uncovered (this exemplar was never actually verified against tier-1
        # regex before). A quantity/summary framing ("how many ... in total")
        # is never a genuine permission-check question in this taxonomy's
        # existing exemplars, so this exclusion is safe generically, not just
        # for the one phrasing that surfaced it.
        #
        # "Can I see the full reporting calendar for return X?" / "Can I
        # download the report for my last submission of return X?" are
        # XBRL-module self-service questions about a RETURN's own data
        # (reporting calendar / submission report), not a role/menu
        # permission question, even though they also match "can I" + "see"/
        # "download"("access" via a broader verb list would too).
        #
        # Naming a return TYPE ("what non-XBRL returns am I able to access?")
        # asks for RETURNS, not for the caller's role/menu permissions — the
        # same carve-out PERMISSION_PROFILE below already carries. It matters
        # here now that "am i allowed"/"am i able to" are triggers: both
        # phrasings pair naturally with "access", so a return-type question
        # satisfies this rule's groups just as well as a module one does.
        excludes=(_kw(r"how\s+many", r"in\s+total",
                     r"reporting\s+calendar", r"report\s+for\s+my", r"download.{0,20}report",
                     r"report\s+ready\s+for\s+my\s+submission", r"reporting\s+schedule",
                     rf"{_NON_XBRL}\s+returns?", r"\bxbrl\s+returns?\b"),),
    ),

    _KeywordRule(
        Intent.PERMISSION_PROFILE, ("self", "role"),
        all_of=(_kw(r"permission\w*", r"access\w*", r"modules?\s+am\s+i\s+allowed",
                     r"not\s+have\s+access", r"full\s+control", r"control\s+over"),),
        any_of=(_kw(r"my", r"i\s+have", r"do\s+i\s+have", r"what\s+can\s+i",
                     r"role\w*",
                     # Narrow, not a bare "\bi\b" (which stole unrelated
                     # self-referential "access" questions like "What
                     # returns am I entitled to access?" — MY_RETURN_
                     # ACCESS's territory, not this intent's).
                     r"what\s+do\s+i"),),
        excludes=(
            _kw(r"\bcan\s+i\b"),  # PERMISSION_CHECK owns "can I ..."
            # "access\w*" also matches "accessible"/"accessing" etc, which
            # made this rule swallow department-returns phrasings like "Show
            # me the returns accessible to my department." (another
            # pre-existing collision this pass's testing uncovered, not
            # introduced by the DEPARTMENT_RETURNS regex trim). A sentence
            # mentioning both "return(s)" and "department" together is
            # squarely DEPARTMENT_RETURNS' territory, never a genuine
            # permission-profile question, regardless of word order.
            re.compile(r"(?=.*\breturns?\b|.*\bforms?\b|.*\breports?\b)(?=.*\bdepartments?\b)", re.IGNORECASE),
            # "how many [non-xbrl] returns do I have access to" is a
            # RETURN-count question (NONXBRL_RETURN_LIST/MY_RETURN_ACCESS
            # territory), not a role/menu permission question, even though
            # it also satisfies "access" + "do i have".
            _kw(r"how\s+many\s+.{0,20}returns?\s+.{0,10}(access|submit)"),
            # Same reasoning one level more general: naming a return TYPE
            # ("what are the non-XBRL returns I have access to?", "list the
            # XBRL returns I can access") asks for RETURNS, not for the
            # caller's role/module permissions — the previous exclude only
            # covered the "how many" counting framing, so the equally
            # common "what are"/"give me a list of" framings still landed
            # here and answered with the permission matrix.
            _kw(rf"{_NON_XBRL}\s+returns?", r"\bxbrl\s+returns?\b"),
        ),
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


# An InstanceLog row's Id — a 32-char hex GUID, dashed or not (e.g.
# "f7593ff72d644345865eaa84ae0b3073" or the dashed 8-4-4-4-12 form). This
# is what a generate-instance call now echoes back to the user (see
# _find_new_instance_log_id in agent/__init__.py) and what SUBMISSION_STATUS
# needs to recognise even with no literal "submission" word in the
# question ("what is the status of <id>"). Kept as a plain string
# fragment (not compiled) so it can be embedded inside _mk()'s raw
# pattern strings; _INSTANCE_ID_RE below is the compiled form used
# directly by callers outside this module (e.g. decide()'s workflow gate).
_INSTANCE_ID_PATTERN = r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32})"
_INSTANCE_ID_RE = re.compile(_INSTANCE_ID_PATTERN, re.IGNORECASE)


def _mk(intent: Intent, target_types: tuple[str, ...], *patterns: str):
    return (intent, target_types, [re.compile(p, re.IGNORECASE) for p in patterns])


# Every reporting-frequency word/synonym a RETURNS_BY_FREQUENCY phrasing
# might use — kept as one alternation so every trigger pattern below stays
# in sync automatically as synonyms are added (PERIOD_ALIASES, used for
# the actual period_name EXTRACTION, must be kept in sync with this list
# by hand since it's a dict of many-to-one mappings, not an alternation).
_FREQ_WORD = (
    r"(?:daily|day|weekly|week|monthly|month|quarterly|quarter|"
    r"semi[\s-]?annual(?:ly)?|half[\s-]?yearly|"
    r"annual(?:ly)?|yearly|year|"
    r"fortnightly|bi[\s-]?weekly|bi[\s-]?monthly)"
)

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
        r"\bnotifications?\b(?!.{0,30}\bdays?\b)", r"\bsms\s+(reminder|enabled)\b",
        # "advance notification(s)" alone is this intent's own territory
        # (SMS/email reminder config for a return), but "advance
        # notification DAYS/PERIOD" is the PERIOD module's configured
        # lead-time field (PERIOD_LOOKUP/PERIOD_LIST) — a completely
        # different concept that happens to share the same two leading
        # words. The negative lookahead (scanning the next ~30 chars,
        # since "days" can be separated by "period greater than N ")
        # keeps this rule from shadowing every PERIOD question that
        # mentions advance notification days/period.
        r"\badvance\s+notifications?\b(?!.{0,30}\bdays?\b)"),

    # ── XBRL_RETURNS / NON_XBRL_RETURNS / PERIOD / DEPT_RETURN_MAPPING ──
    # RETURNS_BY_FREQUENCY: covers both question-word-first phrasing
    # ("which returns are filed monthly") and the reversed/no-question-word
    # phrasing real users type ("returns filed quarterly", "quarterly
    # returns", "returns that follow a quarterly reporting schedule"). The
    # bare "<freq> returns?" pattern is guarded on both sides — a negative
    # lookbehind for a preceding "for " (so "...given for Quarterly
    # returns" — a PERIOD_LOOKUP notification-days question — isn't stolen
    # here) and a negative lookahead for a nearby "notification" — so it
    # only fires for the genuine "list returns of this frequency" framing.
    _mk(Intent.RETURNS_BY_FREQUENCY, ("self", "system_wide"),
        rf"\bwhich\s+returns?\s+are\s+filed\s+(on\s+a\s+)?{_FREQ_WORD}\b",
        rf"\breturns?\s+(that\s+are\s+|are\s+)?filed\s+(on\s+a\s+)?{_FREQ_WORD}\b",
        # "returns filed every year/quarter/month/..." — "every" here
        # means the same as the adjective form ("filed every year" ==
        # "filed yearly"), not a literal frequency word by itself.
        r"\breturns?\s+filed\s+every\s+(day|week|fortnight|month|quarter|half\s+year|year)\b",
        # "Which returns are annual?" / "Show returns that are quarterly" —
        # no "filed" at all, just a plain adjective after "are".
        rf"\breturns?\s+are\s+{_FREQ_WORD}\b",
        rf"\breturns?\s+(that\s+)?follow\w*\s+an?\s+{_FREQ_WORD}\s+(reporting\s+)?schedule\b",
        # "Returns with a quarterly frequency" / "returns that have a
        # monthly frequency" — the frequency word is now a noun modifier
        # of "frequency" itself, not adjacent to "returns" or "filed".
        rf"\breturns?\s+(that\s+)?(have|with)\s+(a\s+)?{_FREQ_WORD}\s+frequenc\w*\b",
        # "<freq> returns" / "<freq> reporting returns" — the optional
        # "reporting" infix covers phrasings like "annual reporting
        # returns" without loosening the guard rails below (a preceding
        # "for " or a nearby "notification" still route elsewhere, e.g.
        # "advance notification days given for Quarterly returns").
        rf"(?<!for\s){_FREQ_WORD}\s+(reporting\s+)?returns?\b(?!.{{0,15}}\bnotification\b)"),
    # RETURN_FIELD is checked BEFORE PERIOD_LOOKUP/PERIOD_LIST so a
    # return-scoped question like "what is the reporting frequency of
    # CIMS_ROR" (asking about ONE return) doesn't fall through to the
    # system-wide period intents (which dump every configured period,
    # ignoring the return name entirely).
    _mk(Intent.RETURN_FIELD, ("return",),
        r"\breturn\s+id\s+(for|of)\b", r"\binternal\s+form\s+id\s+(for|of)\b",
        # Negative lookahead excludes "due period OF MORE THAN 21 days" —
        # an aggregate threshold question about MANY returns (RETURN_LIST's
        # due_gt query_type), not a single named return's own period/
        # frequency field, even though it also contains the literal
        # substring "period of".
        r"\b(reporting\s+)?(period|frequency)\s+(for|of)\s+(?!more\s+than\b|greater\s+than\b)(the\s+)?(return|form|report)?\s*\S",
        r"\bwhat\s+(period|frequency)\s+is\b.{0,40}\breturn\b",
        r"\bhow\s+often\s+is\b.{0,40}\bfiled\b",
        r"\breport\s+formats?\b.{0,40}\bfor\s+return\b",
        r"\bwhat\s+formats?\s+are\s+(supported|available)\s+for\s+return\b"),
    # PERIOD_LOOKUP: single-period/EBR-code field lookups (id/name/EBR
    # code/notification-days for one named period), the QF-vs-QAD-style
    # comparison between two periods, the "greater than N days"/"no
    # notification days configured" aggregate checks, and (self-scoped)
    # the "my personal reporting calendar"/"my report due dates" framing —
    # all grouped under this one intent because every phrasing here reads
    # a period/frequency's own fields; only the actual RETURN listing
    # ("which returns are filed quarterly") belongs to RETURNS_BY_FREQUENCY
    # instead.
    _mk(Intent.PERIOD_LOOKUP, ("self", "system_wide"),
        r"\bperiod\s+(name|id)\s+for\b", r"\bperiod\s+id\s+represents?\b",
        r"\bwhich\s+period\s+id\s+represents?\b",
        r"\bebr\s+frequency\s+code\b",
        r"\badvance\s+notification\s+days?\b.{0,20}\bfor\b",
        r"\bdifference\s+between\b.{0,60}\bfrequenc\w*\b",
        r"\bcompare\b.{0,60}\bfrequenc\w*\b",
        r"\badvance\s+notification\s+(period|days?)\s+greater\s+than\b",
        r"\bno\s+advance\s+notification\s+days?\s+configured\b",
        r"\bwithout\s+(any\s+)?advance\s+notification\b",
        r"\bpersonal\s+reporting\s+calendar\b", r"\breporting\s+calendar\s+for\s+(this|next)\s+year\b",
        r"\bcalendar\s+view\b.{0,30}\bdue\s+dates?\b", r"\breport\s+due\s+dates?\b"),
    _mk(Intent.PERIOD_LIST, ("system_wide",),
        r"\ball\s+(the\s+)?(reporting\s+)?periods?\b",
        # Negative lookahead excludes "returns had their reporting
        # frequency CHANGED (in the last N months)" — a change-history
        # question this system has no audit trail to answer (Returns.xml
        # metadata edits aren't logged anywhere), not a request to list
        # the configured periods/frequencies. Falling through to "none"
        # for that phrasing is the honest answer; dumping the period list
        # would just be a wrong-shaped non-answer.
        r"\breporting\s+frequenc\w*\b(?!\s+changed)",
        r"\bhow\s+many\s+(reporting\s+)?frequenc\w*\b", r"\bperiods?/frequenc\w*\s+(defined|are)\b",
        r"\bshare\s+the\s+same\s+(reporting\s+)?(schedule|frequenc\w*)\b",
        r"\bsame\s+reporting\s+(schedule|frequenc\w*)\b",
        r"\bfull\s+annual\s+reporting\s+calendar\b", r"\breporting\s+calendar\s+across\s+all\s+frequenc\w*\b",
        r"\b(period|frequenc\w*)\b.{0,10}\bhas\s+the\s+most\s+returns\b",
        r"\bmost\s+returns?\s+scheduled\s+under\b", r"\bmost\s+returns?\s+assigned\b",
        r"\b(period|frequenc\w*)\b.{0,40}\bhighest\s+number\s+of\s+returns\b",
        r"\b(period|frequenc\w*)\b.{0,40}\bused\s+by\s+the\s+maximum\s+(number\s+of\s+)?returns?\b"),
    _mk(Intent.RETURNS_SUBMITTABLE_BY_DEPT, ("self", "department", "return"),
        # "submit"/"generate"/"create"/"file" are all synonyms end users use
        # interchangeably for filing a return (same synonym set already
        # documented for REPORTS_FILED_IN_RANGE below) — the original
        # version of this rule only recognised the literal word "submit",
        # so "which XBRL returns can I generate" (or "reports", or "list
        # of ... which I can generate") fell through to the SQL Agent
        # entirely instead of reaching this intent. Self-test:
        # "get me list of xbrl reports which i can generate".
        rf"\bwhich\s+xbrl\s+returns?\s+can\s+i\s+{_RETURN_SUBMIT_VERBS}\b",
        rf"\bwhich\s+departments?\s+can\s+{_RETURN_SUBMIT_VERBS}\b",
        rf"\bxbrl\s+returns?\b.{{0,15}}\bi\s+can\s+{_RETURN_SUBMIT_VERBS}\b",
        rf"\bxbrl\s+reports?\b.{{0,20}}\bi\s+can\s+{_RETURN_SUBMIT_VERBS}\b",
        rf"\blist\s+of\s+xbrl\s+reports?\b.{{0,30}}\bi\s+can\s+{_RETURN_SUBMIT_VERBS}\b"),
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
        r"\bupcoming\s+(returns?|reports?|forms?)\b", r"\bwhat\s+.{0,40}\bupcoming\s+next\s+month\b",
        # "upcoming due dates in the next N days" / "due in the next N
        # days" — a rolling window (today -> today+N), not a fixed
        # "between X and Y" span, but still the same "next due date falls
        # in this window" computation.
        r"\bupcoming\s+due\s+dates?\s+in\s+the\s+next\s+\d+\s+days?\b",
        r"\bdue\s+in\s+the\s+next\s+\d+\s+days?\b",
        r"\bdue\s+(this|next|current)\s+month\b",
        r"\bhow\s+many\s+returns?\s+are\s+due\s+this\s+month\b",
        # "are any of my returns overdue" / "which returns are overdue for
        # submission" — no date range at all; the "overdue" query_type
        # below drives the computation (next due date already passed AND
        # not yet filed) instead of a window match.
        r"\bare\s+any\s+of\s+my\s+returns?\s+overdue\b",
        r"\breturns?\s+(that\s+are\s+|are\s+)?overdue\b",
        r"\boverdue\s+returns?\b", r"\boverdue\s+for\s+submission\b",
        # "what is my next [non-]XBRL return due?" — the single soonest
        # upcoming due date across everything the caller can access. The
        # type word and "due" must sit DIRECTLY around "return(s)": that
        # adjacency is what keeps this from stealing NEXT_REPORTING_DATE's
        # named-return form ("when is my next Non-XBRL return BSR1
        # (Quarterly) due?"), where the name always intervenes. Checked
        # here rather than in NONXBRL_RETURN_LIST because "next ... due" is
        # a date computation over the accessible set, not a listing — LIST
        # previously matched these on its bare "non-XBRL return(s)" trigger
        # and answered with the whole access list.
        rf"\bnext\s+(?:{_NON_XBRL}\s+|xbrl\s+)?returns?\s+(?:is\s+|has\s+|that\s+is\s+|which\s+is\s+)?due\b",
        rf"\bnext\s+due\s+(?:{_NON_XBRL}\s+|xbrl\s+)?returns?\b",
        rf"\b(?:{_NON_XBRL}\s+|xbrl\s+)?returns?\s+(?:is\s+)?due\s+next\b"),
    # MONTHLY_FILING_STATUS: "what's my [XBRL|non-XBRL] filing status for
    # <month>" and "what dates are [XBRL|non-XBRL] reports expected in
    # <month>" — a SINGLE-month roll-up (filed vs not-filed per return),
    # distinct from REPORTS_FILED_IN_RANGE/REPORTS_UPCOMING_IN_RANGE's
    # explicit two-date "between X and Y" span. Checked AFTER those two so
    # a genuine "between X and Y"/"from X to Y" range question (which also
    # contains a month name inside its date tokens) is never miscaught
    # here first — _NEW_RULES tries rules in list order and stops at the
    # first match, so ordering IS the disambiguation mechanism.
    _mk(Intent.MONTHLY_FILING_STATUS, ("self", "department", "system_wide"),
        r"\b(filing\s+status|status)(?:\s+\S.{0,30})?\s+(for|in|during)\b.{0,40}"
        r"\b(month|20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
        r"\bwhat.?s\s+(my|the)\b.{0,40}\bstatus(?:\s+\S.{0,30})?\s+(for|in|during)\b",
        # "my/our [XBRL|non-XBRL] filing for <month>" — "filing" with NO
        # "status" word, but anchored to a self-referential possessive
        # ("my"/"our") immediately before it, which single-report generate/
        # schedule requests naming a specific return never use (those name
        # the report, e.g. "generate CIMS_RAQ filing for 31 march 2026" —
        # no "my/our" directly before "filing"). Narrower than a bare
        # \bfiling\b so it doesn't hijack those.
        r"\b(my|our)\s+(xbrl\s+|non[\s-]?xbrl\s+|nx\s+)?filing\s+(for|in|during)\b.{0,40}"
        r"\b(month|20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
        r"\bstatus\s+(for|of|in)\s+(this|current|last|previous|next)\s+month\b",
        r"\bwhat\s+dates?\s+are\b.{0,40}\bexpected\s+in\b",
        r"\b(reports?|returns?|forms?)\b.{0,20}\bexpected\s+(in|during|for)\b",
        r"\bfiling\s+status(?:\s+\S.{0,30})?\s+(for|in|during)\b"),
    _mk(Intent.NEXT_REPORTING_DATE, ("return",),
        r"\bnext\s+report(ing)?\s+date\b", r"\bnext\s+due\s+date\b",
        r"\bwhen\s+is\b.{0,55}\bdue\b", r"\bwhen\s+(is|does)\b.{0,55}\bnext\s+(report|reporting|submission|due)\b",
        r"\bwhen\s+(should|do)\s+i\s+(submit|file|report)\b", r"\bdue\s+date\s+for\b",
        r"\bnext\s+period[\s-]?end\b", r"\bhow\s+many\s+days?\s+(are\s+)?left\s+before\b.{0,40}\bdue\b",
        # "submission schedule for return X (across all departments/for
        # my returns this year)" — the schedule is a property of the
        # RETURN's own frequency, identical regardless of department, so
        # this reduces to the same next-reporting/due-date computation.
        r"\bsubmission\s+schedule\s+for\s+return\b",
        r"\bwhen\s+is\s+the\s+next\s+due\s+date\s+for\s+return\b",
        # "reporting calendar for return X (for the current year)" / "can
        # I see the full reporting calendar for return X" — every
        # occurrence within a year, not just the single next one, but
        # still the same underlying return-frequency computation
        # (query_type="calendar" tells the handler to enumerate instead
        # of returning just the next occurrence).
        r"\breporting\s+calendar\s+for\s+return\b",
        r"\bfull\s+reporting\s+calendar\s+for\s+return\b"),
    _mk(Intent.RETURN_PROFILE, ("return",),
        r"\btaxonomy\s+(version|does)\b", r"\bxsd\s+path\b",
        r"\bdue\s+days?\s+.*submission\s+of\s+return\b", r"\balternate\s+name\s+for\s+return\b",
        # Existence check for a named return — "is there a return called X",
        # "is X a return", "does return X exist" — previously unhandled
        # entirely (fell through to SQL Agent / LLM fallback; see
        # doc/INTENT_GAP_ANALYSIS.md, gap "RETURN_LIST/RETURN_PROFILE not
        # matched for casual existence phrasing"). Deliberately loose on the
        # return-name side (captured by the entity extractor downstream from
        # the whole message, same as other RETURN_PROFILE phrasings) —
        # this pattern only needs to recognise the QUESTION shape.
        r"\bis\s+there\s+a\s+returns?\s+(called|named)\b",
        r"\bdoes\s+(a\s+|the\s+)?returns?\b.{0,30}\bexist\b",
        r"\bis\b.{0,30}\ba\s+returns?\b",
        # "give me the full profile for DBR01" / "profile of CIMS_ROR" — the
        # word "return" is often absent entirely (the user names the return
        # code directly), which is exactly why USER_PROFILE's bare "profile"
        # keyword rule used to win first (now excluded above when a
        # return-code-shaped token is present). This pattern only needs the
        # QUESTION shape; the entity extractor resolves the actual return
        # name from the full message, same as every other RETURN_PROFILE
        # phrasing above.
        r"\bprofile\s+(for|of)\b",
        # "whats dpss 09 about" — tightened to require a return-code-shaped
        # token (letters + 2+ digits) directly after "what's/what is", so
        # this doesn't also swallow unrelated small talk like "what's the
        # weather about".
        r"\bwhat.?s?\s+(is\s+)?[a-z]+\s*\d{2,}\s+about\b",
        r"\btell\s+me\s+about\s+return\b"),
    # Ordered BEFORE RETURN_LIST deliberately (_NEW_RULES is first-match-
    # wins by list position). RETURN_LIST's word-order-tolerant CIMS
    # patterns from the ChatBot_5.5-test branch
    # (r"\breturns?\b.{0,25}\bcims[\s-]?enabled\b") are broad enough to also
    # match a question naming ONE non-XBRL return -- "is non xbrl return
    # BSR1(Quarterly) CIMS-enabled?" -- which must reach this rule, not the
    # system-wide list. Handled by ordering rather than by narrowing those
    # patterns, so the generic "which returns are CIMS enabled" phrasing
    # they were added for keeps working exactly as before.
    # NONXBRL_RETURN_PROFILE owns every question about ONE NAMED non-XBRL
    # return's own fields (period/frequency, due days, CIMS flag, job
    # processing id, report format/schedule/generation-status framings —
    # all of which this system tracks as fields on the single return row,
    # not a separate per-field intent the way XBRL_RETURNS split RETURN_
    # FIELD out from RETURN_PROFILE). Checked BEFORE NONXBRL_RETURN_LIST
    # so a named-return question doesn't get stolen by LIST's much broader
    # bare "non-XBRL return(s)" trigger below, which would otherwise catch
    # every single-return phrasing too (they all contain that literal
    # phrase) and answer with the full unfiltered list instead.
    _mk(Intent.NONXBRL_RETURN_PROFILE, ("self", "return"),
        rf"\bbase\s+(file\s+)?template\s+for\s+{_NON_XBRL}\b", r"\bjob\s+processing\s+id\b",
        rf"\bperiod/frequency\s+of\s+{_NON_XBRL}\b", rf"\bperiod\s+or\s+frequency\s+of\s+{_NON_XBRL}\b",
        rf"\bhow\s+many\s+due\s+days?\s+does\s+{_NON_XBRL}\b",
        rf"\bis\s+{_NON_XBRL}\s+return\b.{{0,40}}\bcims[\s-]?enabled\b",
        rf"\breport\s+generation\s+status\s+for\s+{_NON_XBRL}\s+return\b",
        rf"\breporting\s+schedule\s+for\s+{_NON_XBRL}\s+return\b",
        rf"\breporting\s+schedule\s+for\s+{_NON_XBRL}\b",
        rf"\breport\s+formats?\s+.{{0,20}}(supported|available)\s+for\s+{_NON_XBRL}\s+return\b",
        rf"\breport\s+format\s+does\s+{_NON_XBRL}\s+return\b.{{0,20}}\buse\b",
        rf"\breport\s+ready\s+for\s+my\s+{_NON_XBRL}\s+submission\s+of\b",
        # Conversational "tell me about / details of / show me the non-XBRL
        # return <name>" — the type word is followed by "return <name>",
        # i.e. a NAME, which is what separates it from LIST's bare "non-XBRL
        # returns" (plural, nothing after it). Without this, every casual
        # single-return phrasing fell through to LIST and answered with the
        # whole catalogue.
        rf"\b(?:tell\s+me\s+about|details?\s+(?:of|for|about)|information\s+(?:on|about)|"
        rf"show\s+me|about)\s+(?:the\s+)?{_NON_XBRL}\s+return\s+\S",
        rf"\b{_NON_XBRL}\s+return\s+(?:called|named)\s+\S"),
    _mk(Intent.RETURN_LIST, ("self", "system_wide"),
        r"\ball\s+(the\s+)?xbrl\s+returns?\b", r"\bhow\s+many\s+xbrl\s+returns?\b",
        r"\bwhich\s+xbrl\s+returns?\s+(are|is)\b",
        # "CIMS-enabled returns" (hyphenated, order-fixed) — original pattern,
        # kept for backward compatibility with anything already relying on it.
        r"\bcims-enabled\s+returns?\b",
        # Word-order-tolerant variants: a real user is at least as likely to
        # say "returns are CIMS enabled" / "returns that are CIMS enabled"
        # as the hyphenated noun-phrase form above. Self-test
        # (doc/INTENT_GAP_ANALYSIS.md) found "which returns are CIMS
        # enabled" falling through to the SQL Agent because only the
        # noun-phrase order was covered.
        r"\breturns?\b.{0,25}\bcims[\s-]?enabled\b",
        r"\bcims[\s-]?enabled\b.{0,25}\breturns?\b",
        # Generic casual catch-all — "tell me abt returns pls", "tell me
        # stuff about returns", "gimme info on returns" — self-test found
        # RETURN_LIST had no rule at all for an unqualified, informally-
        # phrased "tell me about returns"-shaped question; it isn't asking
        # for a specific return (that's RETURN_PROFILE, which requires a
        # named target) so it lands on the general list. Deliberately
        # generic word choices ("tell", "about"/"abt") tolerate filler
        # ("me", "pls", "u") since those aren't part of the pattern at all.
        r"\btell\s+me\b.{0,20}\b(abt|about)\s+returns?\b",
        r"\b(info|information)\s+(on|about|abt)\s+returns?\b",
        # ── ported from my-nlp-changes ──────────────────────────────────
        # Redundant CIMS-enabled variants from that branch were dropped: the
        # word-order-tolerant senior patterns above already subsume them.
        # These cover validation-flag / category / due-period / next-N-due-dates
        # framings the senior branch has no rule for at all.
        r"\bwhich\s+returns?\s+(are|use|have)\b.{0,40}\b(cims|table\s+linkbase|istbl|large\s+validator|"
        r"formula\s+validation|schema[\s-]?calc\w*\s+validation|rbi\s+validation)\b",
        r"\ball\s+returns?\s+(along\s+with|with)\s+their\s+due\s+days?\s+and\s+frequenc\w*\b",
        r"\breturns?\s+belong\w*\s+to\s+the\s+(dpss|dbs|dbr)\s+category\b",
        r"\bwhich\s+returns?\s+have\s+a\s+due\s+period\s+of\s+more\s+than\s+\d+\s+days?\b",
        r"\breturns?\s+(with\s+a\s+)?due\s+period\s+(of\s+)?(more|greater)\s+than\s+\d+\s+days?\b",
        r"\ball\s+returns?\s+and\s+their\s+next\s+three\s+upcoming\s+due\s+dates?\b",
        r"\breturns?\s+and\s+their\s+next\s+(three|\d+)\s+(upcoming\s+)?due\s+dates?\b"),
    _mk(Intent.NONXBRL_RETURN_LIST, ("self", "department", "system_wide"),
        rf"\b{_NON_XBRL}\s+returns?\b", rf"\bhow\s+many\s+{_NON_XBRL}\b"),
    _mk(Intent.DEPT_FULL_RETURN_LIST, ("department",),
        r"\bcomplete\s+list\s+of\s+returns?\s+for\s+department\b"),
    _mk(Intent.MY_RETURN_ACCESS, ("self",),
        r"\bwhich\s+returns?\s+does\s+my\s+department\s+have\s+access\b",
        r"\bcomplete\s+list\s+of\s+returns?\s+i\s+can\s+work\s+with\b",
        r"\bhow\s+many\s+returns?\s+can\s+i\s+access\b",
        # More phrasings of the same "total returns I can access" ask —
        # "total number of"/"count of" instead of "how many", or a
        # statement instead of a question ("returns I'm allowed to use").
        r"\btotal\s+number\s+of\s+returns?\s+can\s+i\s+access\b",
        r"\bcount\s+of\s+returns?\s+can\s+i\s+access\b",
        r"\breturns?\s+am\s+i\s+(?:entitled|allowed)\s+to\s+access\b",
        r"\breturns?\s+i(?:'m|\s+am)\s+allowed\s+to\s+use\b"),
    _mk(Intent.DEPT_RETURN_ACCESS_MATRIX, ("system_wide",),
        r"\breturn\s+.*accessible\s+by\s+the\s+(maximum|most)\b",
        r"\breturns?\s+.*accessible\s+by\s+all\s+departments?\b",
        r"\bdepartment\s+has\s+access\s+to\s+the\s+most\s+returns?\b"),

    # ── INSTANCE_LOG ─────────────────────────────────────────────────────
    _mk(Intent.MY_SUBMISSION_HISTORY, ("self",),
        r"\bwhich\s+returns?\s+have\s+i\s+submitted\b", r"\bhave\s+i\s+ever\s+submitted\b",
        # "is the report ready for my submission of X" / "can I download
        # the report for my last submission of X" — both reduce to "show
        # my submission record(s) for X", which is exactly what this
        # intent already answers (including doc-path/status fields via
        # enrich_instance_log_entry) — no new capability needed, just
        # routing these phrasings here instead of falling through.
        r"\breport\s+ready\s+for\s+my\s+submission\s+of\s+return\b",
        r"\bdownload\s+the\s+report\s+for\s+my\s+(last\s+)?submission\s+of\s+return\b",
        r"\bmy\s+on-?time\s+submission\s+rate\s+for\s+return\b"),
    _mk(Intent.SUBMISSIONS_FOR_RETURN, ("return",),
        r"\bwho\s+submitted\s+returns?\b", r"\bwho\s+submitted\s+.*\breturns?\b",
        # "report generation status for return X this period" — the most
        # recent submission's status IS the report-generation status in
        # this system (there's no separate "generated" vs "submitted"
        # state), so this reduces to SUBMISSIONS_FOR_RETURN's own "most
        # recent submission" summary.
        r"\breport\s+generation\s+status\s+for\s+return\b",
        r"\bhistorical\s+on-?time\s+submission\s+rate\s+for\s+return\b"),
    _mk(Intent.SUBMISSION_DETAIL, ("self", "other_user"),
        r"\binstance\s+document\s+path\s+for\b", r"\bcims\s+upload\s+status\s+for\s+my\s+submission\b",
        r"\brejection\s+reason\b"),
    _mk(Intent.SUBMISSION_STATUS, ("self", "other_user"),
        r"\bstatus\s+of\s+(my\s+)?submission\b", r"\bwas\s+my\s+submission\b.*\brejected\b",
        # "what is the status of <instance log id>" / "...of id: <id>" —
        # no literal "submission" word at all. This is the Id a
        # generate-instance call now echoes back to the user (see
        # _find_new_instance_log_id in agent/__init__.py), a 32-char hex
        # GUID (dashed or not) — distinctive enough to anchor on directly
        # rather than requiring "submission" in the phrasing.
        rf"\bstatus\s+of\s+(?:id\s*[:#]?\s*)?{_INSTANCE_ID_PATTERN}\b"),
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


# Single-token frequency words a typo is plausible for — deliberately a
# small, closed, distinctive vocabulary (5+ letters, no real overlap with
# role/department/user names) so fuzzy-correcting one of these can't
# plausibly clobber an unrelated proper noun elsewhere in the question.
# Multi-word forms ("half yearly", "semi annual") are skipped — per-token
# fuzzy correction can't sensibly fix a typo spanning two words, and the
# exact/synonym forms already cover those without needing typo tolerance.
_FREQ_TYPO_VOCAB = (
    "daily", "weekly", "monthly", "quarterly", "yearly",
    "annual", "annually", "fortnightly", "biweekly",
)
_FREQ_TYPO_SCORE_CUTOFF = 82

# Every single-word form that is ALREADY a valid, recognized frequency
# word — the adjective forms above plus every bare-noun synonym
# (month/quarter/week/day/year/fortnight/...) PERIOD_ALIASES also
# resolves. These must never be "corrected": they're not typos, they're a
# different (already-handled) word form, and skipping them here is what
# stops this normalizer from mangling perfectly valid text like "last
# month"/"this quarter" elsewhere in the app (date-range/filing-status
# phrasing, submission-history phrasing, ...) into "last monthly"/"this
# quarterly".
_FREQ_TYPO_SAFE_WORDS = frozenset(
    re.sub(r"[^a-z]", "", k) for k in PERIOD_ALIASES if " " not in k
) | frozenset(_FREQ_TYPO_VOCAB) | {"fortnight"}


def _normalize_freq_typos(q: str) -> str:
    """Replace a mistyped frequency word ("quaterly", "montly", "anual")
    with its correct spelling before any pattern matching runs, so every
    downstream regex/alias lookup sees the canonical word without needing
    its own typo tolerance. Only touches a token when it's NOT already a
    recognized frequency word/synonym (nothing to fix there) and is long
    enough (4+ letters) that a fuzzy match is meaningful rather than noise."""
    words = q.split()
    changed = False
    out = []
    for w in words:
        core = re.sub(r"[^A-Za-z]", "", w)
        if len(core) < 4 or core.lower() in _FREQ_TYPO_SAFE_WORDS:
            out.append(w)
            continue
        match = _fuzz.extractOne(core.lower(), _FREQ_TYPO_VOCAB, score_cutoff=_FREQ_TYPO_SCORE_CUTOFF)
        if match:
            out.append(w.replace(core, match[0]))
            changed = True
        else:
            out.append(w)
    return " ".join(out) if changed else q


def classify_new(question: str) -> tuple[Intent | None, dict, str | None]:
    """Return (Intent, params, target_type) or (None, {}, None) if no new-
    taxonomy rule matches. Callers should fall back to the legacy
    intent_classifier.classify()/check_db_qa_intent() when this returns None.

    Keyword-group rules (USER/DEPARTMENT/ROLE/ROLE_ACCESS) are tried first
    since they're the accuracy-hardened categories; literal-pattern rules
    (everything else) are tried second, exactly as before.
    """
    q = _normalize_freq_typos(question.strip())

    kw_match = _match_keyword_rules(q)
    if kw_match is not None:
        intent, target_types = kw_match
        target_type = _infer_target_type(q, target_types)
        target_type = _refine_range_target_type(intent, q, target_types, target_type)
        target_type = _refine_submission_target_type(intent, q, target_types, target_type)
        params = _extract_new_params(intent, q)
        params["target_type"] = target_type
        return intent, params, target_type

    for intent, target_types, patterns in _NEW_RULES:
        for pat in patterns:
            if pat.search(q):
                target_type = _infer_target_type(q, target_types)
                target_type = _refine_range_target_type(intent, q, target_types, target_type)
                target_type = _refine_submission_target_type(intent, q, target_types, target_type)
                params = _extract_new_params(intent, q)
                params["target_type"] = target_type
                return intent, params, target_type
    return None, {}, None


_SYSTEM_WIDE_RANGE_RE = re.compile(
    r"\b(system[\s-]?wide|across\s+all\s+departments?|all\s+departments?|every\s+department)\b",
    re.IGNORECASE,
)


_RANGE_TARGET_TYPE_INTENTS = (
    Intent.REPORTS_FILED_IN_RANGE, Intent.REPORTS_UPCOMING_IN_RANGE,
    Intent.MONTHLY_FILING_STATUS,
)


def _refine_range_target_type(
    intent: Intent, q: str, accepted: tuple[str, ...], inferred: str,
) -> str:
    """Correct _infer_target_type's generic 2-way guess for
    REPORTS_FILED_IN_RANGE / REPORTS_UPCOMING_IN_RANGE / MONTHLY_FILING_
    STATUS, whose accepted set is ("self", "department", "system_wide") —
    three options, not the usual two _infer_target_type is designed for.

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
    if intent not in _RANGE_TARGET_TYPE_INTENTS:
        return inferred

    if _SYSTEM_WIDE_RANGE_RE.search(q) and "system_wide" in accepted:
        return "system_wide"

    explicit_dept = _extract_named_entity_before_or_after(q, ("department", "dept"))
    if explicit_dept and "department" in accepted:
        return "department"

    return "self" if "self" in accepted else inferred


def _refine_submission_target_type(
    intent: Intent, q: str, accepted: tuple[str, ...], inferred: str,
) -> str:
    """Correct _infer_target_type's generic 2-way guess for
    SUBMISSION_STATUS / SUBMISSION_DETAIL, whose accepted set is
    ("self", "other_user") — "other_user" is admin-only (access_control.
    TARGET_TYPES_REQUIRING_ADMIN), but _infer_target_type falls back to
    it for ANY phrasing that isn't self-referential ("my"/"I"), not just
    phrasing that actually names another user. "What is the status of
    <instance-log-id>?" has neither a self-referential word NOR a named
    other user — it's simply asking about a specific submission, which
    could well be the caller's own — so it must default to "self", not
    silently deny a regular user via the admin-gated branch. Only an
    explicitly named other user ("...made by jsmith", "...for user
    jsmith") should route to "other_user".
    """
    if intent not in (Intent.SUBMISSION_STATUS, Intent.SUBMISSION_DETAIL):
        return inferred

    named_user = _extract_after_kw(
        q, "user", "for user", "of user", "about user", "made by", "submitted by",
    )
    if named_user and "other_user" in accepted:
        return "other_user"

    return "self" if "self" in accepted else inferred


# Intents opted into the widened embedding_none -> LLM disambiguation path
# (see classify_new_with_semantic_tiers below). Started as a Department-only
# rollout; the Role/Role-Access accuracy pass extended it to that module too
# — the mechanism itself is generic, only membership here is module-specific.
# Kept the name for historical/diff-minimization reasons even though it's no
# longer department-only.
DEPARTMENT_INTENTS = frozenset({
    Intent.DEPARTMENT_LIST,
    Intent.DEPARTMENT_PROFILE,
    Intent.DEPARTMENT_RETURNS,
    Intent.DEPARTMENTS_WITH_RETURN_ACCESS,
    Intent.DEPARTMENT_HAS_RETURN,
    Intent.USERS_BY_DEPARTMENT,
    Intent.DEPT_RETURN_ACCESS_MATRIX,
    Intent.MY_RETURN_ACCESS,
    Intent.DEPT_FULL_RETURN_LIST,
    Intent.ROLE_LIST,
    Intent.ROLE_PROFILE,
    Intent.ROLE_USERS,
    Intent.USERS_BY_ROLE,
    Intent.ROLE_PEER_COUNT,
    Intent.PERMISSION_PROFILE,
    Intent.PERMISSION_CHECK,
    Intent.ROLES_WITH_PERMISSION,
    Intent.ROLE_MODULE_ACCESS,
    Intent.ROLE_PERMISSION_DIFF,
    # PERIOD intents (PERIOD_LIST/PERIOD_LOOKUP/RETURNS_BY_FREQUENCY) were
    # tried here too, but the relaxed (no-floor) candidate search pulled
    # in totally unrelated queries via superficial "what is ... today/
    # year"-shaped overlap with the new personal-calendar exemplars —
    # confirmed by test_embedding_none_widened_to_llm_for_department_only
    # failing on "what is the weather today". Unlike Department/Role,
    # PERIOD's regex coverage is already comprehensive (every taxonomy
    # question + its variations resolves via regex), so the widening's
    # marginal benefit here doesn't justify that false-positive risk —
    # left out deliberately, not an oversight.
})


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

    from backend.db_qa.intents.embedding_index import classify_by_embedding, search_intent_relaxed
    from backend.db_qa.intents.taxonomy import INTENT_SPECS

    async def _disambiguate(candidate_intents: list[Intent]) -> Intent | None:
        """Shared LLM-disambiguation call for both the "ambiguous" and the
        widened "none" path below — same candidates-in/Intent-or-None-out
        shape either way."""
        from backend.services.llm_service import disambiguate_intent

        candidates = [(c.value, INTENT_SPECS[c].description) for c in candidate_intents]
        try:
            chosen_value = await disambiguate_intent(question, candidates)
        except Exception:
            # The Ollama endpoint (local or a remote proxy) can fail
            # transiently — timeout, connection refused, 502/503 from a
            # proxy in front of it, etc. disambiguate_intent()'s own
            # contract is "None means still-ambiguous, fall through to the
            # next tier" for a DECLINED answer; a transport/HTTP failure
            # must degrade the same way, not crash the whole chat request
            # (this call sits deep in decide()'s STEP 2, with STEP 3/4
            # fallbacks still available above it).
            logger.warning(
                "[LLM_DISAMBIGUATE_FAILED] question=%r candidates=%r",
                question, [c[0] for c in candidates], exc_info=True,
            )
            return None
        return Intent(chosen_value) if chosen_value is not None else None

    embedding_result = classify_by_embedding(question)
    tier = embedding_result["tier"]

    resolved_intent: Intent | None = None
    if tier == "embedding_confident":
        resolved_intent = embedding_result["intent"]
        tier = "embedding"
    elif tier == "embedding_ambiguous":
        candidate_intents = [c_intent for c_intent, _score, _text in embedding_result["candidates"]]
        resolved_intent = await _disambiguate(candidate_intents)
        tier = "llm_disambiguation"
    elif tier == "embedding_none":
        # Nothing cleared MIN_SCORE at all — normally this falls straight
        # through to the legacy regex tier. Before doing that, re-search
        # WITHOUT the floor (search_intent_relaxed) purely to see whether the
        # nearest — if still-too-far — matches belong to a module we've
        # explicitly opted into widened LLM coverage for (DEPARTMENT_INTENTS,
        # above). Scoped rather than applied to every intent: a query
        # genuinely unrelated to anything in the taxonomy should keep
        # skipping the LLM call for every module NOT in that set.
        #
        # Restricted to the top 2 relaxed candidates, not all 5: with no
        # score floor, SOME department intent shows up SOMEWHERE in the
        # noisy top-5 for most off-topic queries too (embedding space is
        # small — 9 of 56 intents belong to this module) — tested directly
        # against "what is the capital of France" / "tell me a joke" /
        # "what is the weather today". Restricting to top-2 filters out
        # some of these (e.g. "weather", where the department hit was only
        # at position 5) but not all (for "capital of France", both top-2
        # slots happened to be department intents) — this is a partial
        # latency optimization, not the correctness guarantee. Correctness
        # comes from disambiguate_intent() itself, verified directly against
        # both of those exact adversarial queries: it declined cleanly in
        # both cases, including one where the model ignored instructions and
        # answered something else entirely — the "cannot find exactly one
        # candidate value in the response" fallback still returned None.
        relaxed_intents = [c_intent for c_intent, _score, _text in search_intent_relaxed(question)[:2]]
        if any(c in DEPARTMENT_INTENTS for c in relaxed_intents):
            resolved_intent = await _disambiguate(relaxed_intents)
            tier = "llm_disambiguation"
        else:
            tier = "none"
    else:
        tier = "none"

    if resolved_intent is None:
        return None, {}, None, tier

    spec = INTENT_SPECS[resolved_intent]
    resolved_target_type = _infer_target_type(question, spec.target_types)
    resolved_target_type = _refine_range_target_type(
        resolved_intent, question, spec.target_types, resolved_target_type,
    )
    resolved_target_type = _refine_submission_target_type(
        resolved_intent, question, spec.target_types, resolved_target_type,
    )
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
    # Checked before "with_counts": "top 5 departments BY RETURN COUNT" also
    # matches with_counts' "return\s+counts?" pattern, and first-match-wins
    # in this table — top_n must win that tie or "top N" collapses to the
    # plain with_counts (unlimited, unsorted) branch instead of the
    # sorted-and-sliced one.
    ("top_n", _kw(r"top\s+\d+")),
    # Every phrasing here should mean the same thing regardless of word
    # order or verb choice — "no returns assigned", "zero returns
    # assigned", "don't/doesn't/do not have any returns", "no assigned
    # returns" all describe a department with zero accessible returns.
    ("no_returns", _kw(r"no\s+returns?", r"without\s+any\s+returns?", r"zero\s+returns?",
                        r"no\s+assigned\s+returns?",
                        r"don'?t\s+have\s+any\s+returns?", r"doesn'?t\s+have\s+any\s+returns?",
                        r"do\s+not\s+have\s+any\s+returns?", r"does\s+not\s+have\s+any\s+returns?")),
    # An inherently vague quantity ("few"/"some"/"several" returns) with no
    # ordinal ranking (unlike "fewest") — this can't be answered with a
    # single deterministic query, so it's flagged for the handler to ask
    # a clarification question instead of guessing what "few" means.
    ("ambiguous_quantity", _kw(r"\bfew\b", r"\bsome\b", r"\bseveral\b")),
    ("most", _kw(r"most\s+returns?", r"maximum\s+returns?")),
    ("fewest", _kw(r"fewest\s+returns?", r"least\s+returns?", r"minimum\s+returns?")),
    ("with_counts", _kw(r"return\s+counts?", r"with\s+their\s+return", r"assigned\s+return\s+counts?")),
    ("inactive", _INACTIVE_PAT),
    ("active", _ACTIVE_PAT),
]

_TOP_N_RE = re.compile(r"\btop\s+(\d+)\b", re.IGNORECASE)


def _extract_top_n(q: str, default: int = 5) -> int:
    """The N in "top N departments" — defaults to 5 (matching the brief's
    own example, "Top 5 departments by return count") if somehow the
    query_type matched "top_n" without a parseable number following it."""
    m = _TOP_N_RE.search(q)
    return int(m.group(1)) if m else default

_ROLE_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("count", _HOW_MANY_PAT),
    ("exists", _kw(r"is\s+there\s+a\s+role", r"does\s+.*role.*exist", r"role.*exists?\b",
                    r"check\s+if.*role.*exists?", r"is\s+.*\s+a\s+valid\s+role")),
    ("most_users", _kw(r"most\s+users", r"maximum\s+users?", r"largest", r"biggest")),
    ("least_users", _kw(r"least\s+users?", r"fewest\s+users?", r"minimum\s+users?",
                          r"smallest\s+role", r"least[\s-]?used\s+role",
                          r"role.{0,15}fewest", r"role.{0,15}used\s+by\s+the\s+fewest")),
    ("with_counts", _kw(r"user\s+counts?", r"number\s+of\s+users\s+in\s+each")),
    ("inactive", _INACTIVE_PAT),
    ("active", _ACTIVE_PAT),
]

# RETURN_LIST query_type — checked in this order so "formula validation
# AND schema-calc validation" (a composite, both-flags check) is matched
# before the single-flag "rbi"/"large_validator" patterns would otherwise
# also (harmlessly, but less precisely) match on the word "validation".
_RETURN_LIST_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("next_three_dates", _kw(r"next\s+three\s+(upcoming\s+)?due\s+dates?",
                              r"next\s+\d+\s+(upcoming\s+)?due\s+dates?")),
    ("due_gt", _kw(r"due\s+period\s+of\s+more\s+than", r"due\s+.{0,15}(more|greater)\s+than",
                   r"due\s+.{0,15}exceed")),
    ("formula_and_schema", _kw(r"formula\s+validation.{0,40}schema", r"both\s+formula.{0,40}schema",
                                r"schema.{0,40}validation.{0,20}and.{0,20}formula")),
    ("rbi", _kw(r"rbi\s+validation")),
    ("large_validator", _kw(r"large\s+validator")),
    ("cims", _kw(r"cims[\s-]?enabled", r"use\s+cims\b", r"\bcims\b.{0,15}enabled")),
    ("istbl", _kw(r"table\s+linkbase", r"\bistbl\b", r"\btbl\b")),
    ("inactive", _INACTIVE_PAT),
    ("active", _ACTIVE_PAT),
]

_NONXBRL_RETURN_LIST_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("no_due_days", _kw(r"no\s+due\s+days?\s+configured", r"without\s+due\s+days?")),
    ("has_folder", _kw(r"folder\s+structure", r"has\s+a\s+folder")),
]

# RETURN_VALIDATION_CONFIG's detail_type — checked in this order so the
# composite "both formula AND schema-calc" phrasing wins over the two
# single-flag patterns it would otherwise also (less precisely) match.
_RETURN_VALIDATION_DETAIL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("formula_and_schema", _kw(r"formula\s+validation.{0,40}schema", r"both\s+formula.{0,40}schema",
                                r"schema.{0,40}validation.{0,20}and.{0,20}formula")),
    ("formula", _kw(r"formula\s+validation")),
    ("schema", _kw(r"schema[\s-]?calc\w*\s+validation", r"schema\s+validation")),
    ("rbi", _kw(r"rbi\s+validation")),
    ("large", _kw(r"large\s+validator")),
]


def _extract_return_validation_detail(q: str) -> str | None:
    for value, pat in _RETURN_VALIDATION_DETAIL_PATTERNS:
        if pat.search(q):
            return value
    return None


_RETURN_CATEGORY_RE = re.compile(r"\b(dpss|dbs|dbr)\b", re.IGNORECASE)
_DUE_GT_THRESHOLD_RE = re.compile(r"\b(?:more|greater)\s+than\s+(\d+)\s+days?\b", re.IGNORECASE)


def _extract_return_category(q: str) -> str | None:
    m = _RETURN_CATEGORY_RE.search(q)
    return m.group(1).upper() if m else None


def _extract_due_gt_threshold(q: str, default: int = 21) -> int:
    m = _DUE_GT_THRESHOLD_RE.search(q)
    return int(m.group(1)) if m else default


# Values here must match submission_handlers.handle_submission_list's own
# _STATUS_GROUPS keys ("pending"/"approved"/"audited"/"rejected") plus its
# two CIMS-upload branches and "has_error_doc" — checked in this order so
# "pending approval" (containing the substring "approv" too) matches
# "pending" first, not "approved".
_SUBMISSION_STATUS_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("pending", _kw(r"pending")),
    ("rejected", _kw(r"rejected")),
    ("audited", _kw(r"audited")),
    ("approved", _kw(r"approved")),
    ("cims_ok", _kw(r"uploaded\s+to\s+cims\s+success\w*", r"cims\s+upload\s+success\w*", r"cims\s+ok")),
    ("cims_failed", _kw(r"failed\s+cims\s+upload", r"cims\s+upload\s+fail\w*")),
    ("has_error_doc", _kw(r"error\s+doc(?:ument)?")),
]

_MENU_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("top_level", _kw(r"top[\s-]?level")),
]


# ── PERIOD query_type / field extraction ────────────────────────────────

# Checked in this order (via _extract_query_type/_first_match's
# first-match-wins semantics) so a question naming two periods for
# comparison ("difference between QF and QAD") is never miscaught by the
# broader threshold/no-notification checks below it.
_PERIOD_LOOKUP_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("compare", _kw(r"difference\s+between", r"compare\b", r"\bvs\.?\b")),
    ("notification_gt", _kw(r"greater\s+than\s+\d+\s*days?",
                             r"advance\s+notification.{0,20}greater\s+than",
                             r"notification\s+period\s+greater\s+than")),
    ("no_notification", _kw(r"no\s+advance\s+notification", r"without\s+(any\s+)?advance\s+notification",
                             r"advance\s+notification.{0,20}not\s+configured")),
    ("personal_calendar", _kw(r"personal\s+reporting\s+calendar", r"calendar\s+view",
                               r"report\s+due\s+dates?", r"reporting\s+calendar\s+for")),
]

# Which single field a plain (non-aggregate) PERIOD_LOOKUP question wants —
# only consulted when query_type above is None, i.e. this is a genuine
# one-period lookup ("what is the EBR code for Quarterly?"), mirroring
# RETURN_FIELD's single-field extraction for returns.
_PERIOD_FIELD_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("id", _kw(r"period\s+id\s+for", r"what\s+is\s+the\s+period\s+id", r"which\s+period\s+id",
               r"period\s+id\s+represents?")),
    ("name", _kw(r"period\s+name\s+for", r"what\s+is\s+the\s+period\s+name")),
    ("ebr_code", _kw(r"ebr\s+(frequency\s+)?code")),
    ("notification_days", _kw(r"advance\s+notification\s+days?")),
]

_PERIOD_LIST_QUERY_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("shared_frequency", _kw(r"share\s+the\s+same", r"same\s+reporting\s+(schedule|frequenc\w*)")),
    ("most_returns", _kw(r"most\s+returns?\s+scheduled", r"most\s+returns?\s+assigned",
                          r"(period|frequenc\w*)\s+has\s+the\s+most\s+returns?",
                          r"highest\s+number\s+of\s+returns?",
                          r"used\s+by\s+the\s+maximum\s+(number\s+of\s+)?returns?",
                          r"maximum\s+(number\s+of\s+)?returns?.{0,20}(period|frequenc\w*)")),
]

_PERIOD_ID_RE = re.compile(r"\bperiod\s+id\s+(\d+)\b", re.IGNORECASE)
_NOTIFICATION_THRESHOLD_RE = re.compile(r"\bgreater\s+than\s+(\d+)\s*days?\b", re.IGNORECASE)


def _extract_period_id(q: str) -> str | None:
    m = _PERIOD_ID_RE.search(q)
    return m.group(1) if m else None


def _extract_notification_threshold(q: str, default: int = 0) -> int:
    m = _NOTIFICATION_THRESHOLD_RE.search(q)
    return int(m.group(1)) if m else default


def _extract_period_name_loose(q: str) -> str | None:
    """Fallback for period names/EBR codes _extract_period's fixed alias
    map doesn't cover (e.g. a custom or less-common PeriodName) — takes
    whatever follows "for" and strips trailing filler words a period name
    would never itself contain."""
    name = _extract_after_kw(q, "for")
    if not name:
        return None
    name = re.sub(
        r"\s+(frequenc\w*|returns?|reporting|period|schedule|configured)\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip(" ?.")
    return name or None


# Canonical verb per HasXxx group, checked before its synonyms so
# "create new users" reports back "create" (natural) rather than "new"
# (grammatically awkward in "You can new.") — both map to the same
# HasNew attribute, so this only affects response phrasing, not correctness.
_CANONICAL_ACTION_ORDER = ("create", "edit", "view", "approve",
                           "add", "update", "modify", "see", "read",
                           "approval", "upload", "new")


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


def _first_match(q: str, table: list[tuple[str, re.Pattern]]) -> str | None:
    """Plain first-match-wins lookup — like _extract_query_type but without
    its "how many active/inactive X" special case, which only makes sense
    for User/Department/Role-style boolean active/inactive fields, not for
    categories like submission status or menu top-level/nested."""
    for value, pat in table:
        if pat.search(q):
            return value
    return None


def _strip_leading_not_entity_words(phrase: str) -> str:
    """Drop leading question/list/auxiliary filler words from a multi-word
    capitalized run (e.g. "Which Admin" -> "Admin", "Can Tester" -> "Tester")
    — needed because the run can legitimately start with a sentence-initial
    filler word that also happens to be capitalized."""
    words = phrase.split()
    while words and words[0].lower() in _NOT_AN_ENTITY_NAME:
        words.pop(0)
    return " ".join(words)


def _extract_named_entity_before_or_after(q: str, noun_words: tuple[str, ...]) -> str | None:
    """Extract a proper-noun-looking token immediately before OR after any
    of *noun_words* (e.g. "department"/"dept"). Handles both "Finance
    department" (before) and "department of Finance"/"in Finance" (after),
    which _extract_after_kw alone (after-only) cannot. A sentence-initial
    question/list word (What/Which/Who/...) is never returned as the name.
    """
    for word in noun_words:
        # Two passes, most-specific first.
        #
        # Pass 1 (from my-nlp-changes): a run of up to 4 CAPITALIZED words
        # ("Admin User role") — a single-token capture would otherwise grab
        # only "User" out of "Admin User role", silently truncating any
        # multi-word proper name.
        #
        # Pass 2 (from ChatBot_5.5-test): case-INSENSITIVE single token. A
        # real user typing "the admin role create" (all lowercase, the
        # overwhelmingly common case in chat) has no capitalized token at
        # all, so pass 1 misses and this would otherwise fall through to the
        # "after" fallback below, which then grabs whatever verb follows
        # "role" ("create"/"approve"/...) — self-test: "what modules can the
        # admin role create?" extracted target_role='create' instead of
        # 'admin'. _NOT_AN_ENTITY_NAME filters filler words in both passes.
        #
        # Kept as two separate passes rather than one case-insensitive
        # multi-word pattern: with IGNORECASE the {0,3}-word run would
        # happily swallow lowercase filler ahead of the real name.
        for pattern, flags in (
            (rf"\b((?:[A-Z][A-Za-z0-9_.\-]*\s+){{0,3}}[A-Z][A-Za-z0-9_.\-]*)\s+{re.escape(word)}\b", 0),
            (rf"\b([A-Za-z][A-Za-z0-9_.\-]{{1,40}})\s+{re.escape(word)}\b", re.IGNORECASE),
        ):
            for m in re.finditer(pattern, q, flags):
                candidate = _strip_leading_not_entity_words(m.group(1).strip())
                if candidate and candidate.lower() not in _NOT_AN_ENTITY_NAME:
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


# Leading filler that _extract_named_entity_before_or_after's "after"
# fallback can swallow when the sentence has a bare "department"/"dept"
# NOUN earlier than the actual named department — e.g. "What is department
# ID of department Dept1?" has two occurrences of "department"; the
# extractor's after-keyword anchor matches the FIRST one (a common-noun use
# in "department ID"), not the second (the one immediately preceding the
# real name), producing "ID of department Dept1" instead of "Dept1". This
# mirrors _LEADING_FILLER_RE/_clean_extracted_return_name's existing
# precedent for the same class of bug on return names — applied repeatedly
# since one strip can reveal another (e.g. an id-filler strip can still
# leave a bare "department " prefix behind).
_DEPT_LEADING_FILLER_RE = re.compile(
    r"^(?:department\s+|dept\s+)?"
    r"(?:id|code|identifier)\s+(?:of|for)\s+"
    r"(?:the\s+)?(?:department\s+|dept\s+)?",
    re.IGNORECASE,
)


def _clean_extracted_department_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = name
    for _ in range(2):  # a second pass catches a filler revealed by the first
        stripped = _DEPT_LEADING_FILLER_RE.sub("", cleaned).strip()
        if stripped == cleaned:
            break
        cleaned = stripped
    return cleaned or None


# Same class of bug as _DEPT_LEADING_FILLER_RE, for role names — "What is
# the role ID for Tester?" anchors _extract_after_kw's "role" keyword on
# the first (common-noun) use in "role ID", capturing "ID for Tester"
# instead of "Tester".
_ROLE_LEADING_FILLER_RE = re.compile(
    r"^(?:role\s+)?(?:id|code|identifier)\s+(?:of|for)\s+(?:the\s+)?(?:role\s+)?",
    re.IGNORECASE,
)

# _extract_after_kw's generic stop-word set (?/is/has/have/not/and) doesn't
# cover the action verbs that commonly trail a role name in permission
# questions ("Can role Tester CREATE new users?", "...role Tester VIEW the
# audit log?") — without this, the whole rest of the sentence gets
# captured as if it were part of the role name.
_ROLE_TRAILING_FILLER_RE = re.compile(
    r"\s+(?:create|edit|view|approve|access|disable|upload|run|generate|"
    r"perform|manage|see|read|update|modify|add)\b.*$",
    re.IGNORECASE,
)


def _clean_extracted_role_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = name
    for _ in range(2):
        stripped = _ROLE_LEADING_FILLER_RE.sub("", cleaned).strip()
        if stripped == cleaned:
            break
        cleaned = stripped
    cleaned = _ROLE_TRAILING_FILLER_RE.sub("", cleaned).strip()
    cleaned = cleaned.rstrip(".").strip()
    return cleaned or None


# Words that can appear immediately next to "role"/"roles" in a question
# without themselves being (part of) a role NAME. Real user input is not
# reliably capitalized ("tester role", "admin role"), so — unlike
# _extract_named_entity_before_or_after's [A-Z]-anchored approach — this
# extractor identifies the name by what it is NOT: any run of words next to
# "role(s)" that avoids this set is treated as the name, regardless of case.
_ROLE_FILLER_WORDS = frozenset({
    "which", "who", "what", "show", "list", "give", "tell", "can", "you", "us", "whose",
    "where", "when",
    "the", "a", "an", "this", "that", "these", "those", "is", "are", "does",
    "do", "did", "has", "have", "had", "my", "our", "your", "his", "her",
    "its", "their", "same", "similar", "role", "roles", "in", "system",
    "currently", "present", "available", "please", "of", "for", "to", "and",
    "or", "assigned", "belong", "belongs", "belonging", "with", "having",
    "under", "i", "we", "they", "he", "she", "it", "me", "all", "any",
    "most", "least", "fewest", "minimum", "maximum", "smallest", "largest", "biggest",
    "user", "users", "by",
})
# Connective words that can sit between "role"/"roles" and the actual name
# on the AFTER side ("role OF Tester", "role ID OF admin") — skipped over
# rather than treated as filler that ends the search.
_ROLE_AFTER_CONNECTIVES = frozenset({"of", "called", "named", "is", "for", "id", "code", "identifier"})


def _extract_role_name_loose(q: str) -> str | None:
    """Role-name extraction robust to real (often lowercase, informal)
    user phrasing — "which users have tester role in the system" needs to
    find "tester", not "in the system" (the after-keyword fallback used
    elsewhere anchors on the FIRST thing following "role", which for a
    "<name> role" ordering is nothing or trailing filler, not the name).

    For every occurrence of "role"/"roles" in the question, tries the
    words immediately BEFORE it first ("tester role", "admin role" — the
    common ordering), then the words immediately AFTER, skipping past
    connective words ("role of Tester", "role ID of admin"). A run of up
    to 3 words is captured, stopping at the first filler word — multi-word
    names ("Admin User", "Test Maker") are it stops at "role" and later
    can be stripped separately.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", q)
    lower = [t.lower() for t in tokens]
    for i, t in enumerate(lower):
        if t not in ("role", "roles"):
            continue
        # Before: "<name> role"
        j = i - 1
        words: list[str] = []
        while j >= 0 and lower[j] not in _ROLE_FILLER_WORDS and len(words) < 3:
            words.insert(0, tokens[j])
            j -= 1
        if words:
            return " ".join(words)
        # After: "role of <name>" / "role ID of <name>"
        j = i + 1
        while j < len(lower) and lower[j] in _ROLE_AFTER_CONNECTIVES:
            j += 1
        words = []
        while j < len(lower) and lower[j] not in _ROLE_FILLER_WORDS and len(words) < 3:
            words.append(tokens[j])
            j += 1
        if words:
            return " ".join(words)
    return None


_ROLE_ID_RE = re.compile(r"\brole\s+id\s+(\d+)\b", re.IGNORECASE)


def _extract_role_id(q: str) -> str | None:
    """The numeric id in "role ID <N>" (e.g. "what is the name of role ID
    106?") — distinct from a role NAME lookup ("role ID for Tester"), which
    _clean_extracted_role_name/target_role handles instead."""
    m = _ROLE_ID_RE.search(q)
    return m.group(1) if m else None


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


# Words that only ever DESCRIBE a return rather than identify one. Used by
# _clean_extracted_return_name to reject a capture consisting of nothing
# else — see its comment.
_GENERIC_RETURN_WORDS_RE = re.compile(
    rf"\b(?:{_NON_XBRL}|nonxbrl|xbrl|nx|returns?|forms?|reports?|filings?|"
    # "…have non-XBRL return ACCESS" / "…return SUBMISSION" — the relationship
    # word trailing the noun, swept up by the after-"return" capture but
    # never part of a name.
    r"access|submissions?|"
    r"the|all|any|my|our|their|a|an|this|these|those|list|of|to)\b",
    re.IGNORECASE,
)


def _clean_extracted_return_name(name: str | None) -> str | None:
    if not name:
        return None
    name = _LEADING_FILLER_RE.sub("", name).strip()
    name = _TRAILING_FILLER_RE.sub("", name).strip()
    # A sentence-final period gets swept up when the return name is the
    # last word before it ("...return CIMS_ROR.") — trailing "?" is
    # already excluded by the capture group itself, but "." isn't, so
    # "CIMS_ROR." was reaching resolve_named_return as a literal 5th
    # character no real return name has, turning an exact match into a
    # fuzzy multi-candidate one.
    name = name.rstrip(".").strip()
    if not name:
        return None
    # A phrase built ENTIRELY out of generic type/category words ("non xbrl
    # returns", "xbrl return", "all the returns") is the user describing a
    # KIND of return, not naming one — "which departments can access non
    # xbrl returns?" was reaching resolve_named_return with the literal
    # target "non xbrl returns" and answering with whatever fuzzy match
    # won. Strip the generic vocabulary and require something to survive;
    # a real name/code always leaves a residue ("non-XBRL return BSR1" ->
    # "BSR1"), so this needs no per-name allowlist.
    if not _GENERIC_RETURN_WORDS_RE.sub("", name).strip(" -_"):
        return None
    return name


# Return names/codes in this dataset are written distinctively (CIMS_ROR,
# DPSS09, DBR01, FormA) rather than typed casually in lowercase the way role
# names are, so a capitalized-token heuristic is reliable here.
_RETURN_NAME_BEFORE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_.\-]{1,30})\s+returns?\b")
_RETURN_NAME_BEFORE_EXCLUDE = frozenset({"xbrl", "non-xbrl", "nonxbrl", "nx", "the", "all", "my", "which"})


def _extract_return_name_before(q: str) -> str | None:
    """"Which departments can submit the CIMS_ROR RETURN?" — the name sits
    BEFORE the word "return(s)", which _extract_after_kw (after-only) can't
    see at all; used only as a fallback once the after-keyword extraction
    has already come up empty.

    Requires the candidate to contain an uppercase letter or digit (true of
    every real return name/code in this dataset — CIMS_ROR, DPSS09, FormA)
    rather than an ever-growing stop-word blocklist — generic connectors
    ("list OF returns", "THE returns") are plain lowercase words and are
    naturally excluded, without needing each one named explicitly.
    """
    for m in _RETURN_NAME_BEFORE_RE.finditer(q):
        candidate = m.group(1)
        if candidate.lower() in _RETURN_NAME_BEFORE_EXCLUDE or candidate.lower() in _NOT_AN_ENTITY_NAME:
            continue
        if any(c.isupper() for c in candidate) or any(c.isdigit() for c in candidate):
            return candidate
    return None


# A return code "looks like" a short run of letters immediately followed
# by 2+ digits (DBR01, DPSS09, CIMS_ROR has no digits so this doesn't cover
# every return, only the numbered ones — the common case for phrasings that
# name a return with no "return"/"form"/"report" anchor word at all, e.g.
# "give me the full profile for DBR01", "whats dpss 09 about"). A single
# optional space/underscore between the letters and digits is normalized
# away, since a spoken-style "dpss 09" should resolve the same as "DPSS09".
_RETURN_CODE_SHAPE_RE = re.compile(r"\b([A-Za-z]{2,})[\s_]?(\d{2,}[A-Za-z0-9_]*)\b")


def _extract_return_name_generic(q: str) -> str | None:
    """Last-resort return-name extraction for RETURN_PROFILE — tries the
    shared return/form/report anchor first, then "profile for/of"-style
    phrasing that has no such anchor, then a bare return-code-shaped token
    anywhere in the message (see _RETURN_CODE_SHAPE_RE) as a final fallback
    for phrasings like "whats dpss 09 about" where the code comes BEFORE
    the only anchor word ("about"), which _extract_after_kw cannot handle
    since it only captures text AFTER its keyword."""
    name = _extract_after_kw(q, "return", "form", "report", "profile for", "profile of")
    name = _clean_extracted_return_name(name)
    if name:
        return name
    m = _RETURN_CODE_SHAPE_RE.search(q)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return None


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
# specific phrases (matched first) win over generic ones. "internal form
# id" is checked BEFORE the bare "return id" pattern (which would
# otherwise also match "form id" loosely) since the two are genuinely
# different fields on a Return row — ReturnId (the external code, e.g.
# "R018") vs Id (the internal numeric row id, e.g. "2029") — not synonyms,
# even though everyday phrasing for them overlaps.
_RETURN_FIELD_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("internal_form_id", _kw(r"internal\s+form\s+id")),
    ("return_id", _kw(r"return\s+id")),
    ("frequency", _kw(r"frequency", r"period\b", r"how\s+often")),
    ("due_days", _kw(r"due\s+days?", r"days?\s+.{0,20}due")),
    ("formats", _kw(r"report\s+formats?", r"formats?\s+.{0,20}available")),
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
    from datetime import date as _date, timedelta as _timedelta
    today = _date.today()
    # "in the next N days" / "due in the next N days" — a rolling window
    # from today, distinct from the fixed-calendar-month cases below.
    next_n = re.search(r"\bnext\s+(\d+)\s+days?\b", q, re.IGNORECASE)
    if next_n:
        end = today + _timedelta(days=int(next_n.group(1)))
        return today.strftime("%d-%b-%Y"), end.strftime("%d-%b-%Y")
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


_NEXT_DUE_RE = re.compile(
    rf"\bnext\s+(?:{_NON_XBRL}\s+|xbrl\s+)?returns?\s+(?:is\s+|has\s+|that\s+is\s+|which\s+is\s+)?due\b"
    rf"|\bnext\s+due\s+(?:{_NON_XBRL}\s+|xbrl\s+)?returns?\b"
    # "which non-XBRL return is due next" — same ask, words reversed.
    rf"|\b(?:{_NON_XBRL}\s+|xbrl\s+)?returns?\s+(?:is\s+)?due\s+next\b",
    re.IGNORECASE,
)

_XBRL_TYPE_RE = _kw(_NON_XBRL, r"nx\b")


def _extract_xbrl_type(q: str) -> str | None:
    """"xbrl" or "non_xbrl", or None if the question doesn't specify —
    handlers treat None as "both"."""
    if _XBRL_TYPE_RE.search(q):
        return "non_xbrl"
    if re.search(r"\bxbrl\b", q, re.IGNORECASE):
        return "xbrl"
    return None


_MONTH_NAME_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
    re.IGNORECASE,
)
_MONTH_YEAR_RE = re.compile(
    r"\b((?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"\s+\d{4})\b",
    re.IGNORECASE,
)
_BARE_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _extract_month_year(q: str) -> str | None:
    """Return a "Month YYYY" string (e.g. "June 2025") for the single month
    a monthly-status question refers to, or None if nothing resolvable was
    found. Tried in this order:

      1. Explicit "Month YYYY"/"Mon YYYY" (e.g. "June 2025", "for June 2025").
      2. Relative-month phrases ("this month"/"current month" -> the
         calendar month execution is running in; "last/previous month" ->
         the month before that; "next month" -> the month after) resolved
         to a concrete "Month YYYY" using today's date — same relative-
         phrase vocabulary already supported by resolve_date_range/
         _extract_date_range for range questions, but resolving to ONE
         month rather than a (start, end) pair.
      3. A bare month name with no year ("What's my XBRL status for
         June?") — paired with the current year, since a bank's own
         reporting history is what's being asked about and users
         overwhelmingly mean the current cycle, not an arbitrary past year;
         a query_type-level clarification isn't warranted for something
         this recoverable.
      4. A bare year with no month ("filing status for 2025") is NOT
         resolved here — a whole year is a range question
         (reports_filed_in_range/reports_upcoming_in_range own that
         shape), not a single-month status question, so returning None
         lets the caller's own "please specify a month" fallback fire
         instead of silently guessing a month within the year.
    """
    m = _MONTH_YEAR_RE.search(q)
    if m:
        return m.group(1)

    ql = q.lower()
    from datetime import date as _date
    today = _date.today()
    if re.search(r"\b(this|current)\s+month\b", ql):
        return today.strftime("%B %Y")
    if re.search(r"\b(last|previous|prior)\s+month\b", ql):
        year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        return _date(year, month, 1).strftime("%B %Y")
    if re.search(r"\bnext\s+month\b", ql):
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return _date(year, month, 1).strftime("%B %Y")

    bare_month = _MONTH_NAME_RE.search(q)
    if bare_month and not _BARE_YEAR_RE.search(q):
        return f"{bare_month.group(1).title()} {today.year}"

    return None


def _extract_submission_id(q: str) -> str | None:
    """A submission/InstanceLog id — either the numeric legacy form
    ("submission 4021") or the 32-char hex GUID an instance-generation
    call now returns to the user ("status of f7593ff7...", "status of
    id: f7593ff7..."). Checked in this order:

      1. A GUID-looking token anywhere in the text — distinctive enough
         (32 hex chars) to trust regardless of surrounding wording.
      2. An explicit "id <value>"/"id: <value>" — covers non-GUID ids
         typed with an explicit "id" label.
      3. "submission <number>" — the plain-numeric-id phrasing.
    """
    m = _INSTANCE_ID_RE.search(q)
    if m:
        return m.group(0)
    m = re.search(r"\bid\s*[:#]?\s*([A-Za-z0-9\-]{1,40})\b", q, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\bsubmission\s+(?:id\s+)?(\d+)\b", q, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def _extract_new_params(intent: Intent, q: str) -> dict:
    params: dict = {}
    explicit = _extract_quoted_or_bracketed(q)

    if intent in (Intent.USER_PROFILE, Intent.USER_FIELD, Intent.USERS_BY_DEPARTMENT,
                  Intent.AUDIT_HISTORY, Intent.SUBMISSION_STATUS, Intent.SUBMISSION_DETAIL,
                  Intent.USER_ACCESS_SUMMARY, Intent.SECURITY_EVENTS):
        params["target_user"] = explicit or _extract_after_kw(
            q, "user", "for user", "of user", "about user", "made by", "submitted by",
        )

    if intent in (Intent.SUBMISSION_STATUS, Intent.SUBMISSION_DETAIL):
        params["submission_id"] = _extract_submission_id(q)

    if intent == Intent.USERS_BY_DEPARTMENT:
        params["target_department"] = explicit or _clean_extracted_department_name(
            _extract_department_name_loose(q))
    elif intent in (Intent.DEPARTMENT_PROFILE, Intent.DEPARTMENT_RETURNS,
                    Intent.DEPARTMENT_HAS_RETURN, Intent.DEPT_FULL_RETURN_LIST, Intent.CROSS_ENTITY_QUERY,
                    Intent.AUDIT_ENTITY_TRAIL, Intent.NONXBRL_RETURN_LIST, Intent.RETURNS_SUBMITTABLE_BY_DEPT):
        params["target_department"] = explicit or _clean_extracted_department_name(
            _extract_named_entity_before_or_after(q, ("department", "dept")))

    if intent == Intent.NONXBRL_RETURN_LIST:
        params["query_type"] = _extract_query_type(q, _NONXBRL_RETURN_LIST_QUERY_TYPE_PATTERNS)

    if intent in (Intent.DEPARTMENT_LIST, Intent.DEPARTMENT_PROFILE, Intent.DEPARTMENT_RETURNS,
                  Intent.DEPARTMENTS_WITH_RETURN_ACCESS, Intent.DEPARTMENT_HAS_RETURN,
                  Intent.DEPT_FULL_RETURN_LIST):
        # Department ID is hidden from table output by default (see
        # db_qa_router._SKIP_FIELDS) since it's an internal identifier
        # most questions never asked about — but when a question
        # explicitly mentions "id"/"ids"/"identifier" it should be shown.
        params["want_dept_id"] = bool(re.search(r"\b(id|ids|identifier)\b", q, re.IGNORECASE))

    if intent == Intent.DEPARTMENT_RETURNS:
        # Previously never populated at all — DEPARTMENT_RETURNS' own spec
        # declares xbrl_type as an optional entity, and the handler already
        # filters on it, but nothing upstream ever extracted it, so "List
        # XBRL returns assigned to my department" silently returned both
        # XBRL and Non-XBRL returns regardless of the explicit XBRL request.
        params["xbrl_type"] = _extract_xbrl_type(q)

    if intent in (Intent.USERS_BY_ROLE, Intent.ROLE_PROFILE, Intent.ROLE_USERS, Intent.PERMISSION_CHECK,
                  Intent.PERMISSION_PROFILE, Intent.ROLES_WITH_PERMISSION, Intent.ROLE_MODULE_ACCESS,
                  Intent.ROLE_PERMISSION_DIFF, Intent.CROSS_ENTITY_QUERY):
        params["target_role"] = explicit or _clean_extracted_role_name(_extract_role_name_loose(q))
        if not params["target_role"] and intent == Intent.USERS_BY_ROLE:
            # No "role" word at all in the question ("give me all admin
            # users", "list of all tester users") — fall back to the
            # structural "<word> users" pattern, same idea as
            # _UsersByDeptStructuralPattern but case-insensitive since role
            # names are typed in lowercase far more often than department
            # names are in practice.
            m = _RoleUsersStructuralPattern().search(q)
            if m:
                params["target_role"] = _RoleUsersStructuralPattern.extract_name(m)

    if intent == Intent.ROLE_PROFILE:
        params["role_id"] = _extract_role_id(q)

    if intent == Intent.ROLE_PERMISSION_DIFF:
        # "difference in permissions BETWEEN Admin User AND Tester" — the
        # role-noun-anchored extractor above only finds a name adjacent to
        # the literal word "role", which this phrasing never uses next to
        # either name, so target_role always came back empty; role_b was
        # never extracted here at all before this fix.
        m = re.search(r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
        if m:
            params["target_role"] = explicit or m.group(1).strip()
            params["role_b"] = m.group(2).strip()

    if intent == Intent.RETURN_VALIDATION_CONFIG:
        params["detail_type"] = _extract_return_validation_detail(q)

    if intent == Intent.DEPARTMENTS_WITH_RETURN_ACCESS and re.search(
            r"\bmissed\b|\bdeadline\b", q, re.IGNORECASE):
        params["query_type"] = "missed_deadline"

    if intent in (Intent.SUBMISSIONS_FOR_RETURN, Intent.MY_SUBMISSION_HISTORY) and re.search(
            r"\bon-?time\s+submission\s+rate\b", q, re.IGNORECASE):
        params["query_type"] = "on_time_rate"

    if intent == Intent.RETURN_LIST:
        params["query_type"] = _extract_query_type(q, _RETURN_LIST_QUERY_TYPE_PATTERNS)
        params["category"] = _extract_return_category(q)
        if params["query_type"] == "due_gt":
            params["threshold_days"] = _extract_due_gt_threshold(q)

    if intent == Intent.RETURN_PROFILE:
        # See _extract_return_name_generic — handles "profile for DBR01"
        # and "whats dpss 09 about" phrasings with no return/form/report
        # anchor word at all (self-test: doc/INTENT_GAP_ANALYSIS.md).
        params["target_return"] = explicit or _extract_return_name_generic(q)
    elif intent in (Intent.RETURN_VALIDATION_CONFIG, Intent.NONXBRL_RETURN_PROFILE,
                  Intent.SUBMISSIONS_FOR_RETURN, Intent.SUBMISSION_LIST, Intent.MY_SUBMISSION_HISTORY,
                  Intent.DEPARTMENTS_WITH_RETURN_ACCESS, Intent.DEPARTMENT_HAS_RETURN,
                  Intent.MY_RETURN_ACCESS, Intent.RETURNS_SUBMITTABLE_BY_DEPT, Intent.LOG_QUERY,
                  Intent.NOTIFICATION_QUERY, Intent.AUDIT_ENTITY_TRAIL, Intent.CROSS_ENTITY_QUERY):
        # "submission of" is tried FIRST: in "is the report ready for my
        # Non-XBRL submission of BSR1(Quarterly)?" the word "report" comes
        # earlier in the sentence but is part of the question, not an
        # anchor for the name — anchoring on it captured the whole clause
        # ("ready for my Non-XBRL submission of BSR1(Quarterly)") as the
        # return name. "submission of X" only ever precedes a real name.
        params["target_return"] = explicit or _clean_extracted_return_name(
            _extract_after_kw(q, "submission of", "submissions of")
            or _extract_after_kw(q, "return", "form", "report")
            or _extract_return_name_before(q))
        if not params["target_return"] and intent in (Intent.DEPARTMENTS_WITH_RETURN_ACCESS,
                                                        Intent.RETURNS_SUBMITTABLE_BY_DEPT):
            # "Which departments can ACCESS CIMS_ROR?" / "...can SUBMIT
            # CIMS_ROR?" — no literal "return"/"form"/"report" word at all,
            # so the extraction above never finds an anchor; the verb
            # itself ("access"/"submit") is the only anchor available here.
            params["target_return"] = explicit or _clean_extracted_return_name(
                _extract_after_kw(q, "access", "submit"))
        if intent == Intent.DEPARTMENTS_WITH_RETURN_ACCESS and not params["target_return"]:
            # No return named at all: "which departments can access non-XBRL
            # returns?" asks the same question about a CATEGORY. Only set
            # when the name is genuinely absent, so a real named-return
            # question is never re-interpreted as a type-level one.
            params["xbrl_type"] = _extract_xbrl_type(q)
    elif intent in (Intent.NEXT_REPORTING_DATE, Intent.RETURN_FIELD):
        params["target_return"] = explicit or _clean_extracted_return_name(
            _extract_return_name_for_due_date(q))

    # When a return-scoped question states the TYPE ("non-XBRL return BSR1",
    # "the XBRL return CIMS_ROR"), carry that through so the handler can
    # restrict name resolution to that type instead of matching across both
    # sets — these intents are shared by both modules, so without it a
    # non-XBRL question could resolve to a similarly-named XBRL return.
    if intent in (Intent.NEXT_REPORTING_DATE, Intent.RETURN_FIELD, Intent.RETURN_PROFILE):
        params["xbrl_type"] = _extract_xbrl_type(q)

    if intent == Intent.NEXT_REPORTING_DATE and re.search(r"\breporting\s+calendar\b", q, re.IGNORECASE):
        params["query_type"] = "calendar"

    if intent == Intent.RETURN_FIELD:
        params["field"] = _extract_return_field(q)

    if intent in (Intent.REPORTS_FILED_IN_RANGE, Intent.REPORTS_UPCOMING_IN_RANGE):
        date_from, date_to = _extract_date_range(q)
        params["date_from"] = date_from
        params["date_to"] = date_to
        params["xbrl_type"] = _extract_xbrl_type(q)

    if intent == Intent.REPORTS_UPCOMING_IN_RANGE:
        # "overdue" has no date range at all (no "between X and Y"/"next N
        # days" span to extract) — it's a distinct computation (next due
        # date already passed AND not yet filed), so it's flagged via
        # query_type rather than trying to force a window out of the text.
        if re.search(r"\boverdue\b", q, re.IGNORECASE):
            params["query_type"] = "overdue"
        # "what is my next non-XBRL return due?" — the mirror image of
        # overdue (soonest FUTURE due date rather than a passed one), and
        # likewise not a window question: the user wants the single next
        # one, whenever it falls, so there is no range to extract.
        elif _NEXT_DUE_RE.search(q):
            params["query_type"] = "next_due"

    if intent == Intent.MONTHLY_FILING_STATUS:
        params["month_year"] = _extract_month_year(q)
        params["xbrl_type"] = _extract_xbrl_type(q)
        # Every MONTHLY_FILING_STATUS phrasing that names a department also
        # names a month via a trailing "for <month>" clause ("status for
        # department Compliance for March 2026") — unlike other department-
        # taking intents, so _extract_named_entity_before_or_after's
        # after-keyword fallback (which only stops at "?"/end-of-string/
        # " is"/" has"/" and") swallows the month clause into the
        # department name. Trim it back off here rather than teaching the
        # shared extractor about a stop-word specific to this one intent.
        dept = explicit or _extract_named_entity_before_or_after(q, ("department", "dept"))
        if dept:
            dept = re.sub(r"\s+for\s+.*$", "", dept, flags=re.IGNORECASE).strip() or None
        params["target_department"] = _clean_extracted_department_name(dept)

    if intent in (Intent.PERMISSION_CHECK, Intent.ROLES_WITH_PERMISSION):
        # Raw keyword, NOT the mapped HasNew/HasEdit/... attribute name —
        # query_handlers/role_handlers.py's handle_permission_check() and
        # handle_roles_with_permission() do their own ACTION_MAP lookup on
        # this value (their own local _ACTION_MAP mirrors
        # intent_classifier.ACTION_MAP), so passing the already-mapped
        # attribute here would double-map and fail to match.
        params["action"] = _extract_raw_action_word(q)
        # _extract_raw_action_word only recognizes a fixed canonical verb
        # list, so an unrecognized verb (e.g. "generate") comes back None
        # and is stripped by this function's final None-filter below —
        # the handler-level LLM fallback (role_handlers._resolve_action_attr
        # -> llm_service.normalize_action_word) has nothing to normalize
        # unless the raw query text survives alongside it.
        params["raw_query"] = q

    if intent == Intent.RETURNS_BY_FREQUENCY:
        params["period_name"] = _extract_period(q) or _extract_period_name_loose(q)

    if intent == Intent.PERIOD_LOOKUP:
        params["query_type"] = _extract_query_type(q, _PERIOD_LOOKUP_QUERY_TYPE_PATTERNS)
        params["period_id"] = _extract_period_id(q)
        if params["query_type"] == "compare":
            # "difference between QF and QAD frequencies" / "compare
            # Quarterly vs Half Yearly" — two period names/EBR codes, not
            # one; period_b has no counterpart in RETURN_FIELD-style
            # single-field lookups, mirroring ROLE_PERMISSION_DIFF's own
            # target_role/role_b pair for the same "compare two named
            # things" shape.
            m = (re.search(r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:\s+frequenc\w*)?(?:\?|$)", q, re.IGNORECASE)
                 or re.search(r"\bcompare\s+(.+?)\s+(?:vs\.?|and)\s+(.+?)(?:\s+frequenc\w*)?(?:\?|$)", q, re.IGNORECASE))
            if m:
                params["period_name"] = m.group(1).strip()
                params["period_b"] = m.group(2).strip()
        elif params["query_type"] == "notification_gt":
            params["threshold_days"] = _extract_notification_threshold(q)
        elif params["query_type"] not in ("no_notification", "personal_calendar"):
            # Skip the "for X" loose fallback when a period_id was found —
            # ("period name for period ID 107") would otherwise re-capture
            # "period ID 107" itself as a bogus period_name.
            params["period_name"] = _extract_period(q) or (
                None if params["period_id"] else _extract_period_name_loose(q))
            if not params["query_type"]:
                params["field"] = _first_match(q, _PERIOD_FIELD_PATTERNS)

    if intent == Intent.USER_FIELD:
        for field, pat in _USER_FIELD_PATTERNS.items():
            if re.search(pat, q, re.IGNORECASE):
                params["field"] = field
                break

    if intent == Intent.USER_LIST:
        params["query_type"] = _extract_query_type(q, _USER_QUERY_TYPE_PATTERNS)

    if intent == Intent.DEPARTMENT_LIST:
        params["query_type"] = _extract_query_type(q, _DEPARTMENT_QUERY_TYPE_PATTERNS)
        if params["query_type"] == "top_n":
            params["top_n"] = _extract_top_n(q)

    if intent == Intent.PERIOD_LIST:
        params["query_type"] = _first_match(q, _PERIOD_LIST_QUERY_TYPE_PATTERNS)

    if intent == Intent.ROLE_LIST:
        params["query_type"] = _extract_query_type(q, _ROLE_QUERY_TYPE_PATTERNS)
        if params["query_type"] == "exists":
            name = explicit or _extract_role_name_loose(q)
            if name:
                # "is there a role called X IN THE SYSTEM?" — the after-
                # keyword fallback's stop-word set doesn't cover "in", so it
                # otherwise swallows the trailing "in the system" clause
                # into the role name itself.
                name = re.sub(r"\s+in\s+(the\s+)?system\b.*$", "", name, flags=re.IGNORECASE).strip() or None
            params["target_role"] = name

    if intent == Intent.SUBMISSION_LIST:
        params["status"] = _first_match(q, _SUBMISSION_STATUS_PATTERNS)

    if intent == Intent.MENU_LIST:
        params["query_type"] = _first_match(q, _MENU_QUERY_TYPE_PATTERNS)

    if intent == Intent.PERMISSION_PROFILE:
        if re.search(r"not\s+have\s+access|NOT\s+have\s+access", q, re.IGNORECASE):
            params["query_type"] = "not_access"
        elif re.search(r"full\s+control|control\s+over", q, re.IGNORECASE):
            params["query_type"] = "full_control"

    if intent == Intent.ROLE_MODULE_ACCESS:
        if re.search(r"full\s+control|control\s+over", q, re.IGNORECASE):
            params["query_type"] = "full_control"

    if intent == Intent.DEPT_RETURN_ACCESS_MATRIX:
        if re.search(r"accessible\s+by\s+all\s+departments?", q, re.IGNORECASE):
            params["query_type"] = "all_departments"
        elif re.search(r"maximum\s+number\s+of\s+departments?|accessible\s+by\s+the\s+most", q, re.IGNORECASE):
            params["query_type"] = "max_access"

    if intent == Intent.ROLES_WITH_PERMISSION:
        if re.search(r"full\s+access", q, re.IGNORECASE):
            params["query_type"] = "full_access"
        elif re.search(r"no\s+edit\s+or\s+create|no\s+create\s+or\s+edit|"
                        r"no\s+(edit|create)\s+(or\s+(edit|create)\s+)?permissions?\s+at\s+all",
                        q, re.IGNORECASE):
            params["query_type"] = "no_edit_create"
        elif re.search(r"view[\s-]?only", q, re.IGNORECASE):
            params["query_type"] = "view_only"

    if intent in (Intent.PERMISSION_CHECK, Intent.ROLE_MODULE_ACCESS, Intent.ROLES_WITH_PERMISSION):
        module = None
        for pat, canonical in _MODULE_SYNONYMS:
            # "role"/"roles" is ambiguous: it's a real module ("Roles" in
            # the actual OptionName data — "which roles can I create?"),
            # but it's just as often the word naming the TARGET role
            # ("what modules can the admin role create?"), already
            # captured into target_role above. Self-test found the latter
            # phrasing wrongly extracting module="role" — skip this one
            # synonym when target_role is already set, since that's a
            # strong signal "role" was consumed naming the subject, not
            # requesting a module.
            if canonical == "role" and params.get("target_role"):
                continue
            if pat.search(q):
                module = canonical
                break
        if module is None:
            # Only a bare "... module" phrasing gives a reliable module name
            # this way — "on"/"to" are too generic and swallow the action
            # verb itself (e.g. "edit department settings" -> "edit
            # department settings" instead of just the module).
            # "the NOTIFICATION module" — ported from my-nlp-changes. The
            # name sits BEFORE the bare word "module", which
            # _extract_after_kw (after-only) cannot see, so any module named
            # this way that isn't in _MODULE_SYNONYMS above fell through to
            # "no module" entirely. Tried only after the synonym table has
            # missed, so it can never preempt a canonical mapping.
            before_m = re.search(r"\b([A-Za-z][A-Za-z0-9_\-]{1,30})\s+module\b", q, re.IGNORECASE)
            if before_m and before_m.group(1).lower() not in _NOT_AN_ENTITY_NAME | {"a", "any", "this", "that"}:
                module = before_m.group(1)
            else:
                # Only a bare "... module" phrasing gives a reliable module
                # name this way — "on"/"to" are too generic and swallow the
                # action verb itself (e.g. "edit department settings" ->
                # "edit department settings" instead of just the module).
                module = _extract_after_kw(q, "module")
        params["module"] = module

    return {k: v for k, v in params.items() if v is not None}
