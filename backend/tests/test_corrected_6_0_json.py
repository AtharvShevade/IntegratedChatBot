"""The corrected 6.0 JSON files (flat Json/<return id>.json, top-level
concept_labels, rules with concepts_involved) are located and read correctly by
instance comparison (importance_json) and error explanation (taxonomy_lookup /
formula_error), without changing how 5.5 resolves its JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from backend import config, version_config
from backend.tools import importance_json, taxonomy_lookup
from backend.tools.importance_json import JsonImportance, usable_label
from backend.tools.return_json_path import flat_return_json_path


def _payload(code="4092", **over):
    p = {
        "return_metadata": {"return_code": code,
                            "regulatory_importance_status": {"available": True,
                                                             "sections": {"fcnop-table": "Fcnop table"}}},
        "structure": {"axes": [{"axis_name": "qcb:DE000004", "members": ["qcb:DM000012"]}],
                      "member_labels": {"qcb:DM000012": "Total"}},
        "concept_labels": {
            "PE000001": "Readable only in concept_labels",
            "qcb:PE000001": "Readable only in concept_labels",
            "DebtSecuritiesDomain": "qcb-part:DebtSecuritiesDomain",     # qname echo = no real label
        },
        "concepts": [
            {"concept_id": "qcb:PE001248", "label": "Capital ratio",
             "regulatory_importance": {"matched": True, "score": 39.1, "tier": "Medium", "section_code": "fcnop-table"},
             "db_mapping": {"status": "confirmed", "table_name": "QCB_F015_RATIO", "value_column": "VALUE",
                            "filter_column": "CODE", "filter_value": "R1"}},
            {"concept_id": "qcb:PE001200", "label": "",
             "regulatory_importance": {"matched": True, "score": 10.0, "tier": "Low", "section_code": "fcnop-table"},
             "db_mapping": {"status": "unmapped", "table_name": None, "column_name": None}},
            {"concept_id": "qcb:PE001300", "label": "PE001300",     # label just echoes the id
             "regulatory_importance": {"matched": True, "score": 10.0, "tier": "Low", "section_code": "fcnop-table"}},
        ],
        "validation_rules": [
            {"assertion_id": "F015_Calc_29", "expression": "$V1 = $V2",
             "concepts_involved": [
                 {"concept_id": "qcb:PE001248", "variable_name": "V1", "role": "lhs_total",
                  "dimensional_qualification": ["qcb:DE000004"]},                         # axis only
                 {"concept_id": "qcb:PE001200", "variable_name": "V2", "role": "rhs_variable",
                  "dimensional_qualification": ["Axis=Member"]}]},
        ],
    }
    p.update(over)
    return p


@pytest.fixture
def json_dir(tmp_path, monkeypatch):
    d = tmp_path / "JSON"            # on disk "JSON"; the code asks for "Json"
    d.mkdir()
    monkeypatch.setattr(config, "json_metadata_base_dir", lambda: str(tmp_path / "Json"))
    taxonomy_lookup._TAXONOMY_CACHE.clear()
    importance_json._CACHE.clear()
    return d


def _write(d, rid, payload):
    (d / f"{rid}.json").write_text(json.dumps(payload), encoding="utf-8")


# ── 1. path resolution ──────────────────────────────────────────────────────
class TestFlatPathResolution:
    def test_flat_file_found_even_when_folder_case_differs(self, json_dir):
        _write(json_dir, "4092", _payload())
        assert flat_return_json_path("4092").lower() == str(json_dir / "4092.json").lower()

    def test_each_return_gets_only_its_own_file(self, json_dir):
        _write(json_dir, "4092", _payload("4092"))
        _write(json_dir, "4091", _payload("4091"))
        assert flat_return_json_path("4091").endswith("4091.json")
        assert flat_return_json_path("4092").endswith("4092.json")
        assert flat_return_json_path("4093") is None          # never "the next best" file

    def test_blank_and_traversal_ids_are_safe(self, json_dir):
        _write(json_dir, "4092", _payload())
        assert flat_return_json_path("") is None
        assert flat_return_json_path(None) is None
        got = flat_return_json_path("..\\..\\4092")                                  # reduced to a bare name
        assert got and got.lower() == str(json_dir / "4092.json").lower()


# ── 2. error-explanation loader ─────────────────────────────────────────────
class TestTaxonomyLookupLoader:
    def test_6_0_loads_the_flat_file(self, json_dir, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        _write(json_dir, "4092", _payload())
        t = taxonomy_lookup.get_return_json("4092")
        assert t and "F015_Calc_29" in t["by_assertion_id"] and t["return_code"] == "4092"

    def test_5_5_behaviour_is_unchanged_flat_files_are_not_picked_up(self, json_dir, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", False)
        _write(json_dir, "4092", _payload())
        assert taxonomy_lookup.get_return_json("4092") is None

    def test_the_original_folder_layout_still_works_in_both_versions(self, json_dir, monkeypatch):
        for v6 in (True, False):
            taxonomy_lookup._TAXONOMY_CACHE.clear()
            monkeypatch.setattr(version_config, "IS_V6", v6)
            folder = json_dir / "7777"
            folder.mkdir(exist_ok=True)
            (folder / "anything.json").write_text(json.dumps(_payload("7777")), encoding="utf-8")
            assert taxonomy_lookup.get_return_json("7777") is not None

    def test_missing_malformed_and_foreign_json_fail_safely(self, json_dir, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        assert taxonomy_lookup.get_return_json("4092") is None                      # missing
        (json_dir / "4092.json").write_text("{not json", encoding="utf-8")
        assert taxonomy_lookup.get_return_json("4092") is None                      # malformed
        _write(json_dir, "4091", _payload("4092"))                                  # 4091 file that says it is 4092
        assert taxonomy_lookup.get_return_json("4091") is None                      # refused


# ── 3. labels ───────────────────────────────────────────────────────────────
class TestUsableLabel:
    @pytest.mark.parametrize("label,local,expected", [
        ("Surplus/deficit ratio", "PE001248", "Surplus/deficit ratio"),
        ("", "PE001248", ""), (None, "PE001248", ""), ("   ", "PE001248", ""),
        ("PE001248", "PE001248", ""), ("pe001248", "PE001248", ""),
        ("qcb:PE001248", "PE001248", ""), ("qcb-part:DebtSecuritiesDomain", "DebtSecuritiesDomain", ""),
        ("Inside Qatar [member]", "DM000010", "Inside Qatar"),
        # 5.5-style names: a word equal to its own concept name IS the label
        ("Loans", "Loans", "Loans"), ("AccumulatedLosses", "AccumulatedLosses", "AccumulatedLosses"),
    ])
    def test_cases(self, label, local, expected):
        assert usable_label(label, local) == expected


class TestLabelResolutionForExplanation:
    def _t(self, json_dir, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        _write(json_dir, "4092", _payload())
        return taxonomy_lookup.get_return_json("4092")

    def test_concept_label_then_concept_labels_then_nothing(self, json_dir, monkeypatch):
        t = self._t(json_dir, monkeypatch)
        assert taxonomy_lookup.resolve_concept_label(t, "qcb:PE001248") == "Capital ratio"
        assert taxonomy_lookup.resolve_concept_label(t, "qcb:PE000001") == "Readable only in concept_labels"
        assert taxonomy_lookup.resolve_concept_label(t, "qcb:PE001300") == ""        # id echo is not a label
        assert taxonomy_lookup.resolve_concept_label(t, "qcb-part:DebtSecuritiesDomain") == ""

    def test_rule_variables_are_adapted_from_concepts_involved(self, json_dir, monkeypatch):
        t = self._t(json_dir, monkeypatch)
        rule = t["by_assertion_id"]["F015_Calc_29"]
        vs = {v["name"]: v for v in taxonomy_lookup.rule_variables(rule, t)}
        assert set(vs) == {"V1", "V2"}
        assert vs["V1"]["concept_id"] == "qcb:PE001248"
        assert vs["V1"]["dimensional_qualification"] == []                  # bare axis id dropped
        assert vs["V2"]["dimensional_qualification"] == ["Axis=Member"]     # axis=member kept
        assert vs["V1"]["db_mapping"]["table"] == "QCB_F015_RATIO"
        assert vs["V1"]["db_mapping"]["code_filter"] == "R1"
        assert vs["V2"]["db_mapping"] == {}                                 # unmapped -> nothing

    def test_older_variables_key_is_still_honoured(self):
        rule = {"variables": [{"name": "V1", "concept_id": "x:A"}], "concepts_involved": [{"variable_name": "V9"}]}
        assert [v["name"] for v in taxonomy_lookup.rule_variables(rule, {})] == ["V1"]

    def test_formula_explainer_map_uses_the_new_rule_shape(self, json_dir, monkeypatch):
        from backend.tools import formula_error
        t = self._t(json_dir, monkeypatch)
        m = formula_error._json_variable_map(t, "F015_Calc_29")
        assert m["V1"]["label"] == "Capital ratio"
        assert m["V1"]["db_location"] == "QCB_F015_RATIO.VALUE (code R1)"
        assert m["V1"]["dimensional_qualification"] == []
        assert m["V2"]["label"] == ""                                       # no usable label -> cascade continues


class TestInstanceComparisonLabels:
    def _idx(self, p):
        return JsonImportance("4092", "x.json", p)

    def test_concept_level_label_first(self):
        assert self._idx(_payload()).score_concept("PE001248")["label"] == "Capital ratio"

    def test_concept_labels_is_used_when_the_concept_level_label_is_missing_or_an_echo(self):
        idx = self._idx(_payload(concept_labels={"PE001200": "Bank Capital Base", "PE001300": "Other Reserve"}))
        assert idx.score_concept("PE001200")["label"] == "Bank Capital Base"      # concept-level label empty
        assert idx.score_concept("PE001300")["label"] == "Other Reserve"          # concept-level label echoed the id

    def test_a_concept_missing_from_concepts_still_gets_its_label_but_stays_unscored(self):
        prof = self._idx(_payload()).score_concept("PE000001")
        assert prof["label"] == "Readable only in concept_labels"
        assert prof["matched"] is False and prof["tier"] == "" and prof["score"] is None

    def test_member_labels_and_domain_echo(self):
        idx = self._idx(_payload())
        assert idx.label_for("DM000012") == "Total"
        assert idx.label_for("DebtSecuritiesDomain") == ""

    def test_no_label_anywhere_means_empty_so_callers_can_fall_back(self):
        assert self._idx(_payload()).score_concept("PE999999")["label"] == ""

    def test_old_files_without_concept_labels_behave_as_before(self):
        p = _payload()
        del p["concept_labels"]
        idx = self._idx(p)
        assert idx.score_concept("PE001248")["label"] == "Capital ratio"
        assert idx.score_concept("PE000001")["label"] == ""

    def test_comparison_loader_refuses_another_returns_file(self, json_dir, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        _write(json_dir, "4091", _payload("4092"))
        assert importance_json.get_importance_from_json("4091") is None
        _write(json_dir, "4092", _payload("4092"))
        assert importance_json.get_importance_from_json("4092") is not None

    def test_comparison_loader_survives_missing_and_malformed_files(self, json_dir, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        assert importance_json.get_importance_from_json("4092") is None
        (json_dir / "4092.json").write_text("{oops", encoding="utf-8")
        assert importance_json.get_importance_from_json("4092") is None


# ── 4. the real corrected files ─────────────────────────────────────────────
REAL = Path(r"D:\Repo6.0\1001\JSON")
real_only = pytest.mark.skipif(not (REAL / "4092.json").exists(), reason="corrected 6.0 JSON not on this machine")


@real_only
class TestRealCorrectedFiles:
    @pytest.fixture(autouse=True)
    def _scope(self, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        taxonomy_lookup._TAXONOMY_CACHE.clear()
        importance_json._CACHE.clear()
        with version_config.repo_scope(r"D:\Repo6.0\1001"):
            yield

    @pytest.mark.parametrize("rid", ["4079", "4080", "4091", "4092", "4101", "4106", "4110"])
    def test_both_features_load_the_same_return_specific_file(self, rid):
        t = taxonomy_lookup.get_return_json(rid)
        i = importance_json.get_importance_from_json(rid)
        assert t and i
        assert t["return_code"] == rid and os.path.basename(t["path"]) == f"{rid}.json"

    def test_returns_do_not_share_one_concept_set(self):
        sets = {rid: set(taxonomy_lookup.get_return_json(rid)["by_concept_id"]) for rid in ("4091", "4092", "4101")}
        assert sets["4091"] != sets["4092"] != sets["4101"]
        assert len(sets["4091"]) == 132 and len(sets["4092"]) == 44

    def test_f015_variables_resolve_to_readable_names(self):
        t = taxonomy_lookup.get_return_json("4092")
        from backend.tools import formula_error
        m = formula_error._json_variable_map(t, "F015_Calc_29")
        assert m["V3"]["label"] == "Bank Capital Base"
        assert all(not v["label"].startswith("PE") for v in m.values())

    @pytest.mark.parametrize("rid,section", [("4092", "Fcnop table 001"), ("4091", "Inside table")])
    def test_sections_come_from_the_returns_own_tables(self, rid, section):
        i = importance_json.get_importance_from_json(rid)
        secs = {c: i.score_concept(c)["section"] for c in list(i._by_local)}
        assert section in secs.values()
        assert "Breakdown of exposures by geography" not in {secs[c] for c in secs if c.startswith("PE0012")}
