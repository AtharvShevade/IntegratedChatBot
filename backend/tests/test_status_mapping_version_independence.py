"""Regression tests: return/submission status-code interpretation must be
IDENTICAL for 5.5 and 6.0.

Background: 6.0's InstanceLog used to be populated by a separate/temporary
XBRLGeneration service with its own numeric status scheme (60/25/45/55/10/
20/30/40/50/0, sourced from .NET CreateInstanceModel.GetStatusAsync) —
observed values like 70 didn't even match that switch's own cases. That
service is no longer the source of truth: 6.0's InstanceLog.Status now uses
the SAME codes as 5.5's XML_InstanceLog.xml, so backend.tools.report_lookup
and backend.db_qa.xml_store must use ONE status vocabulary for both
versions, not a per-version table keyed off version_config.IS_V6.

These tests import the two status tables directly and assert they resolve
codes without ever branching on IS_V6 — a future re-introduction of a
"_STATUS_LABELS_6_0"/"_SUBMISSION_STATUS_LABELS_6_0" style split would fail
test_is_v6_does_not_change_status_tables below regardless of which
attribute name it used, since that test flips IS_V6 and re-imports fresh
module state and compares.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.tools import report_lookup
from backend.db_qa import xml_store


# ── report_lookup: the 5.5-sourced mapping is THE mapping, for both versions ──

class TestReportLookupStatusMapping:
    def test_known_5_5_codes_resolve(self):
        expected = {
            0: "Not Started",
            3: "Failed",
            4: "In Progress",
            5: "Failed",
            6: "In Progress",
            8: "Failed",
            9: "Approved",
            10: "Failed",
            11: "Success",
            12: "Rejected",
            13: "Failed",
        }
        for code, label in expected.items():
            assert report_lookup.map_status(code) == label

    def test_old_xbrlgeneration_service_codes_are_unknown_not_mislabeled(self):
        """60/25/45/55/70/etc. were the temporary/incorrect service's own
        scheme — they must NOT resolve to any label (no silent, wrong
        "Success"/"Failed" guess); "Unknown" is the correct, honest answer
        now that this service is not the source of truth."""
        for stale_code in (60, 25, 45, 55, 70, 20, 30, 40, 50):
            assert report_lookup.map_status(stale_code) == "Unknown"

    def test_failed_and_success_sets_match_5_5(self):
        assert report_lookup._FAILED_STATUSES == frozenset({3, 5, 8, 10, 13})
        assert report_lookup._SUCCESS_STATUSES == frozenset({9, 11})

    def test_no_separate_6_0_status_table_exists(self):
        """Locks in "do not create a separate status mapping for 6.0" —
        fails loudly if a _STATUS_LABELS_6_0-style table is reintroduced."""
        assert not hasattr(report_lookup, "_STATUS_LABELS_6_0")
        assert not hasattr(report_lookup, "_FAILED_STATUSES_6_0")
        assert not hasattr(report_lookup, "_SUCCESS_STATUSES_6_0")


# ── xml_store: db_qa's broader SUBMISSION_STATUS_LABELS vocabulary ──────────

class TestXmlStoreSubmissionStatusLabels:
    def test_known_5_5_codes_resolve(self):
        expected = {
            "0": "New / Pending",
            "1": "In Progress",
            "2": "Submitted",
            "3": "Validated",
            "4": "Rejected",
            "9": "Approved",
            "11": "Audited",
        }
        for code, label in expected.items():
            assert xml_store.SUBMISSION_STATUS_LABELS.get(code) == label

    def test_old_xbrlgeneration_service_codes_are_unmapped(self):
        for stale_code in ("60", "25", "45", "55", "70", "20", "30", "40", "50"):
            assert stale_code not in xml_store.SUBMISSION_STATUS_LABELS

    def test_no_separate_6_0_status_table_exists(self):
        assert not hasattr(xml_store, "_SUBMISSION_STATUS_LABELS_6_0")


# ── Version independence: flipping IS_V6 must not change either table ───────

class TestStatusMappingIsVersionIndependent:
    """Reload both modules under IS_V6=True and IS_V6=False and confirm the
    resolved tables are byte-for-byte identical either way — the actual
    guarantee the bug report asked for ("same status-code-to-status-name
    mapping as 5.5", "make the status lookup version-independent")."""

    def teardown_method(self, _method):
        # Always leave module state as pytest found it (IS_V6=False by
        # default in this suite) so other test files aren't affected.
        import backend.version_config as version_config
        importlib.reload(version_config)
        importlib.reload(report_lookup)
        importlib.reload(xml_store)

    def test_is_v6_does_not_change_status_tables(self, monkeypatch):
        import backend.version_config as version_config

        monkeypatch.setattr(version_config, "IS_V6", False)
        importlib.reload(report_lookup)
        importlib.reload(xml_store)
        labels_5_5 = dict(report_lookup._STATUS_LABELS)
        failed_5_5 = frozenset(report_lookup._FAILED_STATUSES)
        success_5_5 = frozenset(report_lookup._SUCCESS_STATUSES)
        submission_labels_5_5 = dict(xml_store.SUBMISSION_STATUS_LABELS)

        monkeypatch.setattr(version_config, "IS_V6", True)
        importlib.reload(report_lookup)
        importlib.reload(xml_store)
        labels_6_0 = dict(report_lookup._STATUS_LABELS)
        failed_6_0 = frozenset(report_lookup._FAILED_STATUSES)
        success_6_0 = frozenset(report_lookup._SUCCESS_STATUSES)
        submission_labels_6_0 = dict(xml_store.SUBMISSION_STATUS_LABELS)

        assert labels_6_0 == labels_5_5
        assert failed_6_0 == failed_5_5
        assert success_6_0 == success_5_5
        assert submission_labels_6_0 == submission_labels_5_5
