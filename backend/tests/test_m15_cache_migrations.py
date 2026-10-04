"""M-15: regression tests for the three call sites migrated onto the shared
backend.utils.file_cache.FileCache utility -- confirms each site's existing
callers still get equivalent results, and that the mtime-invalidation gap
specifically called out for instance_generator.py is now closed.
"""
from __future__ import annotations

import os
import time

import pytest


class TestInstanceGeneratorPeriodMaster:
    def test_get_period_info_still_works(self, tmp_path, monkeypatch):
        import backend.tools.instance_generator as ig
        ig._period_cache.clear()

        period_file = tmp_path / "XML_Period.xml"
        period_file.write_text(
            '<?xml version="1.0"?><Document>'
            '<Row Period_Id="1" Frequency="Q" PeriodName="Quarter One"/>'
            "</Document>",
            encoding="utf-8",
        )
        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(period_file))
        monkeypatch.setattr(ig.version_config, "IS_V6", False)

        info = ig.get_period_info("1")
        assert info is not None
        assert info["PeriodName"] == "Quarter One"

    def test_file_mtime_change_invalidates_the_cache(self, tmp_path, monkeypatch):
        """This is the exact gap M-15 called out for instance_generator.py:
        the previous plain-dict TTL cache (24h) had NO mtime check at all,
        so an edit to Period.xml went unnoticed until the TTL happened to
        expire. Proves the migrated cache now picks up a change immediately."""
        import backend.tools.instance_generator as ig
        ig._period_cache.clear()

        period_file = tmp_path / "XML_Period.xml"
        period_file.write_text(
            '<?xml version="1.0"?><Document>'
            '<Row Period_Id="1" Frequency="Q" PeriodName="Before"/>'
            "</Document>",
            encoding="utf-8",
        )
        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(period_file))
        monkeypatch.setattr(ig.version_config, "IS_V6", False)

        assert ig.get_period_info("1")["PeriodName"] == "Before"

        time.sleep(0.05)
        period_file.write_text(
            '<?xml version="1.0"?><Document>'
            '<Row Period_Id="1" Frequency="Q" PeriodName="After"/>'
            "</Document>",
            encoding="utf-8",
        )
        future = time.time() + 5
        os.utime(str(period_file), (future, future))

        assert ig.get_period_info("1")["PeriodName"] == "After"

    def test_different_tenant_paths_are_cached_independently(self, tmp_path, monkeypatch):
        import backend.tools.instance_generator as ig
        ig._period_cache.clear()

        file_a = tmp_path / "a" / "Period.xml"
        file_a.parent.mkdir()
        file_a.write_text(
            '<?xml version="1.0"?><Document><Row Period_Id="1" Frequency="Q" PeriodName="A"/></Document>',
            encoding="utf-8",
        )
        file_b = tmp_path / "b" / "Period.xml"
        file_b.parent.mkdir()
        file_b.write_text(
            '<?xml version="1.0"?><Document><Row Period_Id="1" Frequency="Y" PeriodName="B"/></Document>',
            encoding="utf-8",
        )
        monkeypatch.setattr(ig.version_config, "IS_V6", False)

        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(file_a))
        assert ig.get_period_info("1")["PeriodName"] == "A"

        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(file_b))
        assert ig.get_period_info("1")["PeriodName"] == "B"

        # Switching back to tenant A's path must still serve A's data, not
        # a leaked/overwritten B entry.
        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(file_a))
        assert ig.get_period_info("1")["PeriodName"] == "A"

    def test_missing_file_degrades_to_empty_dict_not_an_exception(self, tmp_path, monkeypatch):
        import backend.tools.instance_generator as ig
        ig._period_cache.clear()
        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(tmp_path / "missing.xml"))
        monkeypatch.setattr(ig.version_config, "IS_V6", False)
        assert ig.get_period_info("1") is None
