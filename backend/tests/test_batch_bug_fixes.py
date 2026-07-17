"""Regression tests for 5 real bugs surfaced by manual testing, all fixed
in one pass:

1. SUBMISSION_LIST never actually filtered by status ("pending approval",
   "approved", "audited", "rejected", CIMS upload success/failure, has an
   error doc) — the "status" entity was never extracted anywhere, so
   entities.get("status") was always empty and the handler's own
   filtering logic (_STATUS_GROUPS) never ran. Every status-filtered
   question silently returned every submission instead.

2. Submission-derived tables (SUBMISSION_LIST, MY_SUBMISSION_HISTORY, ...)
   showed a duplicate "Status" column — one from the raw InstanceLog
   status CODE (0-11), one from the human-readable StatusLabel. The raw
   code was ALSO run through the User/Department Active/Inactive boolean
   formatter (meant for a totally different kind of Status field),
   showing "Inactive" for nearly every row regardless of actual status.

3. _extract_after_kw's captured-name character class didn't include
   parentheses, so any return name containing one (e.g.
   "CIMS_RAQ(Annually)", common in this dataset) caused the WHOLE
   extraction to fail, not just truncate at the paren — e.g. "Have I
   ever submitted return CIMS_RAQ(Annually)?" silently fell through to
   "no target_return specified" and returned the caller's ENTIRE
   submission history instead of a specific, correct answer.

4. MENU_LIST's "top-level menu items" question counted every IsMenu=true
   option regardless of whether it had a parent (ParentOptionId) —
   conflating child items with true top-level ones, so "how many
   top-level menu items" over-counted (31 instead of the actual 7).

5. Audit-log-derived records (AUDIT_HISTORY) have AuditDateTime,
   AuditType, and Remark fields that weren't in the display layer's
   column allowlist (_PRIORITY_COLS) — since only UserName matched, the
   whole table collapsed to one repeated "User" column with none of the
   actual "what changed and when" information.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.intent_classifier import _extract_after_kw
from backend.db_qa.intents.taxonomy import Intent

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")


# ── Bug 1: SUBMISSION_LIST status extraction ────────────────────────────────

class TestSubmissionListStatusExtraction:
    @pytest.mark.parametrize("q,expected_status", [
        ("Which of my submissions are pending approval?", "pending"),
        ("Which of my submissions are pending?", "pending"),
        ("Which of my submissions have been approved?", "approved"),
        ("Which of my submissions have been audited?", "audited"),
        ("Which submissions are rejected across the system?", "rejected"),
        ("Which submissions have been uploaded to CIMS successfully?", "cims_ok"),
        ("Which submissions failed CIMS upload?", "cims_failed"),
    ])
    def test_status_extracted(self, q, expected_status):
        intent, params, target_type = classify_new(q)
        assert intent == Intent.SUBMISSION_LIST, f"{q!r} -> {intent}"
        assert params.get("status") == expected_status, f"{q!r} -> status={params.get('status')!r}"

    def test_pending_not_confused_with_approved(self):
        # "pending approval" contains the substring "approv" — must still
        # resolve to "pending", not "approved".
        intent, params, target_type = classify_new("Which of my submissions are pending approval?")
        assert params.get("status") == "pending"


@_need_5_5
class TestSubmissionListStatusFiltering:
    def test_pending_filter_actually_reduces_results(self):
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control
        from backend.db_qa.query_handlers.submission_handlers import handle_submission_list

        store = XMLStore(str(PATH_5_5))
        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.SUBMISSION_LIST.value, {"target_type": "self"},
        )
        all_result = handle_submission_list(scope, {}, store)
        pending_result = handle_submission_list(scope, {"status": "pending"}, store)

        assert pending_result["meta"]["count"] < all_result["meta"]["count"]
        pending_codes = {"0", "1", "2"}
        for rec in pending_result["records"]:
            assert rec["Status"] in pending_codes


# ── Bug 2: duplicate Status column ──────────────────────────────────────────

@_need_5_5
class TestNoDuplicateStatusColumn:
    def test_status_dropped_when_status_label_present(self):
        from backend.agent.db_qa_router import _build_db_qa_data
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control
        from backend.db_qa.query_handlers.submission_handlers import handle_submission_list

        store = XMLStore(str(PATH_5_5))
        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.SUBMISSION_LIST.value, {"target_type": "self"},
        )
        result = handle_submission_list(scope, {}, store)
        assert result["found"], "expected submissions present for iris810"

        data = _build_db_qa_data(result, intent="submission_list")
        assert "Status" not in data["cols"], f"raw Status column leaked into: {data['cols']}"
        assert "StatusLabel" in data["cols"]
        # Only one "Status"-labeled header should ever appear
        assert data["headers"].count("Status") == 1


# ── Bug 3: parentheses in _extract_after_kw ─────────────────────────────────

class TestExtractAfterKwParens:
    def test_parenthesized_name_extracted_in_full(self):
        assert _extract_after_kw(
            "Have I ever submitted return CIMS_RAQ(Annually)?", "return",
        ) == "CIMS_RAQ(Annually)"

    def test_parenthesized_name_with_monthly_suffix(self):
        assert _extract_after_kw(
            "What is the reporting frequency of return CIMS_RAQ(Monthly)?", "return",
        ) == "CIMS_RAQ(Monthly)"

    def test_plain_name_without_parens_still_works(self):
        # Sanity check the widened character class didn't break the
        # unparenthesized case.
        assert _extract_after_kw(
            "What is the return ID for CIMS_ROR?", "return",
        ) == "ID for CIMS_ROR"  # existing behavior for "return X" pattern unaffected by this fix

    def test_terminator_words_still_stop_capture(self):
        assert _extract_after_kw(
            "does return CIMS_RAQ(Monthly) has encryption", "return",
        ) == "CIMS_RAQ(Monthly)"


@_need_5_5
class TestMySubmissionHistoryWithParenthesizedReturn:
    def test_specific_return_filter_applies_not_full_history(self):
        from backend.db_qa.new_intent_classifier import classify_new_with_semantic_tiers
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control
        from backend.db_qa.query_handlers import dispatch2
        import asyncio

        async def _run():
            intent, params, tt, tier = await classify_new_with_semantic_tiers(
                "Have I ever submitted return CIMS_RAQ(Annually)?"
            )
            assert intent == Intent.MY_SUBMISSION_HISTORY
            assert params.get("target_return") == "CIMS_RAQ(Annually)"

            store = XMLStore(str(PATH_5_5))
            scope = access_control.scope_query(
                {"login_id": "iris810"}, intent.value, params,
            )
            return dispatch2(intent, scope, params, store)

        result = asyncio.run(_run())
        # Must be scoped to the SPECIFIC return, not silently fall through
        # to the caller's entire submission history.
        assert "CIMS_RAQ(Annually)" in result["summary"]
        assert "across" not in result["summary"]  # that phrase only appears in the no-filter branch


# ── Bug 4: MENU_LIST top-level filtering ────────────────────────────────────

class TestMenuListTopLevelQueryType:
    def test_top_level_query_type_extracted(self):
        intent, params, target_type = classify_new("How many top-level menu items are there?")
        assert intent == Intent.MENU_LIST
        assert params.get("query_type") == "top_level"

    def test_plain_menu_question_has_no_query_type(self):
        intent, params, target_type = classify_new("What modules are available in the entire application?")
        assert intent == Intent.MENU_LIST
        assert params.get("query_type") is None


@_need_5_5
class TestMenuListTopLevelFiltering:
    def test_top_level_excludes_nested_items(self):
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control
        from backend.db_qa.query_handlers.menu_handlers import handle_menu_list

        store = XMLStore(str(PATH_5_5))
        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.MENU_LIST.value, {"target_type": "system_wide"},
        )
        all_menu = handle_menu_list(scope, {}, store)
        top_level = handle_menu_list(scope, {"query_type": "top_level"}, store)

        assert top_level["meta"]["count"] < all_menu["meta"]["count"]
        for rec in top_level["records"]:
            assert not (rec.get("ParentOptionId") or "").strip()


# ── Bug 5: audit history missing columns ─────────────────────────────────────

@_need_5_5
class TestReturnNameByIdResolvesFormId:
    """Regression test for a real bug: return_name_by_id() used
    get_attr(r, "ReturnId", "Id") to compare against a FormId — but
    get_attr returns the FIRST present field, and ReturnId (e.g. "R018")
    is virtually always present on a return record, so "Id" (e.g. "2029",
    the field InstanceLog's FormId actually matches) was NEVER checked.
    Every submission-log-derived intent (SUBMISSION_LIST,
    MY_SUBMISSION_HISTORY, SUBMISSION_DETAIL, SUBMISSIONS_FOR_RETURN,
    SUBMISSION_STATUS — all go through enrich_instance_log_entry, which
    calls this method) showed the raw numeric FormId in place of the
    return's name in every "Return" column."""

    def test_numeric_form_id_resolves_to_name(self):
        from backend.db_qa.xml_store import XMLStore

        store = XMLStore(str(PATH_5_5))
        # 2029 is a real Id in the fixture data (confirmed via
        # store.returns()) whose ReturnId is a completely different code
        # ("R018") — this only resolves correctly once Id is actually
        # checked, not just ReturnId.
        name = store.return_name_by_id("2029")
        assert name != "2029", "FormId did not resolve to a return name"

    def test_return_id_code_still_resolves(self):
        from backend.db_qa.xml_store import XMLStore

        store = XMLStore(str(PATH_5_5))
        ret = next((r for r in store.returns() if r.get("ReturnId")), None)
        assert ret is not None, "no return with a ReturnId in fixture data"
        name = store.return_name_by_id(ret["ReturnId"])
        assert name == ret.get("Name")

    def test_submission_list_shows_resolved_return_names(self):
        from backend.db_qa.query_handlers.submission_handlers import handle_submission_list
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control

        store = XMLStore(str(PATH_5_5))
        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.SUBMISSION_LIST.value, {"target_type": "self"},
        )
        result = handle_submission_list(scope, {}, store)
        assert result["found"]
        # None of the resolved return names should still be a bare
        # numeric FormId string.
        for rec in result["records"][:20]:
            assert not rec["ReturnName"].isdigit(), f"unresolved FormId leaked as ReturnName: {rec['ReturnName']!r}"


@_need_5_5
class TestAuditHistoryColumns:
    def test_audit_fields_survive_to_the_table(self):
        from backend.agent.db_qa_router import _build_db_qa_data
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control
        from backend.db_qa.query_handlers.audit_handlers import handle_audit_history

        store = XMLStore(str(PATH_5_5))
        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.AUDIT_HISTORY.value, {"target_type": "self"},
        )
        result = handle_audit_history(scope, {}, store)
        assert result["found"], "expected audit records present for iris810"

        data = _build_db_qa_data(result, intent="audit_history")
        for expected_col in ("UserName", "AuditDateTime", "AuditType", "Remark"):
            assert expected_col in data["cols"], f"{expected_col} missing from {data['cols']}"
        assert data["cols"] != ["UserName"], "regression: table collapsed back to a single repeated column"
