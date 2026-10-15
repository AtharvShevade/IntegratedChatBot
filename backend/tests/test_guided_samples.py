"""Version-specific sample names in the guided "Check report status" prompt come
from backend/guided_samples.json (5.5 vs 6.0), and fall back safely."""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

import pytest

import backend.agent  # noqa: F401  (import order: loads the 6.0 config before guided)
from backend import guided, guided_samples, version_config

P55 = "Enter the report name, ReturnId, or short name (e.g. CIMS_ROR, R149, RAQ):"
P60 = ("Enter the report name, ReturnId, or short name "
       "(e.g. QCB_F013_Breakdown of exposures by geography, F013):")


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    guided_samples._cache = None
    yield
    guided_samples._cache = None


def _status_prompt(monkeypatch, v6):
    monkeypatch.setattr(version_config, "IS_V6", v6)
    return asyncio.run(guided.guided_step("Check report status", f"s-{v6}", None))


class TestConfiguredSamples:
    def test_samples_per_version_from_the_json_file(self):
        assert guided_samples.get_samples("check_report_status", "5.5") == ["CIMS_ROR", "R149", "RAQ"]
        assert guided_samples.get_samples("check_report_status", "6.0") == [
            "QCB_F013_Breakdown of exposures by geography", "F013"]

    def test_prompt_text_is_exactly_the_requested_wording(self):
        assert guided_samples.report_name_prompt(guided_samples.get_samples("check_report_status", "5.5")) == P55
        assert guided_samples.report_name_prompt(guided_samples.get_samples("check_report_status", "6.0")) == P60

    def test_version_key_follows_the_existing_version_switch(self, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        assert guided_samples.active_version_key() == "6.0"
        monkeypatch.setattr(version_config, "IS_V6", False)
        assert guided_samples.active_version_key() == "5.5"


class TestGuidedFlow:
    def test_5_5_shows_the_5_5_prompt(self, monkeypatch):
        r = _status_prompt(monkeypatch, False)
        assert r["response_text"] == P55 and r["result_type"] == "guided_input" and r["options"] == []

    def test_6_0_shows_the_6_0_prompt(self, monkeypatch):
        r = _status_prompt(monkeypatch, True)
        assert r["response_text"] == P60 and r["result_type"] == "guided_input" and r["options"] == []

    ACTIONS = {
        "Check report status": "",
        "Generate instance for a report": "",
        "Schedule a report": "",
        "Perform comparative analysis": " to compare",
    }
    EG55 = {
        "Check report status": "CIMS_ROR, R149, RAQ",
        "Generate instance for a report": "CIMS_FormGPB, R009",
        "Schedule a report": "CIMS_RAQ, R162",
        "Perform comparative analysis": "CIMS_RAQ, R009, RAQ",
    }
    EG60 = "QCB_F013_Breakdown of exposures by geography, F013"

    @pytest.mark.parametrize("action", list(ACTIONS))
    def test_all_four_actions_5_5(self, monkeypatch, action):
        monkeypatch.setattr(version_config, "IS_V6", False)
        r = asyncio.run(guided.guided_step(action, "s55-" + action, None))
        assert r["response_text"] == f"Enter the report name, ReturnId, or short name{self.ACTIONS[action]} (e.g. {self.EG55[action]}):"
        assert r["result_type"] == "guided_input"

    @pytest.mark.parametrize("action", list(ACTIONS))
    def test_all_four_actions_6_0(self, monkeypatch, action):
        monkeypatch.setattr(version_config, "IS_V6", True)
        r = asyncio.run(guided.guided_step(action, "s60-" + action, None))
        assert r["response_text"] == f"Enter the report name, ReturnId, or short name{self.ACTIONS[action]} (e.g. {self.EG60}):"
        assert r["result_type"] == "guided_input"
        assert "CIMS_" not in r["response_text"]

    def test_the_session_still_waits_for_the_report_name(self, monkeypatch):
        _status_prompt(monkeypatch, True)
        assert guided._guided_sessions.get("s-True", {}).get("stage") == guided.STAGE_STATUS_REPORT


class TestSqlAgentExamples:
    """"Retrieve data from database": the example questions follow the active version."""

    HEAD = ("What data would you like to query? Please describe in detail "
            "(include report name, section, and time period).")
    Q55 = [
        "What is the credit equivalent current credit exposure for domestic derivatives from ale?",
        "Total loan assets from RAQ section 1 domestic latest",
        "What is the loss provision held on an industry basis from ale?",
    ]
    Q60 = [
        "From the F013 exposure table, show country, total and retail for 30-Apr-2026 only, sorted by total from highest to lowest.",
        "From the F013 breakdown of exposures table, show each country with its sovereigns, banks and retail exposure columns, sorted by total, for the latest reporting date.",
        "How many countries in the F014 funding table have a total funding value above 1 million at the latest reporting date?",
    ]

    def _expected(self, questions):
        return self.HEAD + "\nExamples:\n" + "\n".join("\u2022 " + q for q in questions)

    def test_configured_questions_per_version(self):
        assert guided_samples.get_samples("sql_agent", "5.5") == self.Q55
        assert guided_samples.get_samples("sql_agent", "6.0") == self.Q60

    def test_5_5_prompt_is_exactly_what_it_was_before(self, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", False)
        r = asyncio.run(guided.guided_step("Retrieve data from database", "sql55", None))
        assert r["response_text"] == self._expected(self.Q55)
        assert r["result_type"] == "guided_input" and r["options"] == []

    def test_6_0_prompt_shows_the_6_0_questions(self, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        r = asyncio.run(guided.guided_step("Retrieve data from database", "sql60", None))
        assert r["response_text"] == self._expected(self.Q60)
        assert "ale?" not in r["response_text"] and "RAQ section 1" not in r["response_text"]
        assert r["result_type"] == "guided_input" and r["options"] == []

    def test_the_session_still_waits_for_the_query(self, monkeypatch):
        monkeypatch.setattr(version_config, "IS_V6", True)
        asyncio.run(guided.guided_step("Retrieve data from database", "sqlstage", None))
        assert guided._guided_sessions.get("sqlstage", {}).get("stage") == guided.STAGE_DB_QUERY

    def test_missing_entry_falls_back_to_the_built_in_5_5_questions(self, monkeypatch, tmp_path):
        f = tmp_path / "guided_samples.json"
        f.write_text(json.dumps({"6.0": {"check_report_status": ["F013"]}}), encoding="utf-8")
        monkeypatch.setattr(guided_samples, "_PATH", str(f))
        guided_samples._cache = None
        assert guided_samples.get_samples("sql_agent", "6.0") == self.Q55

    def test_no_examples_gives_just_the_question(self):
        assert guided_samples.sql_agent_prompt([]) == self.HEAD

    def test_a_long_question_survives_the_cleaning(self):
        assert all(len(q) <= guided_samples._MAX_LEN for q in self.Q60)


class TestFallbacks:
    def _use(self, monkeypatch, tmp_path, content):
        f = tmp_path / "guided_samples.json"
        if content is not None:
            f.write_text(content, encoding="utf-8")
        monkeypatch.setattr(guided_samples, "_PATH", str(f))
        guided_samples._cache = None

    def test_missing_file_falls_back_to_the_built_in_samples(self, monkeypatch, tmp_path):
        self._use(monkeypatch, tmp_path, None)
        assert guided_samples.get_samples("check_report_status", "6.0") == ["CIMS_ROR", "R149", "RAQ"]

    def test_malformed_file_falls_back(self, monkeypatch, tmp_path):
        self._use(monkeypatch, tmp_path, "{not json")
        assert guided_samples.get_samples("check_report_status", "5.5") == ["CIMS_ROR", "R149", "RAQ"]

    def test_missing_version_or_action_falls_back(self, monkeypatch, tmp_path):
        self._use(monkeypatch, tmp_path, json.dumps({"5.5": {"check_report_status": ["A1"]}}))
        assert guided_samples.get_samples("check_report_status", "5.5") == ["A1"]
        assert guided_samples.get_samples("check_report_status", "6.0") == ["CIMS_ROR", "R149", "RAQ"]
        assert guided_samples.get_samples("some_other_action", "5.5") == []

    def test_junk_values_are_cleaned(self, monkeypatch, tmp_path):
        self._use(monkeypatch, tmp_path, json.dumps({"6.0": {"check_report_status": ["  F013 ", "", None, "F013", 5, "x" * 500, {"a": 1}]}}))
        assert guided_samples.get_samples("check_report_status", "6.0") == ["F013", "5"]

    def test_empty_list_gives_a_prompt_without_examples(self):
        assert guided_samples.report_name_prompt([]) == "Enter the report name, ReturnId, or short name:"

    def test_a_changed_file_is_picked_up_without_a_restart(self, monkeypatch, tmp_path):
        self._use(monkeypatch, tmp_path, json.dumps({"6.0": {"check_report_status": ["AAA"]}}))
        assert guided_samples.get_samples("check_report_status", "6.0") == ["AAA"]
        f = Path(guided_samples._PATH)
        f.write_text(json.dumps({"6.0": {"check_report_status": ["BBB", "CCC"]}}), encoding="utf-8")
        later = f.stat().st_mtime + 5
        os.utime(f, (later, later))
        assert guided_samples.get_samples("check_report_status", "6.0") == ["BBB", "CCC"]


def test_the_frontend_has_no_hardcoded_sample_names():
    """The frontend only displays response_text; no version-specific sample may live there."""
    src = Path(__file__).parent.parent.parent / "frontend" / "src"
    bad = []
    for f in list(src.rglob("*.js")) + list(src.rglob("*.jsx")):
        text = f.read_text(encoding="utf-8", errors="replace")
        if re.search(r"short name \(e\.g\.|\bR149\b|QCB_F013_Breakdown", text):
            bad.append(f.name)
    assert not bad, bad
