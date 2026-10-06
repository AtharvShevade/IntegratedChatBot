"""Regression tests: comparative-analysis instance discovery reads the
instance log (XML_InstanceLog.xml / InstanceLog.xml) instead of scanning the
Instance folder and parsing filenames with a regex.

Bug 1: comparative analysis reported "No instance files found" for a 6.0
report even though D:\\Repo6.0\\<TenantId>\\Instance\\<FormId>\\ plainly had
instance files on disk -- because instance_service.py only recognised the
5.5 filename shape (instance_label_parser.py's one regex) and silently
skipped every 6.0-shaped filename as unparseable.

Fix: get_instances_for_report() now reads report_lookup.get_instances_by_form_id()
(the same instance-log source "Check report status" already uses) instead
of os.listdir() + regex parsing. report_lookup._parse_instances() already
normalises 6.0's differently-named InstanceLog.xml attributes (ReturnId/
InstanceDoc/CreateDT) to the 5.5 shape (FormId/InstanceDocPath/DTC) at the
parse boundary, so instance_service.py needs no version branching of its
own -- it consumes the same normalised shape for both versions.

Bug 2 (found while verifying bug 1's fix against real D:\\Repo6.0 data):
trusting the log's InstanceDocPath unconditionally surfaced two further
real problems the filesystem-scan approach happened to avoid by accident --
(a) some logged InstanceDocPath values point to files that no longer exist
on disk (archived/cleaned up after the fact), and selecting one only failed
deep inside the actual comparison step with a generic error; (b) many rows
log an intermediate ".csv" data-extract as InstanceDocPath, not the real
".xml" instance document sitting right next to it on disk as
"<base>_Instance.xml" -- confirmed as the actual naming relationship in
real 6.0 data. Fixed by resolving + verifying the real file at discovery
time (_resolve_existing_doc_path), so a selectable instance is always a
real, loadable XBRL document.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services import instance_service


def _row(**overrides) -> dict:
    """A normalised instance-log row, the exact shape
    report_lookup.get_instances_by_form_id() returns for EITHER version
    (6.0 rows are already remapped to this shape by _normalize_v6_instance_row
    before instance_service ever sees them)."""
    base = {
        "Id": "1",
        "FormId": "4108",
        "ReportingDate": "30-Apr-2026",
        "Status": "11",
        "DTC": "04-Aug-2026 03:16:13 AM",
        "InstanceDocPath": "QCB_F026_Credit_Card_FX_Sellers_441_30-Apr-2026_04-08-26_03-16-13_Instance.xml",
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _fake_filesystem(monkeypatch):
    """build_instance_doc_path() depends on config._active_root() (the
    version-aware tenant-scoped root) -- not under test here, so it's pinned
    to a fixed, inspectable value. os.path.isfile() is replaced by a
    controllable in-memory set, since the real existence check is exactly
    what's under test -- each test populates `existing_files` with whichever
    filenames should "exist" for that scenario.
    """
    existing_files: set[str] = set()

    def _fake_build_path(form_id, filename):
        return f"ROOT/Instance/{form_id}/{filename}"

    def _fake_isfile(path):
        return path in {_fake_build_path("4108", f) for f in existing_files}

    monkeypatch.setattr(instance_service, "build_instance_doc_path", _fake_build_path)
    monkeypatch.setattr(instance_service.os.path, "isfile", _fake_isfile)
    return existing_files


class TestReadsFromInstanceLogNotFilesystem:
    def test_6_0_shaped_filename_is_never_parsed_and_still_resolves(self, monkeypatch, _fake_filesystem):
        """The exact filename shape that broke the old regex-based approach
        -- now it's just carried through verbatim, never parsed."""
        fname = "QCB_F026_Credit_Card_FX_Sellers_441_30-Apr-2026_04-08-26_03-16-13_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id", lambda fid: [_row(InstanceDocPath=fname)],
        )
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 1
        rec = result[0]
        assert rec["instance_path"] == fname
        assert rec["full_path"] == f"ROOT/Instance/4108/{fname}"

    def test_5_5_shaped_filename_still_resolves_unchanged(self, monkeypatch, _fake_filesystem):
        fname = "HDFC200522R00002M_30-09-24_12-43-45_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(InstanceDocPath=fname)],
        )
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 1
        assert result[0]["instance_path"] == fname

    def test_reporting_date_comes_from_log_not_filename(self, monkeypatch, _fake_filesystem):
        fname = "QCB_F026_Credit_Card_FX_Sellers_441_30-Apr-2026_04-08-26_03-16-13_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(ReportingDate="15-Jan-2099", InstanceDocPath=fname)],  # not in the filename
        )
        result = instance_service.get_instances_for_report("4108")
        assert result[0]["reporting_date"] == "15-Jan-2099"

    def test_dtc_comes_from_log_not_filename(self, monkeypatch, _fake_filesystem):
        fname = "QCB_F026_Credit_Card_FX_Sellers_441_30-Apr-2026_04-08-26_03-16-13_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(DTC="01-Jan-2099 11:59:59 PM", InstanceDocPath=fname)],
        )
        result = instance_service.get_instances_for_report("4108")
        assert result[0]["dtc"] == "01-Jan-2099 11:59:59 PM"

    def test_status_comes_from_log_never_blank(self, monkeypatch, _fake_filesystem):
        """The old filesystem-scan approach hardcoded status="" always
        (filenames don't carry status) -- this is the whole reason
        comparative analysis could never show it."""
        fname = "QCB_F026_Credit_Card_FX_Sellers_441_30-Apr-2026_04-08-26_03-16-13_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(Status="11", InstanceDocPath=fname)],  # 11 = Approval Pending
        )
        result = instance_service.get_instances_for_report("4108")
        assert result[0]["status"] == "Approval Pending"
        assert result[0]["status"] != ""

    def test_failed_status_maps_correctly(self, monkeypatch, _fake_filesystem):
        fname = "x_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(Status="8", InstanceDocPath=fname)],  # 8 = Failed
        )
        result = instance_service.get_instances_for_report("4108")
        assert result[0]["status"] == "Failed"

    def test_malformed_status_degrades_to_empty_not_a_crash(self, monkeypatch, _fake_filesystem):
        fname = "x_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(Status="not-a-number", InstanceDocPath=fname)],
        )
        result = instance_service.get_instances_for_report("4108")
        assert result[0]["status"] == ""

    def test_id_comes_from_log(self, monkeypatch, _fake_filesystem):
        fname = "x_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(Id="583", InstanceDocPath=fname)],
        )
        result = instance_service.get_instances_for_report("4108")
        assert result[0]["id"] == "583"


class TestMultipleInstancesSameForm:
    def test_multiple_instances_all_returned(self, monkeypatch, _fake_filesystem):
        _fake_filesystem.update({"run1_Instance.xml", "run2_Instance.xml", "run3_Instance.xml"})
        rows = [
            _row(Id="1", DTC="04-Aug-2026 03:16:13 AM", InstanceDocPath="run1_Instance.xml"),
            _row(Id="2", DTC="04-Aug-2026 03:21:04 AM", InstanceDocPath="run2_Instance.xml"),
            _row(Id="3", DTC="04-Aug-2026 03:30:36 AM", InstanceDocPath="run3_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 3

    def test_sorted_newest_dtc_first(self, monkeypatch, _fake_filesystem):
        _fake_filesystem.update({"oldest_Instance.xml", "newest_Instance.xml", "middle_Instance.xml"})
        rows = [
            _row(Id="1", DTC="04-Aug-2026 03:16:13 AM", InstanceDocPath="oldest_Instance.xml"),
            _row(Id="2", DTC="04-Aug-2026 03:30:36 AM", InstanceDocPath="newest_Instance.xml"),
            _row(Id="3", DTC="04-Aug-2026 03:21:04 AM", InstanceDocPath="middle_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert [r["instance_path"] for r in result] == [
            "newest_Instance.xml", "middle_Instance.xml", "oldest_Instance.xml",
        ]

    def test_different_reporting_dates_all_preserved(self, monkeypatch, _fake_filesystem):
        _fake_filesystem.update({"q1_Instance.xml", "q2_Instance.xml"})
        rows = [
            _row(Id="1", ReportingDate="30-Apr-2026", DTC="04-Aug-2026 03:16:13 AM",
                 InstanceDocPath="q1_Instance.xml"),
            _row(Id="2", ReportingDate="31-Mar-2026", DTC="04-Aug-2026 03:21:04 AM",
                 InstanceDocPath="q2_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        dates = {r["reporting_date"] for r in result}
        assert dates == {"30-Apr-2026", "31-Mar-2026"}

    def test_different_statuses_each_mapped_independently(self, monkeypatch, _fake_filesystem):
        _fake_filesystem.update({"pending_Instance.xml", "approved_Instance.xml", "failed_Instance.xml"})
        rows = [
            _row(Id="1", Status="11", InstanceDocPath="pending_Instance.xml"),
            _row(Id="2", Status="9", InstanceDocPath="approved_Instance.xml"),
            _row(Id="3", Status="8", InstanceDocPath="failed_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        by_file = {r["instance_path"]: r["status"] for r in result}
        assert by_file["pending_Instance.xml"] == "Approval Pending"
        assert by_file["approved_Instance.xml"] in ("Approved", "Submitted")
        assert by_file["failed_Instance.xml"] == "Failed"

    def test_same_report_generated_multiple_times_keeps_every_run(self, monkeypatch, _fake_filesystem):
        """Same FormId + same ReportingDate, regenerated 3 times -- all 3
        distinct runs must still be returned (comparative analysis needs
        at least 2 of them to pick from)."""
        names = [f"attempt{i}_Instance.xml" for i in range(1, 4)]
        _fake_filesystem.update(names)
        rows = [
            _row(Id=str(i), DTC=f"04-Aug-2026 0{i}:00:00 AM", InstanceDocPath=names[i - 1])
            for i in range(1, 4)
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 3


class TestMissingOrMalformedRows:
    def test_no_rows_returns_empty_list(self, monkeypatch, _fake_filesystem):
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: [])
        assert instance_service.get_instances_for_report("4108") == []

    def test_row_with_no_instance_doc_path_is_skipped(self, monkeypatch, _fake_filesystem):
        """A run that failed before producing a document -- nothing to
        compare against, must not surface as a phantom empty entry."""
        _fake_filesystem.add("real_Instance.xml")
        rows = [
            _row(Id="1", InstanceDocPath=""),
            _row(Id="2", InstanceDocPath="real_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 1
        assert result[0]["instance_path"] == "real_Instance.xml"

    def test_missing_optional_fields_degrade_gracefully(self, monkeypatch, _fake_filesystem):
        _fake_filesystem.add("bare_Instance.xml")
        rows = [{"InstanceDocPath": "bare_Instance.xml"}]  # no Id/Status/DTC/ReportingDate at all
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 1
        assert result[0]["status"] == ""
        assert result[0]["reporting_date"] == ""
        assert result[0]["dtc"] == ""
        assert result[0]["id"] == ""
        # label falls back to the filename when no date/dtc is available
        assert result[0]["label"] == "bare_Instance.xml"

    def test_logged_file_missing_from_disk_is_skipped_not_offered(self, monkeypatch, _fake_filesystem):
        """Bug 2a: a stale log entry (file archived/deleted after logging)
        must never reach the user as a selectable comparison option -- it
        used to fail later, deep inside the actual comparison step, with a
        generic "Unable to perform the comparison" error."""
        # Nothing added to _fake_filesystem -- this file "doesn't exist".
        rows = [_row(Id="1", InstanceDocPath="ghost_Instance.xml")]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert result == []

    def test_mix_of_real_and_stale_rows_keeps_only_the_real_one(self, monkeypatch, _fake_filesystem):
        _fake_filesystem.add("real_Instance.xml")
        rows = [
            _row(Id="1", InstanceDocPath="ghost_Instance.xml"),
            _row(Id="2", InstanceDocPath="real_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 1
        assert result[0]["instance_path"] == "real_Instance.xml"


class TestCsvToInstanceXmlDerivation:
    """Bug 2b, confirmed against real 6.0 data: some rows log an
    intermediate ".csv" data-extract as InstanceDocPath, while the real,
    comparable XBRL document sits right next to it on disk as
    "<base>_Instance.xml"."""

    def test_csv_logged_but_derived_xml_exists_resolves_to_the_xml(self, monkeypatch, _fake_filesystem):
        _fake_filesystem.add("RBIN095622820260430F013D_260817173111_Instance.xml")
        # Note: the literal .csv is deliberately NOT added to _fake_filesystem
        # as a comparable candidate -- it may exist on disk as a real file,
        # but it must never be the thing offered for comparison.
        rows = [_row(Id="1", InstanceDocPath="RBIN095622820260430F013D_260817173111.csv")]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert len(result) == 1
        assert result[0]["instance_path"] == "RBIN095622820260430F013D_260817173111_Instance.xml"

    def test_csv_logged_with_no_derived_xml_is_skipped(self, monkeypatch, _fake_filesystem):
        """Neither the .csv's literal name nor its derived .xml name is
        comparable/exists -- must not be offered."""
        rows = [_row(Id="1", InstanceDocPath="orphan_run.csv")]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert result == []

    def test_literal_csv_file_existing_is_never_itself_returned(self, monkeypatch, _fake_filesystem):
        """Even if the exact logged .csv filename happens to exist on disk
        as a file (it usually does -- it's a real intermediate artifact),
        it must never be the resolved instance_path/full_path -- only the
        derived .xml, and only if THAT exists."""
        fname = "RBIN095622820260430F013D_260817173111.csv"
        _fake_filesystem.add(fname)  # the .csv itself "exists"
        # derived .xml is deliberately absent
        rows = [_row(Id="1", InstanceDocPath=fname)]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)
        result = instance_service.get_instances_for_report("4108")
        assert result == []  # not returned with the .csv path either


class TestReturnContractUnchangedForCallers:
    """backend/agent/comparison.py reads these exact keys -- the refactor
    must not rename or drop any of them."""

    def test_every_expected_key_present(self, monkeypatch, _fake_filesystem):
        fname = "x_Instance.xml"
        _fake_filesystem.add(fname)
        monkeypatch.setattr(
            instance_service, "get_instances_by_form_id",
            lambda fid: [_row(InstanceDocPath=fname)],
        )
        result = instance_service.get_instances_for_report("4108")
        rec = result[0]
        for key in ("instance_path", "full_path", "reporting_date", "dtc", "label", "status", "id"):
            assert key in rec, f"missing key: {key}"


class TestComparativeAnalysisIntegration:
    """The actual reported bug: 'Perform comparative analysis' must no
    longer say 'No instance files found' when the instance log has valid,
    real, resolvable rows -- regardless of filename shape -- and must never
    offer a stale or non-XBRL row that would fail a step later."""

    def test_no_instance_files_found_message_is_gone_when_log_has_real_rows(self, monkeypatch, _fake_filesystem):
        import asyncio
        from backend.agent import comparison

        _fake_filesystem.update({"a_Instance.xml", "b_Instance.xml"})
        monkeypatch.setattr(comparison, "get_form_id_by_name", lambda name: "4108")
        rows = [
            _row(Id="1", DTC="04-Aug-2026 03:16:13 AM", InstanceDocPath="a_Instance.xml"),
            _row(Id="2", DTC="04-Aug-2026 03:21:04 AM", InstanceDocPath="b_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)

        result = asyncio.run(comparison._compare_with_name("QCB_F026_Credit_Card_FX_Sellers", None))
        assert result["result_type"] != "error"
        assert "No instance files found" not in (result.get("response_text") or "")

    def test_selection_flow_reaches_at_least_two_instances(self, monkeypatch, _fake_filesystem):
        import asyncio
        from backend.agent import comparison

        _fake_filesystem.update({"a_Instance.xml", "b_Instance.xml"})
        monkeypatch.setattr(comparison, "get_form_id_by_name", lambda name: "4108")
        rows = [
            _row(Id="1", DTC="04-Aug-2026 03:16:13 AM", InstanceDocPath="a_Instance.xml"),
            _row(Id="2", DTC="04-Aug-2026 03:21:04 AM", InstanceDocPath="b_Instance.xml"),
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)

        result = asyncio.run(comparison._compare_with_name("QCB_F026_Credit_Card_FX_Sellers", None))
        assert result["result_type"] == "instance_selection"
        assert len(result["instances_data"]) == 2

    def test_stale_rows_never_reach_the_selector(self, monkeypatch, _fake_filesystem):
        """A report with rows in the log but none of them resolvable on
        disk must fall back to the 'No instance files found' error -- not
        crash later at the comparison step."""
        import asyncio
        from backend.agent import comparison

        monkeypatch.setattr(comparison, "get_form_id_by_name", lambda name: "4108")
        rows = [
            _row(Id="1", InstanceDocPath="ghost1_Instance.xml"),
            _row(Id="2", InstanceDocPath="ghost2.csv"),  # no derived .xml either
        ]
        monkeypatch.setattr(instance_service, "get_instances_by_form_id", lambda fid: rows)

        result = asyncio.run(comparison._compare_with_name("QCB_F026_Credit_Card_FX_Sellers", None))
        assert result["result_type"] == "error"
        assert "No instance files found" in result["response_text"]
