"""Intent classifier for the app-DB question answering layer.

Maps a natural-language question to one of the structured intents defined below.
Uses pure regex/keyword matching — no embeddings, no LLM, no latency.

Return value of ``classify()``:
    (intent_name: str, params: dict)

``params`` may contain any subset of:
    target_user   str  — a user name / login ID mentioned in the question
    target_dept   str  — a department name mentioned
    target_role   str  — a role name mentioned
    target_return str  — an XBRL / non-XBRL return name mentioned
    target_action str  — permission action (new, edit, view, approve)
    period_name   str  — period/frequency name (daily, monthly, …)
"""
from __future__ import annotations

import re

# ── constants ────────────────────────────────────────────────────────────────

# Permission action keywords → attribute name in XML_RoleAccess.xml
ACTION_MAP = {
    "new": "HasNew", "create": "HasNew", "add": "HasNew",
    "edit": "HasEdit", "update": "HasEdit", "modify": "HasEdit",
    "view": "HasView", "see": "HasView", "read": "HasView",
    "approve": "HasApprove", "approval": "HasApprove",
}

# Period keywords → PeriodName in XML_Period.xml  (lower → canonical)
PERIOD_ALIASES: dict[str, str] = {
    "daily": "Daily", "day": "Daily",
    "weekly": "Weekly", "week": "Weekly",
    "monthly": "Monthly", "month": "Monthly",
    "quarterly": "Quarterly", "quarter": "Quarterly",
    "half": "HalfYearly", "halfyearly": "HalfYearly", "half-yearly": "HalfYearly",
    "yearly": "Yearly", "annual": "Yearly", "year": "Yearly",
    "bi-monthly": "BiMonthly", "bimonthly": "BiMonthly",
    "fortnightly": "Fortnightly",
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
            rf"\b{re.escape(kw)}\b\s+(?:called\s+|named\s+)?([A-Za-z0-9_.\-\s()]{{1,40}}?)(?:\?|$|\sis\b|\shas\b|\sand\b)",
            text,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
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
    """True if the question references the current user (me/my/I/myself)."""
    return bool(re.search(r"\b(my|me|i|myself|mine|i am|i've|i have)\b", text, re.IGNORECASE))


# ── intent rule definitions ──────────────────────────────────────────────────
#
# Each rule is a tuple:
#   (intent_name, pattern_or_list_of_patterns, param_extractor_fn | None)
#
# Rules are evaluated top-to-bottom; first match wins.
# ``pattern`` is a regex applied to the lower-cased question.

def _mk(intent: str, *patterns: str, extractor=None):
    return (intent, [re.compile(p, re.IGNORECASE) for p in patterns], extractor)


_RULES: list[tuple[str, list[re.Pattern], object]] = [

    # ── Bank & Segment (very specific, check first) ──────────────────────────
    _mk("BANK_INFO",
        r"\bbank\b.*(name|code|type|detail|crr|ifsc)",
        r"(name|type|code|crr).*(bank)",
        r"\bbank\b"),

    _mk("SEGMENT_INFO",
        r"\b(segment|scenario)\b.*(type|defin|config|differ)",
        r"(type|defin|how many).*(segment|scenario)",
        r"\b(segment|scenario)\b"),

    # ── MY PROFILE questions (self-service, check before generic USER) ───────
    # More-specific intents MUST come before MY_PROFILE (which matches "my account" broadly)
    # and before MY_STATUS (which matches "my account active")
    _mk("MY_CREATED_DATE",
        r"\bwhen\s+(was|did)\s+(my\s+)?(account|profile|user)\s+creat",
        r"\bwho\s+creat\w*\s+my\s+(account|profile|user)\b",
        r"\bmy\s+account\s+was\s+creat"),

    _mk("MY_PASSWORD_DATE",
        r"\bwhen\s+did\s+i\s+(last\s+)?(update|change|reset)\s+(my\s+)?password\b",
        r"\bmy\s+(last\s+)?password\s+(change|update|reset)\b"),

    _mk("MY_LOGIN_ID",
        r"\bmy\s+(login\s*id|username|user\s*name)\b",
        r"\bwhat\s+is\s+my\s+(login\s*id|username)\b"),

    _mk("MY_USER_CODE",
        r"\bmy\s+user\s*code\b",
        r"\bwhat\s+is\s+my\s+(user\s*)?code\b"),

    _mk("MY_USER_LEVEL",
        r"\bmy\s+(user\s+)?level\b",
        r"\bwhat\s+(is|level)\s+(my|user)\s+level\b"),

    _mk("MY_STATUS",
        r"\b(is|my)\s+(my\s+)?(account|profile)\s*(currently\s+)?(active|enabled|disabled|locked|status)\b",
        r"\bmy\s+account\s+status\b",
        r"\bam\s+i\s+(currently\s+)?(active|enabled|disabled)\b"),

    _mk("MY_PROFILE",
        r"\bmy\s+(profile|account|detail|info|summary)\b",
        r"\bwho\s+am\s+i\b",
        r"\bmy\s+user\s+(info|data|record)\b"),

    _mk("MY_DEPARTMENT",
        r"\bmy\s+(department|dept)\b",
        r"\bwhich\s+department\s+(am\s+i|i\s+belong|i\s+am)"),

    _mk("MY_ROLE",
        r"\bmy\s+role\b",
        r"\bwhat\s+role\s+(am\s+i|do\s+i\s+have|have\s+i)\b"),

    _mk("MY_EMAIL",
        r"\bmy\s+email\b",
        r"\bemail\s+(address|id).*\bmy\b",
        r"\bmy\s+(email address|email id)\b"),

    _mk("MY_MOBILE",
        r"\bmy\s+(mobile|phone|contact)\s*(number)?\b"),

    _mk("MY_LAST_LOGIN",
        r"\b(my|i)\s+(last\s+log|last\s+login|last\s+logged|last\s+signed)\b",
        r"\bwhen\s+did\s+i\s+(last\s+)?(log\s*in|sign\s*in|login)\b"),

    _mk("MY_FAILED_LOGINS",
        r"\bmy\s+(failed|wrong)\s*(login|password)\s*(count|attempt|number)?\b",
        r"\bhow\s+many\s+failed.*\bmy\b"),

    _mk("MY_ROLE_PEER_COUNT",
        r"\bhow\s+many\s+(other\s+)?(users?|people).*(same|my)\s+role\b",
        r"\bhow\s+many\s+(users?|people)\s+(share|have|with)\s+(my|same)\s+role\b"),

    _mk("MY_ROLE_PERMISSIONS",
        r"\bmy\s+(permission|access|privilege|module|right)\b",
        r"\bwhat\s+can\s+i\s+(do|access|see|create|edit|approve)\b",
        r"\bcan\s+i\s+(create|edit|view|see|approve|add|update)\b",
        r"\bdo\s+i\s+have\s+(access|permission|right)\b"),

    _mk("MY_DEPT_RETURNS",
        r"\bmy\s+(department|dept).*(return|form|report)\b",
        r"\b(return|form|report).*\bmy\s+(department|dept)\b",
        r"\bwhich\s+returns?\s+(can\s+i|i\s+can|am\s+i\s+able)\b"),

    _mk("MY_SUBMISSIONS",
        r"\bmy\s+(submission|instance|filing|report|upload)\b",
        r"\b(submission|instance|filing).*\bi\s+(made|submitted|uploaded|filed)\b",
        r"\bwhat\s+(have|did)\s+i\s+(submit|upload|file|report)\b"),

    # ── USER admin questions ─────────────────────────────────────────────────
    _mk("USER_LIST_ACTIVE",
        r"\b(list|show|get|who are|give me).*(active|enabled)\s+users?\b",
        r"\bactive\s+users?\b"),

    _mk("USER_LIST_INACTIVE",
        r"\b(list|show|get|who are|give me).*(inactive|disabled)\s+users?\b",
        r"\b(inactive|disabled)\s+users?\b",
        r"\bwhich\s+users?\s+(are\s+)?(inactive|disabled)\b"),

    _mk("USER_NEVER_LOGIN",
        r"\busers?\s+(who\s+)?(have\s+)?(never|not)\s+(logged|log)\s*in\b",
        r"\bnever\s+logged\s*in\b"),

    _mk("USER_FAILED_LOGIN",
        r"\busers?\s+(with|having)\s+failed\s+(login|password)\b",
        r"\bfailed\s+login\s+(attempt|count)s?\b",
        r"\bwhich\s+users?\s+have\s+failed\b"),

    _mk("USER_DUPLICATE_EMAIL",
        r"\bduplicate\s+email\b",
        r"\bsame\s+email\b",
        r"\bshared\s+email\b"),

    _mk("USER_COUNT",
        r"\bhow\s+many\s+(\w+\s+)?users?\b",   # "how many active users", "how many inactive users"
        r"\btotal\s+(number\s+of\s+)?users?\b",
        r"\bcount\s+of\s+users?\b",
        r"\buser\s+count\b"),

    _mk("USER_BY_DEPT",
        r"\busers?\s+(in|of|for|belonging\s+to|from)\s+(department|dept)\b",
        r"\b(department|dept)\s+\S+\s+(user|member|staff)\b",
        r"\bwhich\s+users?\s+(belong|are)\s+(to|in)\s+(department|dept)\b"),

    _mk("USER_BY_ROLE",
        r"\busers?\s+(with|having|assigned)\s+role\b",
        r"\bwho\s+(has|have|is\s+assigned)\s+(role|the\s+role)\b",
        r"\bwhich\s+users?\s+(have|are\s+assigned)\s+(the\s+)?role\b"),

    _mk("USER_LIST",
        r"\b(list\s+all|all|show\s+all|get\s+all)\s+users?\b",
        r"\busers?\s+(list|listing)\b"),

    _mk("USER_PROFILE",
        r"\b(detail|profile|info|summary)\s+(of|about|for)\s+user\b",
        r"\buser\s+(detail|profile|info)\b",
        r"\bwhat\s+(are|is)\s+the\s+details?\s+(of|for|about)\s+user\b",
        r"\bwhen\s+(was|did)\s+user\b",
        r"\bwho\s+created\s+user\b",
        r"\bwho\s+is\s+\S+\b"),                              # "who is iris810"

    # ── DEPARTMENT ───────────────────────────────────────────────────────────
    _mk("DEPT_RETURNS",
        r"\b(return|form|report)s?\s+(assigned\s+to|of|for|in)\s+(department|dept)\b",
        r"\b(department|dept)\s+\S+\s+(return|form|report)\b",
        r"\bwhat\s+returns?\s+does\s+(department|dept)\b",
        r"\bwhich\s+(xbrl\s+|non.?xbrl\s+)?returns?\s+(are\s+)?(assigned\s+to|for)\s+(department|dept)\b"),  # "which XBRL returns assigned to dept"

    _mk("DEPT_LIST",
        r"\b(list|all|show)\s+(all\s+)?(department|dept)s?\b",
        r"\b(department|dept)s?\s+(list|listing)\b",
        r"\bwhat\s+are\s+(all\s+)?(the\s+)?(departments?|dept)s?\b",
        r"\bwhich\s+(departments?|dept)s?\s+(are|exist|are\s+there)\b",
        r"\bwhat\s+(departments?|dept)s?\s+(are|exist)\b",
        r"\bhow\s+many\s+(departments?|depts?)\b",                           # "how many departments"
        r"\bwhich\s+department\s+has\s+(the\s+)?(most|fewest|highest|lowest)\b",  # rankings
        r"\bwhich\s+departments?\s+have\s+(no|zero|the\s+most|the\s+fewest)\s+returns?\b"),  # dept stats

    _mk("DEPT_INFO",
        r"\b(detail|profile|info)\s+(of|about|for)\s+(department|dept)\b",
        r"\b(department|dept)\s+(info|detail|email|status)\b"),

    # ── ROLE ─────────────────────────────────────────────────────────────────
    _mk("PERMISSION_CHECK",
        r"\bcan\s+(role\s+)?\S+\s+(create|edit|view|see|approve|add|update)\b",
        r"\bdoes\s+(role\s+)?\S+\s+have\s+(permission|access|right)\b",
        r"\b(has|have)\s+(role\s+)?\S+\s+(new|edit|view|approve)\s+(permission|access)\b"),

    _mk("ROLE_PERMISSIONS",
        r"\b(permission|access|privilege|right)s?\s+(of|for)\s+role\b",
        r"\bwhat\s+can\s+role\b",
        r"\brole\s+\S+\s+(permission|access|privilege|right|can)\b",
        r"\bwhat\s+(module|option)s?\s+does\s+role\b"),

    _mk("ROLE_USERS",
        r"\bwho\s+(has|have)\s+(the\s+)?role\b",
        r"\busers?\s+(of|with|assigned\s+to)\s+(the\s+)?role\b"),

    _mk("MY_ROLE_PEER_COUNT",
        r"\bhow\s+many\s+(other\s+)?(users?|people).*(same|my)\s+role\b",
        r"\bhow\s+many\s+(users?|people)\s+(share|have|with)\s+(my|same)\s+role\b"),

    _mk("ROLE_LIST",
        r"\b(list|all|show)\s+(all\s+)?roles?\b",
        r"\broles?\s+(list|listing)\b",
        r"\bwhat\s+roles?\s+(are|exist|available)\b",
        r"\bwhich\s+roles?\s+(are|exist|are\s+there)\b",    # "which roles are active"
        r"\bhow\s+many\s+roles?\b"),                         # "how many roles"

    # ── PERIOD ───────────────────────────────────────────────────────────────
    _mk("USER_LEVEL_LIST",
        r"\b(list|all|show)\s+(all\s+)?(user\s+)?levels?\b",
        r"\bwhat\s+(user\s+)?levels?\s+(are|exist|defined)\b",
        r"\bhow\s+many\s+(user\s+)?levels?\b"),

    _mk("PERIOD_LIST",
        r"\b(list|all|show)\s+(all\s+)?(period|frequency|frequencies)\b",
        r"\bwhat\s+(period|frequency)\b",
        r"\breporting\s+(period|frequency)\b",
        r"\b(advance\s+notification|notification\s+days)\b"),

    # ── RETURNS (XBRL) ───────────────────────────────────────────────────────
    _mk("RETURNS_BY_PERIOD",
        r"\b(daily|weekly|monthly|quarterly|half.?yearly|yearly|annual|fortnightly)\s+(return|form|report)s?\b",
        r"\b(return|form|report)s?\s+(with|for|having)\s+(period|frequency)\b"),

    _mk("VALIDATION_RETURNS",
        r"\b(formula|schema.?calc|schema\s+calculation|schema\s+calc)\s+validation\b",
        r"\bvalidation\s+(enabled|config|rule|check)s?\b",
        r"\bwhich\s+returns?\s+(have|use|enable)\s+(validation|formula|schema)\b",
        r"\bcross.?report\s+validation\b",
        r"\blarge\s+validator\b"),

    _mk("RETURNS_DETAILS",
        r"\bdetails?\s+(of|about|for)\s+return\b",
        r"\breturn\s+\S+\s+(info|detail|config|status|version)\b",
        r"\bwhat\s+is\s+return\s+\S+\b"),

    _mk("RETURNS_LIST",
        r"\b(list|all|show)\s+(all\s+)?(xbrl\s+)?returns?\b",
        r"\bxbrl\s+returns?\b",
        r"\breturns?\s+(list|listing)\b",
        r"\bwhat\s+returns?\s+(are|exist|available)\b"),

    # ── NON-XBRL ─────────────────────────────────────────────────────────────
    _mk("NON_XBRL_LIST",
        r"\bnon.?xbrl\s+returns?\b",
        r"\bnon.?xbrl\b"),

    # ── INSTANCE LOG (submissions) ───────────────────────────────────────────
    _mk("SUBMISSION_PENDING",
        r"\bpending\s+(submission|instance|filing|report)s?\b",
        r"\b(submission|instance|filing)s?\s+(not\s+yet|still\s+)?approved\b",
        r"\bnew\s+submission\b"),

    _mk("SUBMISSION_APPROVED",
        r"\bapproved\s+(submission|instance|filing|report)s?\b",
        r"\b(submission|instance|filing)s?\s+(that\s+(are|were)\s+)?approved\b"),

    _mk("SUBMISSION_STATUS",
        r"\bstatus\s+(of|for)\s+(submission|instance|return|filing)\b",
        r"\b(submission|instance|filing)\s+status\b",
        r"\bwhat\s+is\s+the\s+status\s+of\b"),

    _mk("SUBMISSION_LIST",
        r"\b(list|all|show)\s+(all\s+)?submission\b",
        r"\ball\s+(instance|filing|report)s?\b",
        r"\bfull\s+(submission|instance)\s+log\b"),

    # ── MENU / MODULES ───────────────────────────────────────────────────────
    _mk("NOTIFICATION_LIST",
        r"\b(notification|alert|reminder)s?\b",
        r"\bsms\s+(reminder|notification|alert)\b",
        r"\badvance\s+notification\b"),

    # ── AUDIT / SECURITY / LOGS ───────────────────────────────────────────────
    # Self-service: what I did / my uploads / my cross-val
    _mk("MY_AUDIT_LOG",
        r"\b(what\s+)?(change|action|activit|modification)s?\s+(have\s+i|i\s+made|i\s+took)\b",
        r"\bmy\s+(activit|audit|change|action|histor)\b",
        r"\bshow\s+my\s+(activit|audit|histor)\b"),

    _mk("MY_UPLOAD_LOG",
        r"\b(my|have\s+any)\s+(file\s+)?(upload)s?\b",
        r"\b(file|upload)\s+(log|histor|fail)\b"),

    _mk("MY_CROSS_VAL_LOG",
        r"\bmy\s+(cross.?val|cross\s+validation)\b",
        r"\bcross.?validation\s+(error|log|result)s?\s+(for\s+my|my)\b"),

    # Admin: audit trail / upload log / cross-val log
    _mk("AUDIT_LOG",
        r"\baudit\s+(log|trail|histor)\b",
        r"\b(who|what).*(modif|creat|delet|updat|approv).*audit\b",
        r"\bshow.*(audit|change)s?\s+(for|of|by)\b",
        r"\bwhich\s+users?\s+(have\s+)?deactivat\b",
        r"\bpassword\s+reset\b"),

    _mk("CROSS_VAL_LOG",
        r"\bcross.?report\s+validation\b",
        r"\bcross.?validation\s+(error|log|result|config)\b",
        r"\bdisabled\s+returns?\b"),

    _mk("UPLOAD_LOG",
        r"\bfile\s+upload\s+(fail\w*|log|error)\b",
        r"\bwhich\s+(file|upload)s?\s+fail\w*\b",
        r"\bupload\s+(fail\w*|log|error)\b"),

    _mk("MENU_LIST",
        r"\b(menu|module|option)s?\s+(list|listing|available)\b",
        r"\b(list|all|show)\s+(all\s+)?(menu|module|option)s?\b",
        r"\bwhat\s+(menu|module|option)s?\s+(are|exist|available|does)\b",
        r"\bsystem\s+(module|menu)\b"),

    # ── catch-all ────────────────────────────────────────────────────────────
    _mk("UNKNOWN", r".*"),
]


# ── public API ───────────────────────────────────────────────────────────────

def classify(question: str) -> tuple[str, dict]:
    """Return ``(intent_name, params_dict)`` for *question*.

    All keys in ``params`` are optional; callers should use ``.get()``.
    """
    from backend.utils.debug import debug_log

    q = question.strip()

    # ── Debug trace: log what we are classifying ─────────────────────────────
    debug_log("INTENT CLASSIFIER", normalized_question=q)

    patterns_checked = 0
    for intent, patterns, _ in _RULES:
        for pat in patterns:
            patterns_checked += 1
            if pat.search(q):
                params = _extract_params(intent, q)
                if intent == "UNKNOWN":
                    # Catch-all rule — no specific intent was recognised
                    debug_log(
                        "INTENT NOT MATCHED \u2192 UNKNOWN",
                        question=q,
                        patterns_checked=patterns_checked,
                        fallback_reason="Catch-all rule matched \u2014 no specific intent found",
                    )
                else:
                    debug_log(
                        "INTENT MATCHED",
                        intent=intent,
                        matched_pattern=pat.pattern[:80],
                        patterns_checked=patterns_checked,
                        extracted_params=params or "{}",
                    )
                return intent, params

    return "UNKNOWN", {}


def _extract_params(intent: str, q: str) -> dict:
    """Extract entity parameters relevant to *intent* from the question."""
    params: dict = {}

    # Quoted / bracketed entity (highest confidence)
    explicit = _extract_quoted_or_bracketed(q)

    if intent in ("USER_PROFILE", "USER_BY_DEPT", "USER_BY_ROLE",
                  "USER_LIST_ACTIVE", "USER_LIST_INACTIVE", "USER_FAILED_LOGIN",
                  "USER_NEVER_LOGIN"):
        # Try to extract a target username after "user" keyword
        params["target_user"] = (
            explicit
            or _extract_after_kw(q, "user", "for user", "of user", "about user")
        )

    if intent in ("DEPT_INFO", "DEPT_RETURNS", "USER_BY_DEPT"):
        params["target_dept"] = (
            explicit
            or _extract_after_kw(q, "department", "dept")
        )

    if intent in ("ROLE_PERMISSIONS", "ROLE_USERS", "PERMISSION_CHECK",
                  "USER_BY_ROLE"):
        params["target_role"] = (
            explicit
            or _extract_after_kw(q, "role")
        )

    if intent in ("RETURNS_DETAILS", "DEPT_RETURNS", "SUBMISSION_STATUS",
                  "SUBMISSION_LIST", "RETURNS_BY_PERIOD"):
        params["target_return"] = (
            explicit
            or _extract_after_kw(q, "return", "form", "report")
        )

    if intent in ("PERMISSION_CHECK", "MY_ROLE_PERMISSIONS"):
        params["target_action"] = _extract_action(q)

    if intent in ("RETURNS_BY_PERIOD", "PERIOD_LIST"):
        params["period_name"] = _extract_period(q)

    # Strip None values to keep params clean
    return {k: v for k, v in params.items() if v is not None}
