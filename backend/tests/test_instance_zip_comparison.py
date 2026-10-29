"""Regression tests: 5.5 logs "<stem>_Instance.zip" as InstanceDocPath, but the
zip holds "<stem>_Instance.xml" (also on disk beside it). The comparison picker
offered the zip and load_xbrl_facts() then failed with "not well-formed".

Fix 1: the picker swaps a .zip for its sibling .xml.
Fix 2: load_xbrl_facts() reads the inner instance out of a zip when no sibling
exists.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services import instance_service
from backend.tools import xbrl_comparator

_INSTANCE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:bom="http://example.com/bom">'
    '<context id="c1"><entity><identifier scheme="x">A</identifier></entity>'
    '<period><instant>2026-09-30</instant></period></context>'
    '<unit id="u1"><measure>iso4217:INR</measure></unit>'
    '<bom:PE000001 contextRef="c1" unitRef="u1" decimals="0">100</bom:PE000001>'
    '</xbrl>'
)


class TestPickerResolvesZip:
    @pytest.fixture(autouse=True)
    def _fs(self, monkeypatch):
        self.existing: set[str] = set()
        monkeypatch.setattr(
            instance_service, "build_instance_doc_path", lambda fid, name: f"/repo/{fid}/{name}"
        )
        monkeypatch.setattr(
            instance_service.os.path, "isfile",
            lambda p: p.rsplit("/", 1)[-1] in self.existing,
        )

    def test_zip_resolves_to_sibling_xml(self):
        self.existing = {"RUN_Instance.zip", "RUN_Instance.xml"}
        name, path = instance_service._resolve_existing_doc_path("1038", "RUN_Instance.zip")
        assert name == "RUN_Instance.xml"
        assert path == "/repo/1038/RUN_Instance.xml"

    def test_zip_without_sibling_is_kept(self):
        self.existing = {"RUN_Instance.zip"}
        name, path = instance_service._resolve_existing_doc_path("1038", "RUN_Instance.zip")
        assert name == "RUN_Instance.zip"

    def test_missing_zip_is_skipped(self):
        assert instance_service._resolve_existing_doc_path("1038", "RUN_Instance.zip") is None


class TestLoaderReadsZip:
    def _zip(self, tmp_path, entries: dict[str, str]) -> str:
        p = tmp_path / "RUN_Instance.zip"
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
            for n, data in entries.items():
                zf.writestr(n, data)
        return str(p)

    def test_zip_loads_inner_instance(self, tmp_path, monkeypatch):
        monkeypatch.setattr(xbrl_comparator, "_load_via_arelle", lambda p: [])
        facts = xbrl_comparator._load_xbrl_facts_uncached(
            self._zip(tmp_path, {"RUN_Instance.xml": _INSTANCE_XML})
        )
        assert [f["value_num"] for f in facts] == [100.0]

    def test_zip_without_instance_raises(self, tmp_path):
        with pytest.raises(ValueError):
            xbrl_comparator._load_xbrl_facts_uncached(
                self._zip(tmp_path, {"readme.txt": "x"})
            )

    def test_pick_prefers_xbrl_then_instance_suffix(self):
        assert xbrl_comparator._pick_zip_instance(["a.xml", "b_Instance.xml"]) == "b_Instance.xml"
        assert xbrl_comparator._pick_zip_instance(["a.xml", "b.xbrl"]) == "b.xbrl"
        assert xbrl_comparator._pick_zip_instance(["a.txt"]) is None
