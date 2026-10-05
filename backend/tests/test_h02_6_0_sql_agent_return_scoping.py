"""H-02, APP_VERSION=6.0: proves the SAME authorization gate added for 5.5
(backend/sql_agent/query_handler.py::_authorize_sql_agent_access /
_resolve_target_return_form_ids) is ALREADY correct for 6.0 -- NOT a separate
implementation, NO 6.0-specific code was written.

Why no new code was needed (see doc/CRITICAL_FIXES_LOG.md's H-02 6.0 entry for
the full writeup): every function the 5.5 gate reuses already goes through
this app's existing version-aware abstraction layer, which was NOT built for
this task -- it already existed:
  - backend.tools.report_lookup.find_matching_reports_tiered() resolves a
    return name via backend.config.returns_xml_path(), which already switches
    on version_config.IS_V6 (Return.xml vs Returns.xml) and reads from
    version_config.get_repo_root_override() (the per-request tenant root),
    not a hardcoded 5.5 path.
  - backend.db_qa.access_control.resolve_allowed_form_ids() ->
    auth_service.get_allowed_form_ids()/get_allowed_nx_form_ids() already
    handle 6.0's different XML filenames/attributes/delimiters (Department.xml
    vs XML_Dept.xml, ReturnId vs Forms, comma vs pipe -- the pre-existing D1/D2
    fix, see test_auth_service_dept_delimiter.py).
  - sqlcore.sql_generator._load_table_entries() reads schema.json from
    config.EMBEDDING_DIR, which the SQL Agent's own _bootstrap.py already
    points at embeddings_6.0 under APP_VERSION=6.0 (a process-level constant,
    unaffected by this change).
  - main.py's /chat and /guided handlers already wrap the ENTIRE decide()/
    guided_step() call (and therefore handle_db_query, called deep inside
    either) in version_config.repo_scope(tenant_root, tenant_id, jwt,
    login_id) -- so by the time the authorization gate runs, the tenant
    context is already correctly active, and the gate's own call site (not
    wrapped in asyncio.to_thread) runs in that same context directly.

These tests exercise the EXACT SAME functions test_h02_sql_agent_return_scoping.py
does, but against this machine's real D:\\Repo6.0 tenant data (tenant 1001) and
the real embeddings_6.0/schema.json -- proving the claim empirically rather
than just by code-reading.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from backend.sql_agent import query_handler as qh
from backend import version_config

_TENANT_ROOT = Path(r"D:\Repo6.0\1001")
_EMBEDDINGS_6_0 = Path(__file__).resolve().parents[2] / "backend" / "sql_agent" / "embeddings_6.0"

# backend/config.py's _USER_FILENAME/_DEPT_FILENAME/_RETURNS_FILENAME (and the
# SQL Agent's own EMBEDDING_DIR selection in _bootstrap.py) are process-level
# constants computed ONCE from APP_VERSION at import time -- same convention
# used throughout this app (see _bootstrap.py's own docstring on
# EMBEDDING_DIR). They cannot be flipped mid-process by monkeypatching
# version_config.IS_V6 afterward (verified: doing so left auth_service still
# looking for XML_User.xml/XML_Dept.xml, the 5.5 filenames, under the 6.0
# tenant root). This suite therefore only runs meaningfully in a process that
# was ALREADY started with APP_VERSION=6.0 and APP_600_REPO_ROOT=D:\Repo6.0 --
# e.g.:
#   APP_VERSION=6.0 APP_600_REPO_ROOT=D:\Repo6.0 pytest backend/tests/test_h02_6_0_sql_agent_return_scoping.py
# Run this way at least once after any change to the H-02 gate; it is skipped
# (not failed) under the default 5.5 test-suite invocation.
pytestmark = pytest.mark.skipif(
    not version_config.IS_V6
    or not (_TENANT_ROOT / "DataBase" / "Return.xml").is_file()
    or not (_EMBEDDINGS_6_0 / "schema.json").is_file(),
    reason="requires a process started with APP_VERSION=6.0 APP_600_REPO_ROOT=D:\\Repo6.0 "
           "(see module docstring) and real 6.0 tenant data / embeddings_6.0 on this machine",
)

# Dept 7 "Finanace": ReturnId includes 4079, 4080, 4091, 4092 -- the exact 4
# returns embeddings_6.0/schema.json covers (QCB_F010/013/014/015).
_ALLOWED_LOGIN = "vaibhav@irisindia.net"
# Dept 1 "Compliance": ReturnId="2029,4089,4070" -- none of embeddings_6.0's
# 4 returns.
_DENIED_LOGIN = "checker1@irisindia.net"

_QCB_F010_TABLE = "qcb_f010_filing_info"  # return_name: "QCB_F010_Maturity Ladder of Assets & Liabilities", Id=4091


@pytest.fixture(autouse=True)
def _use_6_0_embeddings_and_tenant(monkeypatch):
    """Point the SQL Agent's own schema/return-resolution machinery at the
    real 6.0 artifacts (normally selected once by _bootstrap.py at process
    start -- this just targets the exact same embeddings_6.0 tree explicitly,
    no different from what a real 6.0 process already resolves on its own),
    and activate a real 6.0 tenant repo_scope -- exactly what main.py's
    /chat handler already does per-request under APP_VERSION=6.0.
    """
    import sqlcore.config as sql_config
    monkeypatch.setattr(sql_config, "EMBEDDING_DIR", str(_EMBEDDINGS_6_0))

    with version_config.repo_scope(str(_TENANT_ROOT), tenant_id="1001", jwt=None, login_id=None):
        yield


class TestRealSchemaReturnNameResolution6_0:
    def test_qcb_f010_table_has_its_real_return_name(self):
        from sqlcore.sql_generator import _load_table_entries
        entries = _load_table_entries([_QCB_F010_TABLE])
        assert entries[_QCB_F010_TABLE]["return_name"] == "QCB_F010_Maturity Ladder of Assets & Liabilities"


class TestResolveTargetReturnFormIds6_0:
    def test_resolves_to_the_real_return_xml_form_id(self):
        form_ids, unresolved = qh._resolve_target_return_form_ids([_QCB_F010_TABLE])
        assert form_ids == {"4091"}
        assert unresolved == []


class TestAuthorizeSqlAgentAccess6_0:
    def test_department_with_access_is_allowed(self):
        allowed, msg = qh._authorize_sql_agent_access(_ALLOWED_LOGIN, [_QCB_F010_TABLE])
        assert allowed is True
        assert msg is None

    def test_department_without_access_is_denied(self):
        allowed, msg = qh._authorize_sql_agent_access(_DENIED_LOGIN, [_QCB_F010_TABLE])
        assert allowed is False
        assert "don't currently have access" in msg.lower()

    def test_missing_login_id_is_denied(self):
        allowed, msg = qh._authorize_sql_agent_access(None, [_QCB_F010_TABLE])
        assert allowed is False

    def test_unresolvable_login_id_is_denied(self):
        allowed, msg = qh._authorize_sql_agent_access("no-such-user@nowhere.test", [_QCB_F010_TABLE])
        assert allowed is False
        assert "not recognised" in msg.lower()

    def test_another_users_identity_cannot_be_supplied_to_gain_access(self):
        """Confirms the gate always re-resolves allowed FormIds fresh from
        login_id -- there is no cached/trusted-without-lookup path a caller
        could exploit by merely naming someone else's login_id string;
        whether that string is itself trustworthy is the standing,
        out-of-scope C-02 caveat (unchanged here), but IF it resolves to a
        real department, that department's real permissions are what apply
        -- never the caller's own or a blanket allow."""
        allowed_as_denied_user, _ = qh._authorize_sql_agent_access(_DENIED_LOGIN, [_QCB_F010_TABLE])
        allowed_as_allowed_user, _ = qh._authorize_sql_agent_access(_ALLOWED_LOGIN, [_QCB_F010_TABLE])
        assert allowed_as_denied_user is False
        assert allowed_as_allowed_user is True


class TestHandleDbQueryIntegration6_0:
    def _patch_retrieval(self, monkeypatch, tables):
        monkeypatch.setattr(qh, "_retrieve", lambda query: (tables, [], [], (None, None), None))

    def _forbid_generation_and_execution(self, monkeypatch):
        def _boom(*a, **k):
            raise AssertionError("must not be called when access is denied")
        import backend.sql_agent.sql_generator as sql_generator_shim
        import backend.sql_agent.executor as executor_shim
        monkeypatch.setattr(sql_generator_shim, "generate_sql", _boom)
        monkeypatch.setattr(sql_generator_shim, "validate_sql", _boom)
        monkeypatch.setattr(executor_shim, "execute_query", _boom)

    def test_denied_6_0_user_never_reaches_generation(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": _QCB_F010_TABLE}])
        self._forbid_generation_and_execution(monkeypatch)
        result = asyncio.run(qh.handle_db_query(
            "show me the maturity ladder filing information please", login_id=_DENIED_LOGIN,
        ))
        assert "don't currently have access" in result["response_text"].lower()
        assert result["db_sql"] == ""
        assert result["db_rows"] == []

    def test_allowed_6_0_user_proceeds_to_generation(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": _QCB_F010_TABLE}])
        import backend.sql_agent.sql_generator as sql_generator_shim
        import backend.sql_agent.executor as executor_shim
        monkeypatch.setattr(
            sql_generator_shim, "generate_sql",
            lambda *a, **k: {"sql": f"SELECT code FROM {_QCB_F010_TABLE}", "warnings": []},
        )
        monkeypatch.setattr(sql_generator_shim, "validate_sql", lambda sql, tables, columns: (True, "Valid"))
        monkeypatch.setattr(executor_shim, "execute_query", lambda sql: (["CODE"], [("X",)], None))

        result = asyncio.run(qh.handle_db_query(
            "show me the maturity ladder filing information please", login_id=_ALLOWED_LOGIN,
        ))
        assert result["db_rows"] == [["X"]]

    def test_exact_qa_match_tier_is_also_gated_for_6_0(self, monkeypatch):
        monkeypatch.setattr(
            qh, "_retrieve",
            lambda query: ([], [], [], None, {
                "sql": f"SELECT code FROM {_QCB_F010_TABLE}",
                "table": _QCB_F010_TABLE,
                "text_similarity": 0.99,
            }),
        )
        self._forbid_generation_and_execution(monkeypatch)
        result = asyncio.run(qh.handle_db_query(
            "show me the maturity ladder filing information please", login_id=_DENIED_LOGIN,
        ))
        assert "don't currently have access" in result["response_text"].lower()
        assert result["db_sql"] == ""
