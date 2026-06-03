"""Intent definitions — wires all existing query handlers into the IntentRegistry.

This module builds a singleton ``REGISTRY`` that maps normalised user queries
to the handler functions in ``backend.db_qa.query_handlers``.

Import and use::

    from backend.db_qa.intents.definitions import REGISTRY

    intent, match = REGISTRY.match(normalized_query)
"""
from __future__ import annotations

from backend.db_qa.intents.registry import IntentRegistry
import backend.db_qa.query_handlers as _h

REGISTRY = IntentRegistry()

# ─────────────────────────────────────────────────────────────────────────────
# SELF-SERVICE — MY PROFILE / ACCOUNT (no admin required, priority 10-19)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="MY_PROFILE",
    patterns=[
        r"\bmy\s+profile\b",
        r"\bmy\s+(account|info(rmation)?|details?)\b",
        r"\bwho\s+am\s+i\b",
        r"\babout\s+me\b",
    ],
    handler=_h.handle_my_profile,
    priority=10,
    description="Show my profile / account details",
    examples=["what is my profile", "show my account details"],
)

REGISTRY.register(
    name="MY_DEPARTMENT",
    patterns=[
        r"\bmy\s+department\b",
        r"\bmy\s+dept\b",
        r"\bwhich\s+department\s+am\s+i\b",
        r"\bwhat\s+department\s+do\s+i\b",
    ],
    handler=_h.handle_my_department,
    priority=11,
    description="Show my department",
    examples=["what is my department", "which department am I in"],
)

REGISTRY.register(
    name="MY_ROLE",
    patterns=[
        r"\bmy\s+role\b",
        r"\bwhat\s+role\s+do\s+i\b",
        r"\bmy\s+access\s+role\b",
    ],
    handler=_h.handle_my_role,
    priority=11,
    description="Show my assigned role",
    examples=["what is my role", "show my role"],
)

REGISTRY.register(
    name="MY_EMAIL",
    patterns=[
        r"\bmy\s+email\b",
        r"\bmy\s+email\s+address\b",
        r"\bwhat\s+is\s+my\s+email\b",
    ],
    handler=_h.handle_my_email,
    priority=12,
    description="Show my email address",
    examples=["what is my email", "my email address"],
)

REGISTRY.register(
    name="MY_MOBILE",
    patterns=[
        r"\bmy\s+mobile\b",
        r"\bmy\s+(phone|contact)\s*number\b",
    ],
    handler=_h.handle_my_mobile,
    priority=12,
    description="Show my mobile number",
    examples=["what is my mobile number"],
)

REGISTRY.register(
    name="MY_LAST_LOGIN",
    patterns=[
        r"\bmy\s+last\s+login\b",
        r"\bwhen\s+did\s+i\s+(last\s+)?log\s*(in|ged)\b",
        r"\bmy\s+login\s+history\b",
    ],
    handler=_h.handle_my_last_login,
    priority=12,
    description="Show my last login time",
    examples=["when did I last login", "my last login"],
)

REGISTRY.register(
    name="MY_FAILED_LOGINS",
    patterns=[
        r"\bmy\s+failed\s+login\b",
        r"\bfailed\s+login\s+(attempts?|count)?\s*for\s+me\b",
        r"\bhow\s+many\s+failed\s+logins?\s+do\s+i\b",
    ],
    handler=_h.handle_my_failed_logins,
    priority=12,
    description="Show my failed login attempts",
    examples=["how many failed logins do I have", "my failed login count"],
)

REGISTRY.register(
    name="MY_STATUS",
    patterns=[
        r"\bmy\s+(account\s+)?status\b",
        r"\bis\s+my\s+account\s+(active|enabled|disabled)\b",
    ],
    handler=_h.handle_my_status,
    priority=12,
    description="Show my account status (active/inactive)",
    examples=["is my account active", "my account status"],
)

REGISTRY.register(
    name="MY_CREATED_DATE",
    patterns=[
        r"\bwhen\s+(was\s+)?my\s+account\s+created\b",
        r"\bmy\s+(account\s+)?creation\s+date\b",
        r"\bmy\s+registration\s+date\b",
    ],
    handler=_h.handle_my_created_date,
    priority=12,
    description="Show when my account was created",
    examples=["when was my account created", "my account creation date"],
)

REGISTRY.register(
    name="MY_LOGIN_ID",
    patterns=[
        r"\bmy\s+login\s+(id|name|username)\b",
        r"\bwhat\s+is\s+my\s+(login|username)\b",
    ],
    handler=_h.handle_my_login_id,
    priority=12,
    description="Show my login ID",
    examples=["what is my login ID", "my username"],
)

REGISTRY.register(
    name="MY_USER_CODE",
    patterns=[
        r"\bmy\s+user\s+code\b",
        r"\bmy\s+code\b",
    ],
    handler=_h.handle_my_user_code,
    priority=13,
    description="Show my user code",
    examples=["what is my user code", "my code"],
)

REGISTRY.register(
    name="MY_PASSWORD_DATE",
    patterns=[
        r"\bmy\s+password\s+date\b",
        r"\bwhen\s+(did\s+i|was\s+my)\s+password\s+(change|update|reset)\b",
        r"\blast\s+password\s+(change|update)\b",
    ],
    handler=_h.handle_my_password_date,
    priority=13,
    description="Show when my password was last updated",
    examples=["when was my password last changed", "my password date"],
)

REGISTRY.register(
    name="MY_USER_LEVEL",
    patterns=[
        r"\bmy\s+(user\s+)?level\b",
        r"\bwhat\s+level\s+am\s+i\b",
        r"\bam\s+i\s+(l1|l2|l3)\b",
    ],
    handler=_h.handle_my_user_level,
    priority=13,
    description="Show my user level (L1/L2/L3)",
    examples=["what is my user level", "am I L1 or L2"],
)

REGISTRY.register(
    name="MY_ROLE_PEER_COUNT",
    patterns=[
        r"\bhow\s+many\s+users?\s+(have|with)\s+my\s+role\b",
        r"\bwho\s+(else\s+)?has\s+my\s+role\b",
        r"\bother\s+users?\s+with\s+(my|same)\s+role\b",
    ],
    handler=_h.handle_my_role_peer_count,
    priority=14,
    description="Show other users who share my role",
    examples=["who else has my role", "how many users have my role"],
)

REGISTRY.register(
    name="MY_ROLE_PERMISSIONS",
    patterns=[
        r"\bmy\s+(role\s+)?permissions?\b",
        r"\bwhat\s+(can|modules?)\s+can\s+i\s+access\b",
        r"\bmy\s+access\s+(rights?|permissions?)\b",
    ],
    handler=_h.handle_my_role_permissions,
    priority=14,
    description="Show my role permissions and accessible modules",
    examples=["what are my permissions", "which modules can I access"],
)

REGISTRY.register(
    name="MY_DEPT_RETURNS",
    patterns=[
        r"\bmy\s+department\s+returns?\b",
        r"\breturns?\s+(assigned\s+to\s+)?my\s+department\b",
        r"\bmy\s+dept\s+reports?\b",
    ],
    handler=_h.handle_my_dept_returns,
    priority=14,
    description="Show returns assigned to my department",
    examples=["what returns are in my department", "my department reports"],
)

REGISTRY.register(
    name="MY_SUBMISSIONS",
    patterns=[
        r"\bmy\s+submissions?\b",
        r"\bmy\s+(filing|instance|report)\s+history\b",
        r"\bsubmissions?\s+by\s+me\b",
        r"\bwhat\s+have\s+i\s+submitted\b",
    ],
    handler=_h.handle_my_submissions,
    priority=14,
    description="Show my submission history",
    examples=["show my submissions", "what have I submitted"],
)

REGISTRY.register(
    name="MY_AUDIT_LOG",
    patterns=[
        r"\bmy\s+audit\s+(log|history|trail)\b",
        r"\bmy\s+activity\s+(log|history)\b",
        r"\bwhat\s+changes?\s+(have\s+)?i\s+made\b",
    ],
    handler=_h.handle_my_audit_log,
    priority=15,
    description="Show my audit / activity history",
    examples=["show my audit log", "what changes have I made"],
)

REGISTRY.register(
    name="MY_UPLOAD_LOG",
    patterns=[
        r"\bmy\s+(file\s+)?upload\s+(log|history)\b",
        r"\bfiles?\s+(i\s+)?(uploaded|submitted)\b",
    ],
    handler=_h.handle_my_upload_log,
    priority=15,
    description="Show my file upload history",
    examples=["show my upload log", "files I uploaded"],
)

REGISTRY.register(
    name="MY_CROSS_VAL_LOG",
    patterns=[
        r"\bmy\s+cross[\s_-]?validat\w*\b",
        r"\bcross[\s_-]?validation\s+(errors?|results?)\s+(for\s+)?me\b",
    ],
    handler=_h.handle_my_cross_validation_log,
    priority=15,
    description="Show my cross-validation results",
    examples=["my cross validation errors", "cross validation results for me"],
)

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — USER MANAGEMENT (priority 20-29)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="USER_LIST_ACTIVE",
    patterns=[
        r"\bactive\s+users?\b",
        r"\blist\s+active\s+users?\b",
        r"\bshow\s+active\s+users?\b",
    ],
    handler=_h.handle_user_list_active,
    priority=20,
    requires_admin=True,
    description="List all active users",
    examples=["list active users", "show active users"],
)

REGISTRY.register(
    name="USER_LIST_INACTIVE",
    patterns=[
        r"\binactive\s+users?\b",
        r"\bdisabled\s+users?\b",
        r"\blist\s+(inactive|disabled)\s+users?\b",
    ],
    handler=_h.handle_user_list_inactive,
    priority=20,
    requires_admin=True,
    description="List all inactive / disabled users",
    examples=["list inactive users", "show disabled users"],
)

REGISTRY.register(
    name="USER_COUNT",
    patterns=[
        r"\bhow\s+many\s+users?\b",
        r"\buser\s+count\b",
        r"\btotal\s+users?\b",
        r"\bnumber\s+of\s+users?\b",
    ],
    handler=_h.handle_user_count,
    priority=21,
    requires_admin=True,
    description="Count total / active / inactive users",
    examples=["how many users are there", "total user count"],
)

REGISTRY.register(
    name="USER_LIST",
    patterns=[
        r"\blist\s+(all\s+)?users?\b",
        r"\bshow\s+(all\s+)?users?\b",
        r"\ball\s+users?\b",
    ],
    handler=_h.handle_user_list,
    priority=22,
    requires_admin=True,
    description="List all users",
    examples=["list all users", "show all users"],
)

REGISTRY.register(
    name="USER_PROFILE",
    patterns=[
        r"\bprofile\s+(of|for)\s+\w+",
        r"\buser\s+(details?|info)\s+(of|for)\s+\w+",
        r"\bshow\s+user\s+\w+",
        r"\bwho\s+is\s+\w+",
    ],
    handler=_h.handle_user_profile,
    priority=23,
    requires_admin=True,
    description="Show a specific user's profile",
    examples=["show profile of John", "who is iris810"],
)

REGISTRY.register(
    name="USER_BY_DEPT",
    patterns=[
        r"\busers?\s+in\s+(the\s+)?\w+\s+department\b",
        r"\busers?\s+(from|belonging\s+to)\s+(the\s+)?department\b",
        r"\bwhich\s+users?\s+are\s+in\s+\w+",
    ],
    handler=_h.handle_user_by_dept,
    priority=24,
    requires_admin=True,
    description="List users in a specific department",
    examples=["users in Finance department", "list users in IT"],
)

REGISTRY.register(
    name="USER_BY_ROLE",
    patterns=[
        r"\busers?\s+with\s+(role|access)\s+\w+",
        r"\busers?\s+having\s+role\s+\w+",
        r"\bwhich\s+users?\s+have\s+role\b",
    ],
    handler=_h.handle_user_by_role,
    priority=24,
    requires_admin=True,
    description="List users with a specific role",
    examples=["users with Admin role", "which users have maker role"],
)

REGISTRY.register(
    name="USER_NEVER_LOGIN",
    patterns=[
        r"\busers?\s+(who\s+)?(have\s+)?never\s+logged?\s*(in)?\b",
        r"\busers?\s+without\s+(any\s+)?login\b",
        r"\bnever\s+logged\s+in\b",
    ],
    handler=_h.handle_user_never_login,
    priority=25,
    requires_admin=True,
    description="List users who have never logged in",
    examples=["users who never logged in", "never logged in users"],
)

REGISTRY.register(
    name="USER_FAILED_LOGIN",
    patterns=[
        r"\busers?\s+with\s+failed\s+login",
        r"\bfailed\s+login\s+(attempts?|count)\b",
        r"\bwhich\s+users?\s+have\s+failed\s+login",
    ],
    handler=_h.handle_user_failed_login,
    priority=25,
    requires_admin=True,
    description="List users with failed login attempts",
    examples=["users with failed login attempts", "show failed logins"],
)

REGISTRY.register(
    name="USER_DUPLICATE_EMAIL",
    patterns=[
        r"\bduplicate\s+email",
        r"\busers?\s+sharing\s+(an?\s+)?email",
        r"\bsame\s+email\s+address",
    ],
    handler=_h.handle_user_duplicate_email,
    priority=25,
    requires_admin=True,
    description="Find users with duplicate email addresses",
    examples=["users with duplicate emails", "check for duplicate email addresses"],
)

REGISTRY.register(
    name="USER_LEVEL_LIST",
    patterns=[
        r"\buser\s+levels?\b",
        r"\blist\s+user\s+levels?\b",
        r"\bwhat\s+levels?\s+are\s+(defined|available)\b",
    ],
    handler=_h.handle_user_level_list,
    priority=26,
    requires_admin=True,
    description="List all defined user levels (L1/L2/L3)",
    examples=["list user levels", "what user levels are defined"],
)

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTMENT (priority 30-34)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="DEPT_LIST",
    patterns=[
        r"\blist\s+(all\s+)?departments?\b",
        r"\bshow\s+(all\s+)?departments?\b",
        r"\ball\s+departments?\b",
    ],
    handler=_h.handle_dept_list,
    priority=30,
    requires_admin=True,
    description="List all departments",
    examples=["list all departments", "show departments"],
)

REGISTRY.register(
    name="DEPT_INFO",
    patterns=[
        r"\bdepartment\s+(info|details?|data)\s*(for|of|about)?\s*\w+",
        r"\binfo\s+(on|about)\s+\w+\s+department\b",
        r"\bshow\s+department\s+\w+",
    ],
    handler=_h.handle_dept_info,
    priority=31,
    requires_admin=True,
    description="Show details for a specific department",
    examples=["show Finance department info", "details for IT department"],
)

REGISTRY.register(
    name="DEPT_RETURNS",
    patterns=[
        r"\breturns?\s+(of|for|in)\s+(the\s+)?\w+\s+department\b",
        r"\breports?\s+(assigned\s+to|for)\s+\w+\s+department\b",
        r"\bdepartment\s+\w+\s+returns?\b",
    ],
    handler=_h.handle_dept_returns,
    priority=32,
    requires_admin=True,
    description="List returns assigned to a department",
    examples=["returns for Finance department", "reports assigned to IT"],
)

# ─────────────────────────────────────────────────────────────────────────────
# ROLE & PERMISSIONS (priority 35-39)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="ROLE_LIST",
    patterns=[
        r"\blist\s+(all\s+)?roles?\b",
        r"\bshow\s+(all\s+)?roles?\b",
        r"\ball\s+roles?\b",
        r"\bwhat\s+roles?\s+are\s+(defined|available|there)\b",
    ],
    handler=_h.handle_role_list,
    priority=35,
    requires_admin=True,
    description="List all roles",
    examples=["list all roles", "what roles are defined"],
)

REGISTRY.register(
    name="ROLE_PERMISSIONS",
    patterns=[
        r"\bpermissions?\s+(for|of)\s+(role\s+)?\w+",
        r"\brole\s+\w+\s+permissions?\b",
        r"\bwhat\s+can\s+(role\s+)?\w+\s+do\b",
        r"\baccess\s+rights?\s+(for|of)\s+(role\s+)?\w+",
    ],
    handler=_h.handle_role_permissions,
    priority=36,
    requires_admin=True,
    description="Show permissions for a specific role",
    examples=["permissions for Admin role", "what can Maker role do"],
)

REGISTRY.register(
    name="ROLE_USERS",
    patterns=[
        r"\busers?\s+assigned\s+to\s+role\s+\w+",
        r"\bwho\s+(has|have)\s+role\s+\w+",
        r"\bwhich\s+users?\s+have\s+the\s+\w+\s+role\b",
    ],
    handler=_h.handle_role_users,
    priority=37,
    requires_admin=True,
    description="List users assigned to a specific role",
    examples=["who has Admin role", "users assigned to Maker role"],
)

REGISTRY.register(
    name="PERMISSION_CHECK",
    patterns=[
        r"\bcan\s+role\s+\w+\s+(access|do|use|view)\b",
        r"\bdoes\s+(role\s+)?\w+\s+have\s+\w+\s+permission\b",
        r"\bcheck\s+permission\s+(for|of)\s+role\b",
    ],
    handler=_h.handle_permission_check,
    priority=38,
    requires_admin=True,
    description="Check a specific permission for a role",
    examples=["can Admin role access upload", "does Maker have generate permission"],
)

# ─────────────────────────────────────────────────────────────────────────────
# PERIODS (priority 40)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="PERIOD_LIST",
    patterns=[
        r"\blist\s+(all\s+)?periods?\b",
        r"\bshow\s+(all\s+)?periods?\b",
        r"\breporting\s+periods?\b",
        r"\bwhat\s+periods?\s+are\s+(defined|there|available)\b",
    ],
    handler=_h.handle_period_list,
    priority=40,
    description="List all reporting periods",
    examples=["list all periods", "what reporting periods are there"],
)

# ─────────────────────────────────────────────────────────────────────────────
# RETURNS / REPORTS (priority 45-49)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="NON_XBRL_LIST",
    patterns=[
        r"\bnon[\s_-]?xbrl\s+returns?\b",
        r"\bnon[\s_-]?xbrl\s+reports?\b",
        r"\blist\s+non[\s_-]?xbrl\b",
    ],
    handler=_h.handle_non_xbrl_list,
    priority=45,
    description="List all non-XBRL returns",
    examples=["list non-XBRL returns", "show non-XBRL reports"],
)

REGISTRY.register(
    name="VALIDATION_RETURNS",
    patterns=[
        r"\breturns?\s+with\s+(formula|schema|large)\s+validat\w*\b",
        r"\bvalidat\w+\s+returns?\b",
        r"\bcims[\s_-]enabled\s+returns?\b",
    ],
    handler=_h.handle_validation_returns,
    priority=46,
    description="List returns with specific validation settings",
    examples=["returns with formula validation", "CIMS-enabled returns"],
)

REGISTRY.register(
    name="RETURNS_BY_PERIOD",
    patterns=[
        r"\b(quarterly|monthly|half[\s_-]?yearly|annual|daily)\s+returns?\b",
        r"\breturns?\s+(for|by)\s+(quarter|month|period)\b",
    ],
    handler=_h.handle_returns_by_period,
    priority=47,
    description="List returns for a specific reporting period",
    examples=["quarterly returns", "monthly reports"],
)

REGISTRY.register(
    name="RETURNS_DETAILS",
    patterns=[
        r"\bdetails?\s+(of|for|about)\s+(return|report)\s+\S+",
        r"\bshow\s+(return|report)\s+\S+",
        r"\binfo\s+on\s+(return|report)\s+\S+",
    ],
    handler=_h.handle_returns_details,
    priority=48,
    description="Show details for a specific return",
    examples=["details for CIMS_LR return", "show report info"],
)

REGISTRY.register(
    name="RETURNS_LIST",
    patterns=[
        r"\blist\s+(all\s+)?returns?\b",
        r"\bshow\s+(all\s+)?returns?\b",
        r"\ball\s+(xbrl\s+)?returns?\b",
        r"\bxbrl\s+returns?\b",
    ],
    handler=_h.handle_returns_list,
    priority=49,
    description="List all XBRL returns",
    examples=["list all returns", "show XBRL returns"],
)

# ─────────────────────────────────────────────────────────────────────────────
# SUBMISSIONS / INSTANCE LOG (priority 50-54)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="SUBMISSION_PENDING",
    patterns=[
        r"\bpending\s+submissions?\b",
        r"\bsubmissions?\s+(that\s+are\s+)?pending\b",
        r"\bunsubmitted\s+reports?\b",
        r"\bopen\s+submissions?\b",
    ],
    handler=_h.handle_submission_pending,
    priority=50,
    requires_admin=True,
    description="List all pending submissions",
    examples=["show pending submissions", "unsubmitted reports"],
)

REGISTRY.register(
    name="SUBMISSION_APPROVED",
    patterns=[
        r"\bapproved\s+submissions?\b",
        r"\bsubmissions?\s+(that\s+are\s+)?approved\b",
        r"\baudited\s+submissions?\b",
    ],
    handler=_h.handle_submission_approved,
    priority=51,
    requires_admin=True,
    description="List all approved / audited submissions",
    examples=["show approved submissions", "audited filings"],
)

REGISTRY.register(
    name="SUBMISSION_STATUS",
    patterns=[
        r"\bstatus\s+(of|for)\s+(return|report)\s+\S+",
        r"\bsubmission\s+status\s+(for|of)\s+\S+",
        r"\bhow\s+many\s+submissions?\s+(for|of)\s+\S+",
    ],
    handler=_h.handle_submission_status,
    priority=52,
    requires_admin=True,
    description="Show submission status for a specific return",
    examples=["status of CIMS_LR submissions", "submission count for ROF"],
)

REGISTRY.register(
    name="SUBMISSION_LIST",
    patterns=[
        r"\ball\s+submissions?\b",
        r"\blist\s+submissions?\b",
        r"\bsubmission\s+(log|history|records?)\b",
        r"\binstance\s+log\b",
    ],
    handler=_h.handle_submission_list,
    priority=53,
    requires_admin=True,
    description="List all submission records (instance log)",
    examples=["show all submissions", "instance log"],
)

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN AUDIT / LOGS (priority 55-59)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="AUDIT_LOG",
    patterns=[
        r"\baudit\s+(log|trail|records?|history)\b",
        r"\bsystem\s+audit\b",
        r"\bwho\s+changed\b",
        r"\bchanges?\s+made\s+by\s+\S+",
    ],
    handler=_h.handle_audit_log,
    priority=55,
    requires_admin=True,
    description="Show system audit log",
    examples=["show audit log", "who made changes"],
)

REGISTRY.register(
    name="CROSS_VAL_LOG",
    patterns=[
        r"\bcross[\s_-]?validation\s+(log|errors?|results?|history)\b",
        r"\bvalidation\s+failures?\s+(log|history)\b",
    ],
    handler=_h.handle_cross_validation_log,
    priority=56,
    requires_admin=True,
    description="Show cross-validation log",
    examples=["cross validation log", "validation errors history"],
)

REGISTRY.register(
    name="UPLOAD_LOG",
    patterns=[
        r"\bupload(ed)?\s+(file\s+)?log\b",
        r"\bfile\s+upload\s+(history|records?|log)\b",
    ],
    handler=_h.handle_upload_log,
    priority=57,
    requires_admin=True,
    description="Show file upload log",
    examples=["uploaded file log", "file upload history"],
)

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM / CONFIGURATION (priority 60-69)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY.register(
    name="MENU_LIST",
    patterns=[
        r"\bsystem\s+menu\b",
        r"\blist\s+(all\s+)?modules?\b",
        r"\bshow\s+(all\s+)?modules?\b",
        r"\bwhat\s+modules?\s+are\s+(available|in\s+the\s+system)\b",
    ],
    handler=_h.handle_menu_list,
    priority=60,
    description="List all system menu options / modules",
    examples=["list all modules", "what modules are available"],
)

REGISTRY.register(
    name="NOTIFICATION_LIST",
    patterns=[
        r"\bnotification\s+(list|settings?|config\w*)\b",
        r"\bshow\s+notifications?\b",
        r"\bnotifications?\s+(for|of)\s+\S+",
    ],
    handler=_h.handle_notification_list,
    priority=61,
    description="Show notification configuration",
    examples=["show notification settings", "notifications for CIMS_LR"],
)

REGISTRY.register(
    name="BANK_INFO",
    patterns=[
        r"\bbank\s+(details?|info|name|type)\b",
        r"\bwhich\s+bank\b",
        r"\borganis?ation\s+bank\b",
    ],
    handler=_h.handle_bank_info,
    priority=62,
    description="Show bank / organisation details",
    examples=["show bank details", "which bank is configured"],
)

REGISTRY.register(
    name="SEGMENT_INFO",
    patterns=[
        r"\bsegment\s+(types?|list|info|details?)\b",
        r"\blist\s+segments?\b",
        r"\bwhat\s+segments?\s+are\s+(defined|there)\b",
    ],
    handler=_h.handle_segment_info,
    priority=63,
    description="Show configured segment types",
    examples=["list segments", "what segment types are defined"],
)

# ─────────────────────────────────────────────────────────────────────────────
# HELP — lowest priority so it doesn't shadow any real intent
# ─────────────────────────────────────────────────────────────────────────────

def _help_handler(store, params, user_id, is_admin):  # type: ignore[override]
    """Inline handler for /help — returns the generated help text."""
    return {
        "intent": "HELP",
        "label": "Available Commands",
        "found": True,
        "records": [],
        "summary": REGISTRY.generate_help(),
        "meta": {},
    }


REGISTRY.register(
    name="HELP",
    patterns=[
        r"\bhelp\b",
        r"\bwhat\s+can\s+(you|i)\s+(do|ask|query)\b",
        r"\bshow\s+(me\s+)?(commands?|queries|examples?)\b",
    ],
    handler=_help_handler,
    priority=99,
    description="Show this help message",
    examples=["help", "what can I ask"],
)
