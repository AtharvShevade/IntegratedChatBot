"""SQL agent query context: named-return scoping, explicit reporting dates,
"which return?" clarification and follow-ups on the previous answer."""
from __future__ import annotations

import asyncio
from datetime import date

import pytest

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from backend.sql_agent import context_resolver as cr
from backend.sql_agent import session_context as sc
from backend.sql_agent.latest_date import apply_explicit_date


F010 = "QCB_F010_Maturity Ladder of Assets & Liabilities"
F013 = "QCB_F013_Breakdown of exposures by geography"
F014 = "QCB_F014_Breakdown of Funding by geography"


@pytest.fixture
def catalogue(monkeypatch):
    returns = {}
    for name, tables, codes in (
        (F010, ["qcb_f010_rcm_in_qtr", "qcb_f010_filing_info"], {"f010", "qcb_f010", "4091"}),
        (F013, ["qcb_f013_break_exposure"], {"f013", "qcb_f013", "4079"}),
        (F014, ["qcb_f014_funding_geo"], {"f014", "qcb_f014"}),
    ):
        _codes, title = cr._split_return_name(name)
        returns[name] = cr.ReturnInfo(name=name, tables=tables, codes=codes, title=title)
    monkeypatch.setattr(cr, "load_returns", lambda: returns)
    return returns


@pytest.fixture(autouse=True)
def _clean_sessions():
    sc._store.clear()
    yield
    sc._store.clear()


class TestDetectReturns:
    @pytest.mark.parametrize("q, expected", [
        ("show total assets in F010", [F010]),
        ("assets for f10 please", [F010]),
        ("return 4079 exposures", [F013]),
        ("maturity ladder assets inside qatar", [F010]),
        ("funding by geography for 31-03-2025", [F014]),
        ("show total assets", []),
    ])
    def test_named_returns(self, catalogue, q, expected):
        assert cr.detect_returns(q) == expected

    def test_shared_title_words_match_both_returns(self, catalogue):
        assert set(cr.detect_returns("breakdown by geography")) == {F013, F014}

    def test_tables_and_owners(self, catalogue):
        assert cr.tables_for_returns([F014]) == {"qcb_f014_funding_geo"}
        assert cr.returns_for_tables(["qcb_f013_break_exposure", "QCB_F010_RCM_IN_QTR"]) == [F013, F010]


class TestExtractReportDate:
    @pytest.mark.parametrize("q, start, end", [
        ("assets on 31-03-2025", date(2025, 3, 31), date(2025, 3, 31)),
        ("assets 2025-06-30", date(2025, 6, 30), date(2025, 6, 30)),
        ("31 March 2025 data", date(2025, 3, 31), date(2025, 3, 31)),
        ("as at March 31, 2025", date(2025, 3, 31), date(2025, 3, 31)),
        ("Q1 2025 assets", date(2025, 1, 1), date(2025, 3, 31)),
        ("for march 2025", date(2025, 3, 1), date(2025, 3, 31)),
        ("FY2024 totals", date(2024, 1, 1), date(2024, 12, 31)),
    ])
    def test_single_periods(self, q, start, end):
        p = cr.extract_report_date(q)
        assert (p.start, p.end) == (start, end)

    @pytest.mark.parametrize("q", ["latest assets", "trend since 2023", "compare Q1 2025 and Q2 2025", "total assets"])
    def test_no_single_period(self, q):
        assert cr.extract_report_date(q) is None


class TestApplyExplicitDate:
    T = [{"table": "qcb_f010_rcm_in_qtr"}]

    def test_latest_subquery_is_pinned(self):
        sql = ("SELECT A FROM qcb_f010_rcm_in_qtr WHERE DESCRIPTION = 'Assets' "
               "AND RDATE = (SELECT MAX(RDATE) FROM qcb_f010_rcm_in_qtr)")
        out, changed = apply_explicit_date(sql, self.T, date(2025, 3, 31), date(2025, 3, 31))
        assert changed
        assert out.endswith(
            "RDATE = (SELECT MAX(RDATE) FROM qcb_f010_rcm_in_qtr WHERE RDATE BETWEEN "
            "TO_DATE('2025-03-31', 'YYYY-MM-DD') AND TO_DATE('2025-03-31', 'YYYY-MM-DD'))")

    def test_sql_without_rdate_gets_wrapped(self):
        out, changed = apply_explicit_date("SELECT A FROM qcb_f010_rcm_in_qtr t", self.T,
                                           date(2025, 1, 1), date(2025, 3, 31))
        assert changed and out.endswith(") t")
        assert "TO_DATE('2025-01-01', 'YYYY-MM-DD') AND TO_DATE('2025-03-31', 'YYYY-MM-DD')" in out

    def test_model_written_date_filter_is_kept(self):
        sql = "SELECT A FROM qcb_f010_rcm_in_qtr WHERE RDATE = TO_DATE('2025-03-31', 'YYYY-MM-DD')"
        assert apply_explicit_date(sql, self.T, date(2025, 3, 31), date(2025, 3, 31)) == (sql, False)


def _patch_pipeline(monkeypatch, tables, model_sql="SELECT DESCRIPTION, TOTAL FROM {t}", seen=None):
    import backend.sql_agent.query_handler as qh
    import backend.sql_agent.sql_generator as gen
    import backend.sql_agent.executor as ex

    def _retrieve(q, return_names=None):
        if seen is not None:
            seen.append((q, return_names))
        picked = [t for t in tables if not return_names
                  or t["table"] in cr.tables_for_returns(return_names)]
        return picked, [], [], (None, None), None

    monkeypatch.setattr(qh, "_retrieve", _retrieve)
    monkeypatch.setattr(qh, "_authorize_sql_agent_access", lambda login, t: (True, ""))
    monkeypatch.setattr(gen, "generate_sql",
                        lambda q, tbls, *a, **k: {"sql": model_sql.format(t=tbls[0]["table"]), "warnings": []})
    monkeypatch.setattr(gen, "validate_sql", lambda sql, t, c: (True, "Valid"))
    monkeypatch.setattr(ex, "execute_query",
                        lambda sql: (["DESCRIPTION", "TOTAL"], [("Assets", 10), ("Liabilities", 7)], None))
    return qh


class TestClarificationAndFollowups:
    def test_tables_spanning_two_returns_ask_which_return(self, catalogue, monkeypatch):
        seen = []
        qh = _patch_pipeline(monkeypatch, [{"table": "qcb_f013_break_exposure"},
                                           {"table": "qcb_f014_funding_geo"}], seen=seen)
        r = asyncio.run(qh.handle_db_query("show the total amount by country please", session_id="s1", login_id="u"))
        assert r["need_clarification"] is True
        assert set(r["options"]) == {F013, F014}
        assert sc.looks_like_followup("s1", F014)

        # picking an option re-runs the ORIGINAL question scoped to that return
        r2 = asyncio.run(qh.handle_db_query(F014, session_id="s1", login_id="u"))
        assert r2["need_clarification"] is False
        assert seen[-1][1] == [F014]
        assert "qcb_f014_funding_geo" in r2["db_sql"]

    def test_named_return_scopes_retrieval_and_no_date_means_latest(self, catalogue, monkeypatch):
        seen = []
        qh = _patch_pipeline(monkeypatch, [{"table": "qcb_f013_break_exposure"},
                                           {"table": "qcb_f010_rcm_in_qtr"}], seen=seen)
        r = asyncio.run(qh.handle_db_query("show total assets in F010 maturity ladder", session_id="s2", login_id="u"))
        assert seen[-1][1] == [F010]
        assert "(SELECT MAX(RDATE) FROM qcb_f010_rcm_in_qtr)" in r["db_sql"]
        assert "latest available reporting date" in (r["accuracy_hint"] or "")
        ctx = sc.get("s2")
        assert ctx["returns"] == [F010] and ctx["rows"] == [["Assets", 10], ["Liabilities", 7]]

    def test_question_about_shown_data_is_answered_without_new_sql(self, catalogue, monkeypatch):
        qh = _patch_pipeline(monkeypatch, [{"table": "qcb_f010_rcm_in_qtr"}])
        asyncio.run(qh.handle_db_query("show total assets in F010 maturity ladder", session_id="s3", login_id="u"))

        import backend.services.llm_service as llm
        calls = []

        async def fake_llm(prompt, system, history=None, model=None, temperature=0.1):
            calls.append(prompt)
            if "Classify" in system:
                return '{"type": "data_question"}'
            assert "Assets | 10" in prompt
            return "Assets is the highest at 10."
        monkeypatch.setattr(llm, "_call_ollama", fake_llm)

        import backend.sql_agent.sql_generator as gen
        monkeypatch.setattr(gen, "generate_sql", lambda *a, **k: pytest.fail("no new SQL expected"))
        r = asyncio.run(qh.handle_db_query("which one is highest?", session_id="s3", login_id="u"))
        assert r["response_text"] == "Assets is the highest at 10."
        assert r["db_sql"] == "" and len(calls) == 2

    def test_refine_keeps_previous_return_and_applies_new_date(self, catalogue, monkeypatch):
        seen = []
        qh = _patch_pipeline(monkeypatch, [{"table": "qcb_f010_rcm_in_qtr"}], seen=seen)
        asyncio.run(qh.handle_db_query("show total assets in F010 maturity ladder", session_id="s4", login_id="u"))

        import backend.services.llm_service as llm

        async def fake_llm(prompt, system, history=None, model=None, temperature=0.1):
            return '{"type": "refine", "question": "show total assets for 31-03-2025"}'
        monkeypatch.setattr(llm, "_call_ollama", fake_llm)

        r = asyncio.run(qh.handle_db_query("same for 31-03-2025", session_id="s4", login_id="u"))
        assert seen[-1] == ("show total assets for 31-03-2025", [F010])
        assert "TO_DATE('2025-03-31', 'YYYY-MM-DD')" in r["db_sql"]

    def test_no_context_means_no_followup_routing(self):
        assert not sc.looks_like_followup("nobody", "which one is highest?")
