"""M-15: report_lookup.py's _parse_returns()/_parse_instances()/
_normalised_returns() migrated from a path-keyed dict-of-`_TTLCache`
(unbounded, unlocked) onto the shared backend.utils.file_cache.FileCache.
"""
from __future__ import annotations

import os
import time

import pytest


@pytest.fixture(autouse=True)
def _reset_caches():
    import backend.tools.report_lookup as rl
    rl._returns_cache.clear()
    rl._instances_cache.clear()
    rl._norm_cache.clear()
    yield
    rl._returns_cache.clear()
    rl._instances_cache.clear()
    rl._norm_cache.clear()


_RETURNS_XML = (
    '<?xml version="1.0"?><Returns>'
    '<Return Name="CIMS_RAQ" ReturnId="R1" Id="1"/>'
    "</Returns>"
)


class TestParseReturnsCache:
    def test_parses_and_caches(self, tmp_path, monkeypatch):
        import backend.tools.report_lookup as rl
        p = tmp_path / "Returns.xml"
        p.write_text(_RETURNS_XML, encoding="utf-8")
        monkeypatch.setattr(rl.config, "returns_xml_path", lambda: str(p))
        monkeypatch.setattr(rl.version_config, "IS_V6", False)

        result = rl._parse_returns()
        assert len(result) == 1
        assert result[0]["Name"] == "CIMS_RAQ"

    def test_cache_hit_does_not_reparse(self, tmp_path, monkeypatch):
        import backend.tools.report_lookup as rl
        p = tmp_path / "Returns.xml"
        p.write_text(_RETURNS_XML, encoding="utf-8")
        monkeypatch.setattr(rl.config, "returns_xml_path", lambda: str(p))
        monkeypatch.setattr(rl.version_config, "IS_V6", False)

        calls = {"n": 0}
        real_load_xml_tree = rl.load_xml_tree

        def _counting_load(*a, **k):
            calls["n"] += 1
            return real_load_xml_tree(*a, **k)

        monkeypatch.setattr(rl, "load_xml_tree", _counting_load)
        rl._parse_returns()
        rl._parse_returns()
        assert calls["n"] == 1

    def test_mtime_change_invalidates(self, tmp_path, monkeypatch):
        import backend.tools.report_lookup as rl
        p = tmp_path / "Returns.xml"
        p.write_text(_RETURNS_XML, encoding="utf-8")
        monkeypatch.setattr(rl.config, "returns_xml_path", lambda: str(p))
        monkeypatch.setattr(rl.version_config, "IS_V6", False)

        assert rl._parse_returns()[0]["Name"] == "CIMS_RAQ"

        time.sleep(0.05)
        p.write_text(
            '<?xml version="1.0"?><Returns><Return Name="NEW_RETURN" ReturnId="R2" Id="2"/></Returns>',
            encoding="utf-8",
        )
        future = time.time() + 5
        os.utime(str(p), (future, future))

        assert rl._parse_returns()[0]["Name"] == "NEW_RETURN"


class TestParseInstancesCacheEmptyNotPersisted:
    def test_empty_result_is_not_cached(self, tmp_path, monkeypatch):
        """Mirrors the original cache_empty=False semantic: a transient
        0-row parse must not evict/replace a previously-cached good result,
        and must not itself be served from cache on the next call either."""
        import backend.tools.report_lookup as rl

        p = tmp_path / "InstanceLog.xml"
        p.write_text('<?xml version="1.0"?><Document></Document>', encoding="utf-8")
        monkeypatch.setattr(rl.config, "instance_log_xml_path", lambda: str(p))
        monkeypatch.setattr(rl.version_config, "IS_V6", False)

        result1 = rl._parse_instances()
        assert result1 == ()
        # Not cached: loaded_at must still be None for this path.
        assert rl._instances_cache.loaded_at(str(p)) is None

    def test_nonempty_result_is_cached(self, tmp_path, monkeypatch):
        import backend.tools.report_lookup as rl

        p = tmp_path / "InstanceLog.xml"
        p.write_text(
            '<?xml version="1.0"?><Document><Row FormId="1" DTC="01-Jan-2026"/></Document>',
            encoding="utf-8",
        )
        monkeypatch.setattr(rl.config, "instance_log_xml_path", lambda: str(p))
        monkeypatch.setattr(rl.version_config, "IS_V6", False)

        result = rl._parse_instances()
        assert len(result) == 1
        assert rl._instances_cache.loaded_at(str(p)) is not None


class TestNormalisedReturnsDerivedCache:
    def test_normalised_returns_reflects_parsed_returns(self, tmp_path, monkeypatch):
        import backend.tools.report_lookup as rl
        p = tmp_path / "Returns.xml"
        p.write_text(_RETURNS_XML, encoding="utf-8")
        monkeypatch.setattr(rl.config, "returns_xml_path", lambda: str(p))
        monkeypatch.setattr(rl.version_config, "IS_V6", False)

        norm = rl._normalised_returns()
        assert len(norm) == 1
        assert norm[0][0] == "cims raq"

    def test_stale_norm_cache_is_invalidated_when_returns_cache_is_fresher(self, tmp_path, monkeypatch):
        """Reproduces the exact scenario the original loaded_at comparison
        guarded against: _parse_returns() refreshed independently/more
        recently than _normalised_returns()'s own cache entry."""
        import backend.tools.report_lookup as rl
        p = tmp_path / "Returns.xml"
        p.write_text(_RETURNS_XML, encoding="utf-8")
        monkeypatch.setattr(rl.config, "returns_xml_path", lambda: str(p))
        monkeypatch.setattr(rl.version_config, "IS_V6", False)

        rl._normalised_returns()  # populates _norm_cache
        # Force _returns_cache to look "fresher" than _norm_cache without an
        # actual file change, exactly like a direct, independent
        # _parse_returns() refresh would.
        rl._returns_cache.invalidate(str(p))
        rl._returns_cache.set(str(p), rl._parse_returns())
        time.sleep(0.01)
        rl._returns_cache._store[str(p)] = (
            rl._returns_cache._store[str(p)][0],
            rl._returns_cache._store[str(p)][1],
            rl._returns_cache.loaded_at(str(p)) + 10,  # pretend it's newer
        )

        assert rl._norm_cache.loaded_at(str(p)) < rl._returns_cache.loaded_at(str(p))
        norm = rl._normalised_returns()  # must reload, not serve the stale entry
        assert len(norm) == 1


class TestBoundedSize:
    def test_returns_cache_is_bounded(self):
        import backend.tools.report_lookup as rl
        assert rl._returns_cache._max_size == 64
        assert rl._instances_cache._max_size == 64
        assert rl._norm_cache._max_size == 64
