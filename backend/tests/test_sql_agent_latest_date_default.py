"""When the question names no date, the SQL agent must default to the latest
reporting period (RDATE = MAX(RDATE)) - and must leave everything else alone."""
from __future__ import annotations

import json as _json

import pytest

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from backend.sql_agent.latest_date import apply_latest_date_default, query_implies_period

T = {"table": "QCB_F014_FUNDING_GEO"}
TABLES = [T]


def _apply(sql, query="show total funding by country", tables=TABLES):
    return apply_latest_date_default(sql, tables, query_implies_period(query))


class TestWhenTheDefaultApplies:
    def test_single_table_without_alias(self):
        sql = "SELECT COUNTRY, SUM(TOTAL) FROM QCB_F014_FUNDING_GEO GROUP BY COUNTRY"
        out, changed = _apply(sql)
        assert changed
        assert out == (
            "SELECT COUNTRY, SUM(TOTAL) FROM (SELECT * FROM QCB_F014_FUNDING_GEO WHERE RDATE = "
            "(SELECT MAX(RDATE) FROM QCB_F014_FUNDING_GEO)) QCB_F014_FUNDING_GEO GROUP BY COUNTRY")

    def test_alias_is_kept_and_qualified_columns_still_resolve(self):
        sql = "SELECT q.COUNTRY, q.TOTAL FROM QCB_F014_FUNDING_GEO q WHERE q.TOTAL > 5 ORDER BY q.TOTAL DESC"
        out, changed = _apply(sql)
        assert changed
        assert ") q WHERE q.TOTAL > 5 ORDER BY q.TOTAL DESC" in out
        assert out.count("MAX(RDATE)") == 1

    def test_as_alias_and_lowercase_table_name(self):
        out, changed = _apply("select q.country from qcb_f014_funding_geo as q")
        assert changed and ") as q" in out

    def test_table_referenced_in_a_subquery_and_a_join_is_wrapped_everywhere(self):
        tables = TABLES + [{"table": "QCB_F013_GEO"}]
        sql = ("SELECT a.COUNTRY FROM QCB_F014_FUNDING_GEO a JOIN QCB_F013_GEO b ON a.CODE = b.CODE "
               "WHERE a.TOTAL > (SELECT AVG(TOTAL) FROM QCB_F014_FUNDING_GEO)")
        out, changed = _apply(sql, tables=tables)
        assert changed
        assert out.count("MAX(RDATE)") == 3
        assert ") a JOIN (SELECT * FROM QCB_F013_GEO" in out and ") b ON a.CODE" in out

    def test_a_clause_keyword_after_the_table_is_not_mistaken_for_an_alias(self):
        out, changed = _apply("SELECT COUNTRY FROM QCB_F014_FUNDING_GEO WHERE TOTAL > 1")
        assert changed
        assert ")) QCB_F014_FUNDING_GEO WHERE TOTAL > 1" in out


class TestWhenItMustNotApply:
    def test_the_model_already_handled_the_period(self):
        for sql in (
            "SELECT * FROM QCB_F014_FUNDING_GEO WHERE RDATE = (SELECT MAX(RDATE) FROM QCB_F014_FUNDING_GEO)",
            "SELECT * FROM QCB_F014_FUNDING_GEO WHERE RDATE = TO_DATE('2026-04-30','YYYY-MM-DD')",
            "SELECT RDATE, SUM(TOTAL) FROM QCB_F014_FUNDING_GEO GROUP BY RDATE",
        ):
            assert _apply(sql) == (sql, False)

    @pytest.mark.parametrize("question", [
        "show total funding by country for 30 April 2026",
        "funding by country in April 2026",
        "funding by country for Q1 FY2026",
        "funding by country as of 30-Apr-2026",
        "funding by country on 2026-04-30",
        "funding by country for last quarter",
        "funding by country over the last 3 months",
        "funding trend by country",
        "funding by country over time",
        "month wise funding by country",
        "compare funding by country with last year",
        "funding by country between January and March",
        "funding by country year to date",
        "funding by country today",
        "funding by country each quarter",
        "funding by country from january to march",
    ])
    def test_a_date_or_multi_period_question_is_left_alone(self, question):
        sql = "SELECT COUNTRY, SUM(TOTAL) FROM QCB_F014_FUNDING_GEO GROUP BY COUNTRY"
        assert query_implies_period(question), question
        assert _apply(sql, question) == (sql, False)

    @pytest.mark.parametrize("question", [
        "show total funding by country",
        "what is the total funded exposure by country",
        "give me the latest funding by country",
        "list countries with the highest funding",
    ])
    def test_a_question_with_no_date_is_detected(self, question):
        assert not query_implies_period(question), question

    def test_comma_join_and_unselected_tables_are_left_alone(self):
        for sql in (
            "SELECT a.X FROM QCB_F014_FUNDING_GEO a, QCB_F014_FUNDING_GEO b WHERE a.CODE = b.CODE",
            "SELECT X FROM SOME_OTHER_TABLE",
        ):
            assert _apply(sql) == (sql, False)

    def test_empty_inputs(self):
        assert apply_latest_date_default("", TABLES, False) == ("", False)
        assert apply_latest_date_default("SELECT 1 FROM DUAL", [], False) == ("SELECT 1 FROM DUAL", False)


class TestRewrittenSqlStillPassesTheAgentsOwnValidation:
    def test_validate_sql_accepts_the_rewritten_query_on_a_real_table(self):
        from sqlcore import config as sql_config
        from sqlcore.sql_generator import validate_sql
        schema = _json.load(open(f"{sql_config.EMBEDDING_DIR}/schema.json", encoding="utf-8"))
        entry = schema[0]
        table = entry.get("table") or entry.get("table_name")
        cols = [c.get("name") if isinstance(c, dict) else c for c in entry.get("columns", [])]
        metric = next((c for c in cols if str(c).upper() not in ("CODE", "RDATE")), None)
        if not (table and metric):
            pytest.skip("no usable table in the active embeddings")
        tables = [{"table": table}]
        columns = [{"table": table, "column": c} for c in cols]
        original = f"SELECT {metric} FROM {table}"
        ok_before, _ = validate_sql(original, tables, columns)
        rewritten, changed = apply_latest_date_default(original, tables, False)
        assert changed
        ok_after, why = validate_sql(rewritten, tables, columns)
        assert ok_after or not ok_before, why


class TestHandlerIntegration:
    """handle_db_query applies the default only when the question names no date."""

    def _run(self, monkeypatch, question, model_sql, validate=lambda sql, t, c: (True, "Valid")):
        import asyncio
        import backend.sql_agent.query_handler as qh
        import backend.sql_agent.sql_generator as gen
        import backend.sql_agent.executor as ex
        tables = [{"table": "cims_ale_q_anx_1_a"}]
        monkeypatch.setattr(qh, "_retrieve", lambda q: (tables, [], [], (None, None), None), raising=False)
        monkeypatch.setattr(qh, "_authorize_sql_agent_access", lambda login, t: (True, ""), raising=False)
        monkeypatch.setattr(gen, "generate_sql", lambda *a, **k: {"sql": model_sql, "warnings": []})
        monkeypatch.setattr(gen, "validate_sql", validate)
        monkeypatch.setattr(ex, "execute_query", lambda sql: (["CODE"], [("X",)], None))
        return asyncio.run(qh.handle_db_query(question, login_id="any"))

    def test_no_date_in_the_question_gets_the_latest_period(self, monkeypatch):
        r = self._run(monkeypatch, "show me the total exposure please",
                      "SELECT code FROM cims_ale_q_anx_1_a")
        assert "WHERE RDATE = (SELECT MAX(RDATE) FROM cims_ale_q_anx_1_a)" in r["db_sql"]

    def test_a_date_in_the_question_leaves_the_sql_alone(self, monkeypatch):
        r = self._run(monkeypatch, "show me the total exposure for 31 March 2026",
                      "SELECT code FROM cims_ale_q_anx_1_a")
        assert r["db_sql"] == "SELECT code FROM cims_ale_q_anx_1_a"

    def test_if_the_rewrite_fails_validation_the_model_sql_is_kept(self, monkeypatch):
        def validate(sql, t, c):
            return ("MAX(RDATE)" not in sql, "rejected")
        r = self._run(monkeypatch, "show me the total exposure please",
                      "SELECT code FROM cims_ale_q_anx_1_a", validate=validate)
        assert r["db_sql"] == "SELECT code FROM cims_ale_q_anx_1_a"
