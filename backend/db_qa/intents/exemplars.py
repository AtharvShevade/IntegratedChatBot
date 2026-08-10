"""Curated example phrasings per Intent, for embedding-based semantic
intent matching.

Source: remapped from backend/db_qa/app_db_questions.json (the original
access-tiered question catalog, organized by category + admin/self tier,
not by Intent). Each raw question was manually assigned to the Intent it
actually asks for; bracketed placeholders (e.g. "[other username]",
"[return name]") were rewritten into natural concrete-ish phrasing so
exemplars read like real user messages rather than templates. Two blank/
placeholder entries in the source JSON ("" ?"", "" "") were dropped as
data-entry artifacts, not real questions.

This is intentionally NOT exhaustive per intent — a handful of strong,
distinct phrasings beats a large but repetitive list for nearest-neighbor
embedding matching. Intents with thin coverage below are flagged in
THIN_COVERAGE_INTENTS so the embedding-tier build can treat them as
higher-risk for false negatives until more real usage data (see
backend/utils/intent_log.py) suggests better/more phrasings to add.
"""
from __future__ import annotations

from backend.db_qa.intents.taxonomy import Intent

EXEMPLARS: dict[Intent, list[str]] = {

    # ── USER ─────────────────────────────────────────────────────────────
    Intent.USER_PROFILE: [
        "What are the details of user with ID 4821?",
        "Give me the full profile for user jsmith",
        "Show me everything about user rpatel",
        "Tell me about myself",
        "Who am I in the system?",
    ],
    Intent.USER_FIELD: [
        "What is my email address?",
        "Can you tell me the mobile number of user rpatel?",
        "What is the email address of user jsmith?",
        "What is my mobile number on record?",
        "What is the mobile number of user rpatel?",
        "When did I last log in?",
        "When did user jsmith last log in?",
        "When was my account created?",
        "When was user rpatel created?",
        "Who created my account?",
        "Who created user jsmith?",
        "When did I last update my password?",
        "When did user jsmith last update their password?",
        "What is my login ID?",
        "What is the login ID of user rpatel?",
        "What is my user code?",
        "What is the user code for jsmith?",
        "Is my account currently active?",
        "How many failed login attempts does my account have?",
        "How many failed login attempts does user jsmith have?",
    ],
    Intent.USER_LIST: [
        "How many users are there in total?",
        "How many active users are there?",
        "Who are all the inactive users?",
        "Which users have never logged in?",
        "Which users have failed login attempts?",
        "Which users have not updated their password recently?",
        "Are there any duplicate email addresses across users?",
    ],
    Intent.USERS_BY_DEPARTMENT: [
        "Which users belong to the Finance department?",
        "Which users are associated with department ID 12?",
        "Who works in the Compliance department?",
        # From app_db_questions_augmented.json — casual/polite phrasing
        # templates the regex classifier doesn't tolerate but the embedding
        # tier should (see doc/INTENT_GAP_ANALYSIS.md).
        "Can you show me which users belong to the Treasury department?",
        "I need to know which users belong to the Finance department.",
    ],
    Intent.USERS_BY_ROLE: [
        "Which users are assigned the Admin User role?",
        "Which users have the Tester role?",
        "How many users have the Admin User role?",
        "Can you show me which users are assigned the Auditor role?",
        "I need to know which users are assigned the Tester role.",
    ],
    Intent.USERS_WITH_ROLES_AND_DEPARTMENTS: [
        "List all users along with their roles and departments.",
        "Show me every user with their role and department.",
        "Can you list all users along with their roles and departments?",
        "Give me a list of all users along with their roles and departments.",
    ],

    # ── DEPARTMENT ───────────────────────────────────────────────────────
    Intent.DEPARTMENT_LIST: [
        "What are all the departments in the system?",
        "Which departments are currently active?",
        "Which departments are inactive?",
        "How many departments are there in total?",
        "Which department has the most returns assigned?",
        "Which department has the fewest returns assigned?",
        "Which departments have no returns assigned?",
        "Which departments have zero returns assigned?",
        "Which departments don't have any returns?",
        "Which departments have no assigned returns?",
        "List all departments along with their assigned return counts.",
    ],
    Intent.DEPARTMENT_PROFILE: [
        "What department am I in?",
        "What is the email address of the Finance department?",
        "What is the department ID of Compliance?",
        "What is the Department ID of my department?",
        # Real-world paraphrases: different vocabulary ("team", "assigned",
        # "belong"), not just reworded synonyms of the same words — the
        # embedding tier needs these words actually present in an exemplar to
        # rank the right intent highly; before adding these, "Which team am I
        # assigned to?" scored 0.831 (ambiguous) and "Where am I assigned?"
        # 0.811, both against "What department am I in?" as nearest neighbour.
        "What department do I belong to?",
        "Which team am I assigned to?",
        "Can you tell me my department?",
        "Show my department.",
        "Where am I assigned?",
        "Which department do I work in?",
        "Tell me which department I'm part of.",
        "What is the email address of my department?",
    ],
    Intent.DEPARTMENT_RETURNS: [
        "Which XBRL returns does my department have access to?",
        "Which Non-XBRL returns does my department have access to?",
        "How many returns does my department have access to?",
        "Which XBRL returns are assigned to the Treasury department?",
        "How many XBRL returns does the Compliance department have access to?",
        "Which Non-XBRL returns are assigned to the Treasury department?",
        "How many Non-XBRL returns does the Compliance department have access to?",
        "Which returns can my department access?",
        "Show all returns assigned to my department.",
        "What returns are available for my department?",
        "List my department's assigned returns.",
        "Which reports can my department file?",
        "Which returns can the Treasury department access?",
        "What returns are assigned to the Compliance department?",
        "Which returns are available for the Treasury department?",
        "Which returns are accessible by my department?",
        "Which returns are mapped to the Compliance department?",
        "Which returns are linked to my department?",
        "Which returns are configured for the Treasury department?",
    ],
    Intent.DEPARTMENTS_WITH_RETURN_ACCESS: [
        "Which departments have access to return CIMS_ROR?",
        "How many departments have access to return DPSS09?",
        "Can you show me which departments have access to return DPSS09?",
        "I need to know which departments have access to return CIMS_RAQ.",
        "Which departments have missed the submission deadline for return CIMS_ROR?",
        "Which departments failed to submit return DPSS09 on time?",
        # Type-level form (no single return named) — same intent, answered
        # via xbrl_type rather than target_return.
        "Which departments can access Non-XBRL returns?",
        "Which departments have access to XBRL returns?",
        "Which departments are assigned Non-XBRL returns?",
    ],
    Intent.DEPARTMENT_HAS_RETURN: [
        "Does my department have access to return CIMS_RAQ?",
        "Does the Treasury department have access to DBR01?",
        "Can you confirm does my department have access to return CIMS_ROR?",
        "Am I allowed to submit return DPSS09 through my department?",
    ],

    # ── ROLE ─────────────────────────────────────────────────────────────
    Intent.ROLE_LIST: [
        "What are all the roles defined in the system?",
        "Which roles are currently active?",
        "Which roles are inactive or disabled?",
        "How many roles are there in total?",
        "Which role has the most users?",
        "Which role has the least users?",
        "Which role is used by the fewest users?",
        "List all roles along with the number of users in each.",
        "Is there a role called Auditor in the system?",
        "What roles do we have?",
        "What roles are present in the system?",
        "I need the role list.",
        "Can you tell me all the roles?",
    ],
    Intent.ROLE_PROFILE: [
        "What is my role?",
        "What is the name of my role?",
        "What is my role ID?",
        "Is my role currently active?",
        "What is the role ID for Admin User?",
        "What is the name of role ID 101?",
        "Which role do I belong to?",
        "Tell me about the Tester role.",
    ],
    Intent.ROLE_USERS: [
        "Which users are assigned the Tester role?",
        "Who has the Admin User role?",
        "Can you show me which users are assigned the Auditor role?",
        "I need to know which users are assigned the Checker role.",
        "Show users assigned to the Maker role.",
        "Who belongs to the Tester role?",
        "How many users belong to the Tester role?",
        "Count users in the Admin role.",
    ],
    Intent.ROLE_PEER_COUNT: [
        "How many other users share the same role as me?",
        "How many people have my same role?",
        "What is the total number of other users who share the same role as me?",
        "Give me the count of other users who share the same role as me.",
    ],

    # ── ROLE_ACCESS ──────────────────────────────────────────────────────
    Intent.PERMISSION_PROFILE: [
        "What permissions do I have in the system?",
        "What permissions does the Tester role have?",
        "What modules am I allowed to access?",
        "List all modules accessible to the Admin User role.",
        "What do I NOT have access to in this application?",
        "What does the Tester role NOT have access to?",
    ],
    Intent.PERMISSION_CHECK: [
        "Do I have permission to approve submissions?",
        "Can I create new users?",
        "Can role Admin User create new users?",
        "Can I edit department settings?",
        "Can I approve submissions?",
        "Can I view the audit log?",
        "Can role Tester view the audit log?",
        "Can I run cross-validation?",
        "Can I generate SDMX?",
        "Can I upload Non-XBRL files?",
        "Can I create XBRL instances?",
        "Can I access the Balance Sheet module?",
        "Can I disable the maker-checker workflow?",
        "Can I access data preparation?",
        "Can the QA Analyst role run cross-validation?",
        "Do I have approval rights for any module?",
        "Am I allowed to edit return configurations?",
        "Can I view the SDMX log?",
        "Can I add or edit providers?",
    ],
    Intent.ROLES_WITH_PERMISSION: [
        "Which roles have full access to the Balance Sheet module?",
        "Which roles can approve data preparation?",
        "Which roles can create XBRL instances?",
        "Which roles have view-only access to returns?",
        "Which roles have no edit or create permissions at all?",
        "Which roles have approval rights for the audit log?",
        "Which roles can upload Non-XBRL files?",
        "Which roles have access to the NXQueryBuilder?",
        "Which roles can generate SDMX?",
    ],
    Intent.ROLE_MODULE_ACCESS: [
        "Does role Tester have access to the SDMX generation module?",
        "Does role Auditor have access to cross-validation?",
        "Which modules does the Admin User role have full control over?",
        "Can the Tester role edit any module?",
        "What actions can role Tester perform on the notification module?",
        "Can role Auditor disable the maker-checker workflow?",
        "What actions can I perform on the notification module?",
        # "What access does the checker role have" was found failing across
        # every round of self-test in doc/INTENT_GAP_ANALYSIS.md — no
        # exemplar or regex rule covered this exact "what access does ROLE
        # have" shape (distinct from PERMISSION_PROFILE's "what permissions
        # does ROLE have", which a real user treats as the same question but
        # the two phrasings weren't linked).
        "What access does the Checker role have?",
        "What access does the Maker role have?",
        "What can the Checker role do in this application?",
    ],
    Intent.ROLE_PERMISSION_DIFF: [
        "What is the difference in permissions between Admin User and Tester?",
        "How do the permissions of Auditor and Tester differ?",
        "Can you tell me the difference in permissions between Maker and Checker?",
        "Please provide the difference in permissions between Admin User and Auditor.",
    ],

    # ── USER_LEVEL ───────────────────────────────────────────────────────
    Intent.USER_LEVEL_LIST: [
        "What user levels are defined in the system?",
        "How many user levels exist?",
        "Are all user levels currently active?",
        "Which users are at level L1?",
        "Which users are at level L2?",
        "Which users are at level L3?",
    ],
    Intent.USER_LEVEL_SELF: [
        "What is my user level?",
        "What is the meaning of my user level?",
        "What is the level ID assigned to me?",
        "Can you tell me the meaning of my user level (L1 / L2 / L3)?",
    ],

    # ── PERIOD ───────────────────────────────────────────────────────────
    Intent.PERIOD_LIST: [
        "What are all the reporting periods and frequencies defined in the system?",
        "List all reporting frequencies with their EBR codes.",
        "How many reporting frequencies are defined?",
        "Give me the full list of reporting frequencies we have configured.",
        "Which returns share the same reporting schedule or frequency?",
        "Do any returns have an identical reporting frequency?",
        "What is the full annual reporting calendar across all frequencies?",
        "Show me the annual calendar covering every reporting frequency.",
        "Which frequency has the most returns scheduled under it?",
        "Which reporting frequency is used by the largest number of returns?",
        "Which period has the most returns assigned?",
        "Which reporting period has the highest number of returns?",
    ],
    Intent.PERIOD_LOOKUP: [
        "What is the period name for period ID 107?",
        "What is the EBR frequency code for Quarterly?",
        "What is the period ID for the Half Yearly frequency?",
        "Which period ID represents fortnightly reporting?",
        "How many advance notification days are given for Quarterly returns?",
        "What is the advance notification days for daily returns?",
        "Which periods have an advance notification period greater than 10 days?",
        "Are there any returns with no advance notification days configured?",
        "Is there any return that has no advance notification configured at all?",
        "What is my personal reporting calendar for this year?",
        "Can you show me a calendar view of all my report due dates?",
        "Show me all my upcoming report due dates for the year.",
        # Comparison framing — moved here from PERIOD_LIST so this
        # intent's exemplar space matches its own regex/handler
        # (query_type="compare"), not the plain full-listing intent.
        "What is the difference between QF and QAD frequencies?",
        "Can you compare the Quarterly and Half Yearly frequencies for me?",
        "How does the Fortnightly frequency differ from the Monthly one?",
    ],
    # RETURNS_BY_FREQUENCY gets deliberately dense coverage below (well
    # past this file's usual "handful of strong phrasings" convention —
    # see the module docstring) because every frequency word has several
    # real user synonyms (Monthly/Month, Quarterly/Quarter, Half Yearly/
    # Semi Annual, Yearly/Annual/Annually/Year, Fortnightly/Biweekly,
    # Weekly/Week, Daily/Day) that regex already resolves deterministically
    # via PERIOD_ALIASES, but which still need embedding-tier exemplars so
    # a phrasing regex doesn't anticipate can still land here via semantic
    # similarity rather than falling through to LLM disambiguation or
    # nothing at all.
    Intent.RETURNS_BY_FREQUENCY: [
        # Monthly / Month
        "Which returns are filed on a monthly basis?",
        "Which returns are filed monthly?",
        "Show me all the monthly returns.",
        "List the returns filed every month.",
        "Which of my returns are filed monthly?",
        "Give me the month returns.",
        "What returns get filed every month?",
        # Quarterly / Quarter
        "Which returns are filed quarterly?",
        "Show quarterly returns.",
        "List the quarter returns.",
        "Which of my returns are filed quarterly?",
        "Which of my returns follow a quarterly reporting schedule?",
        "Give me the returns filed every quarter.",
        "What returns are submitted on a quarterly basis?",
        # Half Yearly / Semi Annual
        "Show me all the half yearly returns.",
        "List the semi annual returns.",
        "Which returns are filed half-yearly?",
        "What returns get filed every half year?",
        "Give me the returns that are semi-annual.",
        # Yearly / Annual / Annually / Year
        "Which returns are filed annually?",
        "Which returns are annual?",
        "Show annual returns.",
        "List yearly returns.",
        "Returns filed every year.",
        "Give me annual reporting returns.",
        "Which of my returns are filed yearly?",
        "What returns are due once a year?",
        # Fortnightly / Biweekly
        "Show me all the fortnightly returns.",
        "List biweekly returns.",
        "Which returns are filed every fortnight?",
        "Give me the returns filed once every two weeks.",
        # Weekly / Week
        "Give me the returns that are filed weekly.",
        "Show weekly returns.",
        "List the week returns.",
        "Which returns are filed every week?",
        # Daily / Day
        "Which returns are filed daily?",
        "Show me the day returns.",
        "List all daily returns.",
        "What returns are due every day?",
    ],

    # ── XBRL_RETURNS ─────────────────────────────────────────────────────
    Intent.RETURN_LIST: [
        "What are all the XBRL returns available in the system?",
        "Which XBRL returns are currently active?",
        "Which XBRL returns are inactive?",
        "How many XBRL returns are there in total?",
        "Which returns have both formula validation and schema-calculation validation enabled?",
        "Which returns use the large validator?",
        "List all returns along with their due days and frequency.",
        "Which returns are CIMS-enabled?",
        "Which returns use the table linkbase?",
        "Which returns belong to the DPSS category?",
        "Which returns belong to the DBS category?",
        "Which returns belong to the DBR category?",
        "Which returns have a due period of more than 21 days?",
        "Which XBRL returns can I submit?",
        "List all returns and their next three upcoming due dates.",
        "Show me the next three due dates for every return.",
    ],
    Intent.RETURN_PROFILE: [
        "What version of the taxonomy does return CIMS_ROR use?",
        "What is the XSD path for return CIMS_RAQ?",
        "What is the base Excel file for return CIMS_ROR?",
        "What is the table linkbase path for return DPSS09?",
        "What is the alternate name for return CIMS_ROR?",
        "What are the namespace details for return CIMS_RAQ?",
        "Give me the full details of return CIMS_ROR.",
        # "whats dpss 09 about" failed across Rounds 2-3 of self-test
        # (doc/INTENT_GAP_ANALYSIS.md) — no exemplar covered this generic
        # "what is/about a named return" shape at all.
        "What is DPSS09 about?",
        "What is the DBR01 return?",
        "Tell me about return CIMS_ROR.",
    ],
    Intent.RETURN_FIELD: [
        "Please provide the return ID for CIMS_ROR.",
        "What is the return ID for CIMS_ROR?",
        "What is the internal form ID for return CIMS_RAQ?",
        "How many days are due for submission of return CIMS_ROR?",
        "Does return CIMS_RAQ require encryption?",
        "What is the reporting frequency of return CIMS_ROR?",
        "What report formats are available for return CIMS_ROR?",
        "What formats does return CIMS_RAQ support — PDF, Excel, or HTML?",
    ],
    Intent.RETURN_VALIDATION_CONFIG: [
        "Does return CIMS_RAQ require formula validation?",
        "Does return CIMS_ROR use schema-calculation validation?",
        "Which returns have RBI validation enabled?",
        "Can you show me which returns have RBI validation enabled?",
    ],
    Intent.RETURNS_SUBMITTABLE_BY_DEPT: [
        "Which departments can submit the DPSS09 return?",
        "Which departments can submit the DBR01 return?",
        "Can you show me which departments can submit the DPSS09 return?",
        "I need to know which departments can submit the DBR01 return.",
    ],
    Intent.NEXT_REPORTING_DATE: [
        "What is the next reporting date for return CIMS_ROR?",
        "When is return CIMS_RAQ due?",
        "When should I submit return CIMS_ROR next?",
        "Can you tell me when is return DPSS09 due?",
        "What is the reporting calendar for return CIMS_ROR for the current year?",
        "Can I see the full reporting calendar for return CIMS_ROR?",
    ],
    Intent.REPORTS_FILED_IN_RANGE: [
        "Show me all XBRL reports filed between 1-Jan-2026 and 31-Mar-2026",
        "Which returns were filed between January and March?",
        "Show all reports submitted between last month and today.",
        "Display all submissions between 1-Jan-2026 and 31-Mar-2026.",
    ],
    Intent.REPORTS_UPCOMING_IN_RANGE: [
        "What XBRL reports are coming up between 1-Jan-2026 and 31-Mar-2026",
        "What non-XBRL returns are due between two dates?",
        "What returns are upcoming next month?",
        "Can you show me which returns have upcoming due dates in the next 30 days?",
        "Which returns have upcoming due dates in the next 10 days?",
        "How many returns are due this month across the organization?",
        "Are any of my returns overdue?",
        "Which returns are overdue for submission across all departments?",
        "What is my next Non-XBRL return due?",
        "Which return is due next for me?",
        "What is my next XBRL return due?",
        "When is my next return due?",
    ],
    Intent.MONTHLY_FILING_STATUS: [
        "What's my XBRL filing status for June 2025?",
        "What's my non-XBRL filing status for June 2025?",
        "What's the non-XBRL status for this month?",
        "What's my filing status for last month?",
        "What dates are non-XBRL reports expected in June 2025?",
        "Which XBRL returns have I filed this month, and which are still pending?",
        "Give me my department's non-XBRL status for next month.",
    ],

    # ── NON_XBRL_RETURNS ─────────────────────────────────────────────────
    Intent.NONXBRL_RETURN_LIST: [
        "How many Non-XBRL returns are there in total?",
        "Which Non-XBRL returns have no due days configured?",
        "List all Non-XBRL returns with their return IDs and frequencies.",
        "Which Non-XBRL returns have a folder structure?",
        "Which Non-XBRL returns can I submit?",
        "How many Non-XBRL returns do I have access to?",
        "What are the Non-XBRL returns I have access to?",
        "Give me the list of Non-XBRL returns I can access.",
        "Show me the Non-XBRL returns available to me.",
    ],
    Intent.NONXBRL_RETURN_PROFILE: [
        "Please provide the base file template for Non-XBRL return BSR1.",
        "What is the base file template for Non-XBRL return BSR1?",
        "What is the period or frequency of Non-XBRL return BSR1?",
        "How many due days does Non-XBRL return BSR1 have?",
        "Is Non-XBRL return BSR1 CIMS-enabled?",
        "What is the job processing ID for Non-XBRL return BSR1?",
        "What is the report generation status for Non-XBRL return BSR1?",
        "What is the reporting schedule for Non-XBRL return BSR1?",
        "Can I see the reporting schedule for Non-XBRL return BSR1?",
        "What report formats are supported for Non-XBRL return BSR1?",
        "What report format does Non-XBRL return BSR1 use?",
        "Tell me about the Non-XBRL return BSR1.",
        "Show me the Non-XBRL return Collateral Loan.",
        "Give me the details of Non-XBRL return Credit to Women.",
    ],

    # ── DEPT_RETURN_MAPPING ──────────────────────────────────────────────
    Intent.DEPT_RETURN_ACCESS_MATRIX: [
        "Which return is accessible by the maximum number of departments?",
        "Which returns are accessible by all departments?",
        "Which department has access to the most returns?",
        # "which department has the most returns" was found misrouted to
        # DEPARTMENT_PROFILE in Round 1-2 self-test (it tried to resolve
        # "has the most returns" as a literal department name) — this
        # exemplar set already covers the phrasing; the embedding tier
        # being inactive until now is why it didn't help in practice.
        "Which department has the most returns assigned?",
        "Can you show me which department has access to the most returns?",
    ],
    # Deliberately kept narrow to a personal ACCESS-SUMMARY/TOTAL framing —
    # distinct from DEPARTMENT_RETURNS' department-scoped LISTING framing
    # (self or a named department, XBRL/Non-XBRL filterable). The two used to
    # share a near-duplicate exemplar ("Which returns does my department have
    # access to?", removed from here), which meant they were actively
    # competing for the same phrasing space — both intents appeared in each
    # other's top-3 candidates for the same test queries. Narrowing this list
    # to the "summary/total" framing its other two exemplars already
    # established (rather than differentiating DEPARTMENT_RETURNS instead)
    # keeps the department-scoped listing intent as the one place that owns
    # "returns my department can access/file/is assigned" — matching how the
    # brief itself treats every such paraphrase as one intent.
    Intent.MY_RETURN_ACCESS: [
        "What is the complete list of returns I can work with?",
        "How many returns can I access in total?",
        "What returns am I entitled to access?",
        "Give me a full count of the returns I'm allowed to use.",
    ],
    Intent.DEPT_FULL_RETURN_LIST: [
        "What is the complete list of returns for the Treasury department?",
        "Which Non-XBRL returns can the Compliance department access?",
        "Can you tell me the complete list of returns for the Finance department?",
        "Please provide the complete list of returns for department Compliance.",
    ],

    # ── INSTANCE_LOG ─────────────────────────────────────────────────────
    Intent.SUBMISSION_STATUS: [
        "What is the status of my submission ID 4021?",
        "What is the status of submission 4021 made by jsmith?",
        "Can you tell me the status of my submission ID 4021?",
        "Did my last submission go through?",
    ],
    Intent.SUBMISSION_LIST: [
        "Which returns have reports pending generation across all users?",
        "Which of my submissions are pending approval?",
        "Which submissions are pending approval across all users?",
        "Which of my submissions have been approved?",
        "Which of my submissions have been audited?",
        "Which submissions have been uploaded to CIMS successfully?",
        "Which submissions failed CIMS upload?",
        "How many submissions have the status Audited system-wide?",
        "What is the total number of submissions in the system?",
        "Which submissions are rejected and what is the rejection reason?",
        "Which submissions have an error document generated?",
        "Which submissions have Un-Audited status?",
        "Show all my submissions between 1-Jan-2026 and 31-Mar-2026.",
        "Show all submissions between two dates across all users.",
    ],
    Intent.SUBMISSION_DETAIL: [
        "Was my submission 4021 rejected? What is the rejection reason?",
        "Does my submission 4021 have an error document?",
        "What is the instance document path for my submission 4021?",
        "What is the CIMS upload status for my submission 4021?",
        "Did my CIMS upload for submission 4021 succeed?",
        "When was my submission 4021 approved?",
        "Who approved submission 4021?",
        "What is the rendered Excel or HTML report path for my submission 4021?",
        "Does my submission 4021 have any comments or remarks?",
        "Has my submission 4021 been uploaded to CIMS?",
        "Can I re-download the report for my submission 4021?",
        "What is the report generation date for my submission 4021?",
    ],
    Intent.SUBMISSIONS_FOR_RETURN: [
        "Which users have submitted return CIMS_ROR?",
        "What are all recent submissions made for return CIMS_ROR across all users?",
        "How many submissions are there for return CIMS_ROR this quarter across all users?",
        "Show submissions made by all users for return CIMS_ROR this period.",
        "Which submissions made by user jsmith are still pending?",
        # New computed metric from the updated catalog — no existing field
        # for this exists yet in the InstanceLog handler; flagged in the
        # Phase 1 report as needing a handler decision before this phrasing
        # can return a real answer rather than falling through unanswered.
        "What is the average time between report generation and submission for return CIMS_ROR?",
        "What is the historical on-time submission rate for return CIMS_ROR?",
        "What is the report generation status for return CIMS_ROR this period?",
    ],
    Intent.MY_SUBMISSION_HISTORY: [
        "Which returns have I submitted so far?",
        "Which submissions have I made for return CIMS_ROR?",
        "Have I ever submitted return CIMS_ROR before?",
        "How many submissions have I made for return CIMS_ROR this quarter?",
        "Which of my submissions were made for reporting date 31-Mar-2026?",
        "What is my on-time submission rate for return CIMS_ROR?",
        "Is the report ready for my submission of return CIMS_ROR?",
        "Can I download the report for my last submission of return CIMS_ROR?",
    ],

    # ── MENU_OPTIONS ─────────────────────────────────────────────────────
    Intent.MENU_LIST: [
        "How many top-level menu items are there?",
        "What modules are available in the entire application?",
        "Which modules open in a new tab?",
        "What modules am I able to see in the menu?",
        "What modules are under the ETL/Workflow section?",
        "What modules fall under the Data Management section?",
    ],
    Intent.MODULE_DETAIL: [
        "Can you tell me the parent module of NXQueryBuilder?",
        "What is the menu rank or order of the Balance Sheet module?",
        "What is the resource label for module option 205?",
        "What is the icon for the Balance Sheet module?",
        "What is the parent module of NXQueryBuilder?",
        "Is the Business Analytics module available to me?",
    ],
    Intent.MODULE_CHILDREN: [
        "What are the child modules under Data Management?",
        "What are the child modules under ETL/Workflow?",
        "Can you tell me the child modules under the Business Analytics section?",
        "Please provide the child modules under the Reports section.",
    ],

    # ── AUDIT_SECURITY ───────────────────────────────────────────────────
    Intent.AUDIT_HISTORY: [
        "Can you show me all changes made to user jsmith's profile?",
        "What changes were made by user jsmith in the last 30 days?",
        "What changes have I made in the system in the last 7 days?",
        "Show my activity history in the application.",
        "Show all changes made to user jsmith's profile.",
    ],
    Intent.AUDIT_ENTITY_TRAIL: [
        "Show the audit trail for the Treasury department.",
        "Show the audit trail for return CIMS_ROR.",
        "Who last modified the configuration for the notification module?",
        "Who last approved a submission for return CIMS_ROR?",
        "What actions were taken on submission 4021 by any user?",
    ],
    Intent.SECURITY_EVENTS: [
        "Which users have had their passwords reset?",
        "Are there any pending password reset requests?",
        "Which users have exceeded the maximum failed login attempts?",
        "Which users have been deactivated and when?",
        "Has my password ever been reset?",
        "Do I have a pending password reset request?",
        "Has my account been locked due to failed logins?",
    ],
    Intent.LOG_QUERY: [
        "Which file uploads failed in the last 7 days across all users?",
        "Have any of my file uploads failed recently?",
        "Show all SDMX generation logs for return CIMS_ROR.",
        "Are there any cross-validation errors logged for return CIMS_ROR?",
        "What errors were recorded for submission 4021 of another user?",
        "What errors were recorded for my submission 4021?",
    ],

    # ── CROSS_ENTITY ─────────────────────────────────────────────────────
    Intent.USER_ACCESS_SUMMARY: [
        "Give a full profile summary of user jsmith including role, department, and accessible returns.",
        "Give me a full summary of my access — role, department, and returns.",
        "What is my full permission profile in this application?",
        "What can user jsmith do in the system?",
        "What can I do in the system based on my role?",
    ],
    Intent.CROSS_ENTITY_QUERY: [
        "Which users have access to return CIMS_ROR via their department?",
        "Can user jsmith approve submissions?",
        "Can user jsmith create new users?",
        "Who in the Treasury department can approve submissions?",
        "Which users have both Admin role and belong to the Treasury department?",
        "Which users with the Tester role have access to return CIMS_ROR?",
        "Which department and role combination has the broadest system access?",
        "Who has approval rights for the audit log across all departments?",
        "Which active users have not logged in for more than 60 days?",
        "Who submitted return CIMS_ROR most recently and what was the outcome?",
        "Which users can generate SDMX for return CIMS_ROR?",
        "List all users who have both data preparation and approval rights.",
        "What returns can I submit based on my department?",
        "Which of my assigned returns are due this month?",
        "Which of my returns require formula validation?",
        "Can I run cross-validation for return CIMS_ROR?",
        "What is the status of my most recent submission?",
        "Which of my submissions are still awaiting CIMS upload?",
        "Which returns assigned to my department have I not yet submitted this period?",
    ],

    # ── Reference data ───────────────────────────────────────────────────
    Intent.BANK_INFO: [
        "What is the bank name configured in the system?",
        "What is the bank code?",
        "What type of bank is this?",
        "What is the CRR/IFSC code of the bank?",
    ],
    Intent.SEGMENT_INFO: [
        "What segment types are defined in the system?",
        "What is the difference between Segment and Scenario dimension types?",
        "How many segment types are configured?",
        "What is the Segment_Id for the Scenario dimension?",
    ],
    Intent.NOTIFICATION_QUERY: [
        "What notifications are configured in the system?",
        "Which returns have notifications enabled?",
        "What is the email format for notification type reminder?",
        "What is the SMS format for notification type reminder?",
        "Which users are configured to receive notifications for return CIMS_ROR?",
        "Which of my returns have notifications enabled?",
        "How many days before the due date will I be notified for return CIMS_ROR?",
        "Will I receive an SMS reminder for return CIMS_ROR?",
        "Am I configured to receive notifications for return CIMS_ROR?",
        "Which returns have their report generation scheduled but not yet run?",
        # "Failed scheduled jobs" is a new log sub-type from the updated
        # catalog, not currently one of LOG_QUERY's optional log_type values
        # — flagged in the Phase 1 report; mapped here for now since it's
        # phrased as a notification/scheduling question, not an error log one.
        "Are there any failed scheduled report-generation jobs in the last 7 days?",
        "When is my next reminder scheduled for return CIMS_ROR?",
        "Can I see the schedule of reminders for all my returns?",
    ],
}


# Intents with fewer than 4 exemplars — the source catalog had thin or no
# coverage for these, so embedding-similarity matches against them are
# higher-risk for false negatives until real usage data (see
# backend/utils/intent_log.py's JSONL output) surfaces better phrasings.
THIN_COVERAGE_INTENTS: list[Intent] = [
    intent for intent, exemplars in EXEMPLARS.items() if len(exemplars) < 4
]


# Sanity: every Intent has at least one exemplar, and every exemplar list
# key is a real Intent (guards against typos in this file).
assert set(Intent) == set(EXEMPLARS.keys()), (
    "Intent enum and EXEMPLARS must define exactly the same members — "
    f"missing: {set(Intent) - set(EXEMPLARS.keys())}, "
    f"extra: {set(EXEMPLARS.keys()) - set(Intent)}"
)
