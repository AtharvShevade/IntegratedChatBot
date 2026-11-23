"""Loose line-item label matching for a generated query that found nothing."""
from backend.sql_agent.label_match import normalize_label, plan_label_fix

ENTRY = {"columns": [
    {"name": "srno", "type": "number", "description": "Serial number"},
    {"name": "description", "type": "varchar2(200)", "description": "Text label of the line item"},
    {"name": "code", "type": "varchar2(20)", "description": "Item code"},
    {"name": "total", "type": "number(20,4)", "description": "Total"},
]}
SQL = ("SELECT TOTAL FROM t1 WHERE DESCRIPTION = 'Term Loans' "
       "AND RDATE = (SELECT MAX(RDATE) FROM t1)")


def _db(labels):
    seen = []

    def run(sql):
        seen.append(sql)
        return ["DESCRIPTION"], [(x,) for x in labels], None
    run.seen = seen
    return run


def test_normalize_ignores_case_space_and_numbering():
    assert normalize_label("(iii)Term Loans") == normalize_label("(iii) Term Loans ") == normalize_label("TERM  loans")
    assert normalize_label("1. Term Loans") == "term loans"


def test_same_label_spelled_differently_uses_all_spellings_and_latest_date_of_those_rows():
    fix = plan_label_fix(SQL, "t1", ENTRY, _db(["(iii)Term Loans", "(iii) Term Loans ", "Term Loans"]))
    assert fix and not fix.ask
    assert "DESCRIPTION IN ('(iii)Term Loans', '(iii) Term Loans ', 'Term Loans')" in fix.sql
    assert "SELECT MAX(RDATE) FROM t1 WHERE DESCRIPTION IN (" in fix.sql


def test_exact_normalized_label_wins_over_longer_labels():
    fix = plan_label_fix(SQL, "t1", ENTRY, _db(["(iii)Term Loans", "Term Loans - Overseas"]))
    assert fix and not fix.ask and fix.labels == ["(iii)Term Loans"]


def test_one_other_label_containing_the_text_is_a_best_guess():
    fix = plan_label_fix(SQL.replace("Term Loans", "Term"), "t1", ENTRY, _db(["(iii)Term Loans"]))
    assert fix and not fix.ask and fix.labels == ["(iii)Term Loans"]


def test_several_different_labels_ask_the_user_instead_of_guessing():
    fix = plan_label_fix(SQL.replace("Term Loans", "Loans"), "t1", ENTRY,
                         _db(["(ii)Cash Credits and Loans", "(iii)Term Loans"]))
    assert fix and fix.ask and fix.sql is None and len(fix.labels) == 2


def test_nothing_found_leaves_the_result_alone():
    assert plan_label_fix(SQL, "t1", ENTRY, _db([])) is None


def test_code_columns_and_multi_table_queries_are_never_touched():
    assert plan_label_fix("SELECT TOTAL FROM t1 WHERE CODE = '1001'", "t1", ENTRY, _db(["x"])) is None
    assert plan_label_fix(SQL.replace("FROM t1", "FROM t1 JOIN t2 ON 1=1"), "t1", ENTRY, _db(["Term Loans"])) is None


def test_literal_with_quote_is_escaped_in_the_probe():
    run = _db(["Bank's Loans"])
    plan_label_fix("SELECT TOTAL FROM t1 WHERE DESCRIPTION = 'Bank''s Loans'", "t1", ENTRY, run)
    assert "BANK''S" in run.seen[0] and ";" not in run.seen[0]
