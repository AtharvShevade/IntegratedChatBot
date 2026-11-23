"""Count rules ("count($V1) = 12 and count($V2) = 12 ..."): the variable that is short lacks the contexts the complete ones carry;
each missing value is placed by the return's mapping, so the blank cell is named. All or nothing."""
from types import SimpleNamespace as NS

from backend.error_improvement import explain_workbook as ew
from backend.error_improvement import presence_rules as pr

EXPR = "(count($V1) = 3) and (count($V2) = 3) and (count($V3) = 4)"


def _lc(var, ctx, concept="C"):
    return NS(fact=NS(var=var, concept=f"{concept}{var}", context=ctx, value="1"))


def _located(v2_ctx):
    a, b, c, extra = ("asof_20260930_AMember_StandaloneMember", "asof_20260930_BMember_StandaloneMember",
                      "asof_20260930_CMember_StandaloneMember", "asof_20260930_AggregateMember_StandaloneMember")
    return {"V1": [_lc("V1", x) for x in (a, b, c)], "V2": [_lc("V2", x) for x in v2_ctx],
            "V3": [_lc("V3", x) for x in (a, b, c, extra)]}, (a, b, c)


def _meta():
    pin = {"Axis": ["StandaloneMember"]}
    return NS(formula_defs={"R": {"vars": {v: {"concepts": [f"C{v}"], "dims": pin} for v in ("V1", "V2", "V3")}}}, reported=None)


def _wb(template=False):
    return NS(sheets=["S"], is_template=template)


def _place(monkeypatch, cells):
    def place(meta, wb, vd, base):
        m = next(iter(base), None)
        return cells.get(m)
    monkeypatch.setattr(pr, "place", place)


CELL = {"sheet": "S", "row": 16, "col": 4, "cell": "D16", "code": "Y040_X020", "how": "x", "workbook_value": None}


def test_missing_value_is_named(monkeypatch):
    loc, (a, b, c) = _located([None, None])
    loc["V2"] = [_lc("V2", a), _lc("V2", c)]                       # V2 lacks B
    _place(monkeypatch, {"BMember": CELL})
    ev = ew._count_missing(NS(name="R"), EXPR, loc, _meta(), _wb())
    req = ev["presence"]["required"]
    assert ev["count_missing"] and len(req) == 1
    assert req[0]["cell"] == "D16" and req[0]["var"] == "V2" and req[0]["workbook_value"] is None
    assert list(req[0]["dims"]) == ["BMember"]                     # only the member that tells it apart, not the shared Standalone


def test_extra_aggregate_value_on_one_variable_is_not_a_candidate(monkeypatch):
    loc, (a, b, c) = _located([None])
    loc["V2"] = [_lc("V2", a), _lc("V2", c)]
    _place(monkeypatch, {"BMember": CELL, "AggregateMember": dict(CELL, cell="E25")})
    ev = ew._count_missing(NS(name="R"), EXPR, loc, _meta(), _wb())
    assert [r["cell"] for r in ev["presence"]["required"]] == ["D16"]


def test_nothing_guessed_when_the_cell_cannot_be_placed(monkeypatch):
    loc, (a, b, c) = _located([None])
    loc["V2"] = [_lc("V2", a), _lc("V2", c)]
    _place(monkeypatch, {})
    assert ew._count_missing(NS(name="R"), EXPR, loc, _meta(), _wb()) is None


def test_several_missing_values_are_all_found(monkeypatch):
    loc, (a, b, c) = _located([None])
    loc["V2"] = [_lc("V2", a)]                                     # needs 3, has 1: B and C are both missing
    _place(monkeypatch, {"BMember": CELL, "CMember": dict(CELL, cell="D17")})
    ev = ew._count_missing(NS(name="R"), EXPR, loc, _meta(), _wb())
    assert sorted(r["cell"] for r in ev["presence"]["required"]) == ["D16", "D17"]


def test_ambiguous_when_the_gap_does_not_match_the_shortfall(monkeypatch):
    loc, (a, b, c) = _located([None])
    loc["V2"] = [_lc("V2", a), _lc("V2", "asof_20260930_OtherMember_StandaloneMember")]   # short by 1, but B and C are both absent
    _place(monkeypatch, {"BMember": CELL, "CMember": dict(CELL, cell="D17")})
    assert ew._count_missing(NS(name="R"), EXPR, loc, _meta(), _wb()) is None


def test_other_shapes_are_left_alone(monkeypatch):
    loc, _ = _located([None])
    _place(monkeypatch, {"BMember": CELL})
    assert ew._count_missing(NS(name="R"), "count($V1) = 3 or $V2 > 1", loc, _meta(), _wb()) is None
    assert ew._count_missing(NS(name="R"), "$V1 = 3", loc, _meta(), _wb()) is None
    assert ew._count_missing(NS(name="R"), EXPR, loc, _meta(), None) is None


def test_template_workbook_names_the_place_but_does_not_check_it(monkeypatch):
    loc, (a, b, c) = _located([None])
    loc["V2"] = [_lc("V2", a), _lc("V2", c)]
    _place(monkeypatch, {"BMember": dict(CELL, workbook_value="7")})
    req = ew._count_missing(NS(name="R"), EXPR, loc, _meta(), _wb(template=True))["presence"]["required"]
    assert req[0]["checked"] is False and req[0]["workbook_value"] is None
