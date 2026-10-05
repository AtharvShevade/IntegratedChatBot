"""H-02: the SQL Agent previously had no identity/authorization check at all
-- handle_db_query(message, session_id=None) took no login_id, so any caller
(even unauthenticated, even hitting the backend API directly) could query any
table the retrieval pipeline shortlisted, regardless of which return it
belonged to or whether their department has access to that return.

Fix: before any SQL is generated, the target return(s) are identified from
the final selected table(s) (via schema.json's existing `return_name` field,
reusing sqlcore.sql_generator._load_table_entries -- no retrieval/FAISS/
selector change) and resolved to a FormId via the existing Returns.xml
resolver (backend.tools.report_lookup.find_matching_reports_tiered -- the
same one status/generate/schedule already use). That FormId is then checked
against the SAME department-scoping the rest of the app already enforces
(backend.db_qa.access_control.resolve_allowed_form_ids, built on
auth_service.get_allowed_form_ids/get_allowed_nx_form_ids). No new
authorization system, no tenant concept -- 5.5 only.

These tests exercise _authorize_sql_agent_access/_resolve_target_return_form_ids
directly (mocking only the two external resolvers: report_lookup's name
resolution and access_control's form-id resolution) and confirm
handle_db_query never reaches generate_sql/execute_query when denied.
"""
from __future__ import annotations

import asyncio

import pytest

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from backend.sql_agent import query_handler as qh


# ── _resolve_target_return_form_ids ─────────────────────────────────────────

class TestResolveTargetReturnFormIds:
    def test_single_table_resolves_to_its_return_form_id(self, monkeypatch):
        import sqlcore.sql_generator as sql_generator

        monkeypatch.setattr(
            sql_generator, "_load_table_entries",
            lambda names: {"cims_raq_q_sec1_part_c_o": {"return_name": "CIMS_RAQ(Quarterly)"}},
        )

        def _fake_find(name):
            assert name == "CIMS_RAQ(Quarterly)"
            return [{"Name": "CIMS_RAQ(Quarterly)", "Id": "2041"}], "exact"

        monkeypatch.setattr(
            "backend.tools.report_lookup.find_matching_reports_tiered", _fake_find,
        )

        form_ids, unresolved = qh._resolve_target_return_form_ids(["cims_raq_q_sec1_part_c_o"])
        assert form_ids == {"2041"}
        assert unresolved == []

    def test_fuzzy_match_is_treated_as_unresolved(self, monkeypatch):
        import sqlcore.sql_generator as sql_generator
        monkeypatch.setattr(
            sql_generator, "_load_table_entries",
            lambda names: {"some_table": {"return_name": "Some Ambiguous Return"}},
        )
        monkeypatch.setattr(
            "backend.tools.report_lookup.find_matching_reports_tiered",
            lambda name: ([{"Name": "Some Ambiguous Return", "Id": "9"},
                           {"Name": "Some Other Return", "Id": "10"}], "fuzzy"),
        )
        form_ids, unresolved = qh._resolve_target_return_form_ids(["some_table"])
        assert form_ids == set()
        assert unresolved == ["Some Ambiguous Return"]

    def test_missing_return_name_metadata_is_unresolved(self, monkeypatch):
        import sqlcore.sql_generator as sql_generator
        monkeypatch.setattr(sql_generator, "_load_table_entries", lambda names: {})
        form_ids, unresolved = qh._resolve_target_return_form_ids(["unknown_table"])
        assert form_ids == set()
        assert unresolved == []

    def test_two_tables_same_return_resolve_to_one_form_id(self, monkeypatch):
        import sqlcore.sql_generator as sql_generator
        monkeypatch.setattr(
            sql_generator, "_load_table_entries",
            lambda names: {
                "t1": {"return_name": "CIMS_ALE_Domestic(Quarterly)"},
                "t2": {"return_name": "CIMS_ALE_Domestic(Quarterly)"},
            },
        )
        monkeypatch.setattr(
            "backend.tools.report_lookup.find_matching_reports_tiered",
            lambda name: ([{"Name": "CIMS_ALE_Domestic(Quarterly)", "Id": "1001"}], "exact"),
        )
        form_ids, unresolved = qh._resolve_target_return_form_ids(["t1", "t2"])
        assert form_ids == {"1001"}
        assert unresolved == []

    def test_two_tables_different_returns_resolve_to_two_form_ids(self, monkeypatch):
        import sqlcore.sql_generator as sql_generator
        monkeypatch.setattr(
            sql_generator, "_load_table_entries",
            lambda names: {
                "t1": {"return_name": "Return A"},
                "t2": {"return_name": "Return B"},
            },
        )
        def _fake_find(name):
            return ([{"Name": name, "Id": "1" if name == "Return A" else "2"}], "exact")
        monkeypatch.setattr("backend.tools.report_lookup.find_matching_reports_tiered", _fake_find)
        form_ids, unresolved = qh._resolve_target_return_form_ids(["t1", "t2"])
        assert form_ids == {"1", "2"}
        assert unresolved == []


# ── _authorize_sql_agent_access ──────────────────────────────────────────────

class TestAuthorizeSqlAgentAccess:
    def _mock_resolution(self, monkeypatch, form_ids={"2041"}, unresolved=[]):
        monkeypatch.setattr(qh, "_resolve_target_return_form_ids", lambda tables: (form_ids, unresolved))

    def test_missing_login_id_is_denied(self, monkeypatch):
        self._mock_resolution(monkeypatch)
        allowed, msg = qh._authorize_sql_agent_access(None, ["t"])
        assert allowed is False
        assert "signed in" in msg.lower()

    def test_empty_login_id_is_denied(self, monkeypatch):
        self._mock_resolution(monkeypatch)
        allowed, msg = qh._authorize_sql_agent_access("   ", ["t"])
        assert allowed is False

    def test_unresolvable_login_id_is_denied(self, monkeypatch):
        self._mock_resolution(monkeypatch)
        def _raise(login_id):
            raise PermissionError("Your account was not recognised. Please contact your administrator.")
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", _raise)
        allowed, msg = qh._authorize_sql_agent_access("ghost-user", ["t"])
        assert allowed is False
        assert "not recognised" in msg.lower()

    def test_authorization_disabled_bypasses_the_check(self, monkeypatch):
        self._mock_resolution(monkeypatch)
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: None)
        allowed, msg = qh._authorize_sql_agent_access("anyone", ["t"])
        assert allowed is True
        assert msg is None

    def test_user_with_access_to_the_target_return_is_allowed(self, monkeypatch):
        self._mock_resolution(monkeypatch, form_ids={"2041"})
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"2041", "9999"})
        allowed, msg = qh._authorize_sql_agent_access("dept_a_user", ["cims_raq_table"])
        assert allowed is True
        assert msg is None

    def test_user_without_access_to_the_target_return_is_denied(self, monkeypatch):
        self._mock_resolution(monkeypatch, form_ids={"2041"})
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"1234"})
        allowed, msg = qh._authorize_sql_agent_access("dept_b_user", ["cims_raq_table"])
        assert allowed is False
        assert "don't currently have access" in msg.lower()

    def test_query_spanning_two_returns_requires_access_to_both(self, monkeypatch):
        self._mock_resolution(monkeypatch, form_ids={"2041", "3333"})
        # User has access to ONE of the two targeted returns, not both.
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"2041"})
        allowed, msg = qh._authorize_sql_agent_access("dept_a_user", ["t1", "t2"])
        assert allowed is False

    def test_unresolved_target_return_is_denied_not_guessed(self, monkeypatch):
        self._mock_resolution(monkeypatch, form_ids=set(), unresolved=["Some Return"])
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"2041"})
        allowed, msg = qh._authorize_sql_agent_access("dept_a_user", ["t"])
        assert allowed is False
        assert "couldn't determine" in msg.lower()

    def test_no_target_return_at_all_is_denied_not_guessed(self, monkeypatch):
        self._mock_resolution(monkeypatch, form_ids=set(), unresolved=[])
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"2041"})
        allowed, msg = qh._authorize_sql_agent_access("dept_a_user", ["t"])
        assert allowed is False

    def test_denied_response_never_leaks_internal_form_ids(self, monkeypatch):
        self._mock_resolution(monkeypatch, form_ids={"2041"})
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"1234"})
        allowed, msg = qh._authorize_sql_agent_access("dept_b_user", ["t"])
        assert "2041" not in msg
        assert "1234" not in msg


# ── handle_db_query integration: denial must short-circuit before generation ─

class TestHandleDbQueryNeverGeneratesOrExecutesWhenDenied:
    """These confirm the gate actually sits where it's supposed to: denial
    must return before generate_sql/execute_query are ever imported-and-called,
    by making both raise if invoked at all."""

    def _patch_retrieval(self, monkeypatch, tables):
        monkeypatch.setattr(
            qh, "_retrieve",
            lambda query: (tables, [], [], (None, None), None),
        )

    def _forbid_generation_and_execution(self, monkeypatch):
        def _boom(*a, **k):
            raise AssertionError("must not be called when access is denied")
        import backend.sql_agent.sql_generator as sql_generator_shim
        import backend.sql_agent.executor as executor_shim
        monkeypatch.setattr(sql_generator_shim, "generate_sql", _boom)
        monkeypatch.setattr(sql_generator_shim, "validate_sql", _boom)
        monkeypatch.setattr(executor_shim, "execute_query", _boom)

    def test_missing_login_id_never_reaches_generation(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": "some_table"}])
        self._forbid_generation_and_execution(monkeypatch)
        result = asyncio.run(qh.handle_db_query(
            "show me all failed CIMS RAQ filings please", login_id=None,
        ))
        assert "signed in" in result["response_text"].lower()
        assert result["db_sql"] == ""
        assert result["db_rows"] == []

    def test_unauthorized_return_never_reaches_generation(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": "cims_raq_q_sec1_part_c_o"}])
        self._forbid_generation_and_execution(monkeypatch)
        monkeypatch.setattr(qh, "_resolve_target_return_form_ids", lambda tables: ({"2041"}, []))
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"9999"})
        result = asyncio.run(qh.handle_db_query(
            "show me all failed CIMS RAQ filings please", login_id="dept_b_user",
        ))
        assert "don't currently have access" in result["response_text"].lower()
        assert result["db_sql"] == ""
        assert result["db_rows"] == []

    def test_authorized_query_proceeds_to_generation(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": "cims_raq_q_sec1_part_c_o"}])
        monkeypatch.setattr(qh, "_resolve_target_return_form_ids", lambda tables: ({"2041"}, []))
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"2041"})

        import backend.sql_agent.sql_generator as sql_generator_shim
        import backend.sql_agent.executor as executor_shim
        monkeypatch.setattr(
            sql_generator_shim, "generate_sql",
            lambda *a, **k: {"sql": "SELECT code FROM cims_raq_q_sec1_part_c_o", "warnings": []},
        )
        monkeypatch.setattr(sql_generator_shim, "validate_sql", lambda sql, tables, columns: (True, "Valid"))
        monkeypatch.setattr(executor_shim, "execute_query", lambda sql: (["CODE"], [("X",)], None))

        result = asyncio.run(qh.handle_db_query(
            "show me all failed CIMS RAQ filings please", login_id="dept_a_user",
        ))
        assert result["db_rows"] == [["X"]]

    def test_exact_qa_match_tier_is_also_gated(self, monkeypatch):
        """The verified-answer short-circuit must not bypass authorization."""
        monkeypatch.setattr(
            qh, "_retrieve",
            lambda query: ([], [], [], None, {
                "sql": "SELECT code FROM cims_raq_q_sec1_part_c_o",
                "table": "cims_raq_q_sec1_part_c_o",
                "text_similarity": 0.99,
            }),
        )
        self._forbid_generation_and_execution(monkeypatch)
        monkeypatch.setattr(qh, "_resolve_target_return_form_ids", lambda tables: ({"2041"}, []))
        monkeypatch.setattr("backend.db_qa.access_control.resolve_allowed_form_ids", lambda login_id: {"9999"})
        result = asyncio.run(qh.handle_db_query(
            "show me all failed CIMS RAQ filings please", login_id="dept_b_user",
        ))
        assert "don't currently have access" in result["response_text"].lower()
        assert result["db_sql"] == ""


# ── Real schema.json integration (no mocks on the schema/table side) ───────

class TestRealSchemaReturnNameResolution:
    """Confirms _load_table_entries + return_name really are present in the
    live 5.5 embeddings set this deployment ships -- not just in a mock."""

    def test_a_real_table_has_a_resolvable_return_name(self):
        from sqlcore.sql_generator import _load_table_entries
        entries = _load_table_entries(["cims_raq_q_sec1_part_c_o"])
        assert "cims_raq_q_sec1_part_c_o" in entries
        assert entries["cims_raq_q_sec1_part_c_o"].get("return_name") == "CIMS_RAQ(Quarterly)"
