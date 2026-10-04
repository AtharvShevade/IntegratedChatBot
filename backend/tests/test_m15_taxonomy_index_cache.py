"""M-15: taxonomy_index.py's _SCHEMA_LOCATION_CACHE / _INDEX_CACHE migrated
from raw, unbounded dicts onto the shared backend.utils.file_cache.FileCache
-- both were already thread-safe/signature-keyed in their own way; the only
gap being closed is unbounded growth, while preserving find_roots_for_schema's
existing "scan outside the lock" behavior and get_index_for_paths's stronger
"never construct the same index twice concurrently" guarantee.
"""
from __future__ import annotations

import threading

import pytest


@pytest.fixture(autouse=True)
def _reset_caches():
    import backend.tools.taxonomy_index as ti
    ti._SCHEMA_LOCATION_CACHE.clear()
    ti._INDEX_CACHE.clear()
    yield
    ti._SCHEMA_LOCATION_CACHE.clear()
    ti._INDEX_CACHE.clear()


class TestFindRootsForSchemaCache:
    def test_empty_schema_href_returns_empty_without_caching(self, monkeypatch):
        import backend.tools.taxonomy_index as ti
        monkeypatch.setattr(ti.config, "_active_root", lambda: "/fake/root")
        assert ti.find_roots_for_schema("") == ()
        assert len(ti._SCHEMA_LOCATION_CACHE) == 0

    def test_result_is_cached_by_root_and_name(self, tmp_path, monkeypatch):
        import backend.tools.taxonomy_index as ti

        root = tmp_path / "root"
        tax_dir = root / "DataBase" / "4038" / "Taxonomy"
        tax_dir.mkdir(parents=True)
        (tax_dir / "mpd03.xsd").write_text("<schema/>")

        monkeypatch.setattr(ti.config, "_active_root", lambda: str(root))

        calls = {"n": 0}
        real_walk_dirs = ti._all_taxonomy_dirs

        def _counting(active_root):
            calls["n"] += 1
            return real_walk_dirs(active_root)

        monkeypatch.setattr(ti, "_all_taxonomy_dirs", _counting)

        result1 = ti.find_roots_for_schema("mpd03.xsd")
        result2 = ti.find_roots_for_schema("mpd03.xsd")
        assert result1 == result2
        assert len(result1) == 1
        assert calls["n"] == 1  # second call was a cache hit, no rescan

    def test_cache_is_bounded(self):
        import backend.tools.taxonomy_index as ti
        assert ti._SCHEMA_LOCATION_CACHE._max_size == 128


class TestGetIndexForPathsCache:
    def test_none_for_no_valid_roots(self, tmp_path):
        import backend.tools.taxonomy_index as ti
        assert ti.get_index_for_paths((str(tmp_path / "does-not-exist"),)) is None

    def test_result_is_cached_by_content_signature(self, tmp_path):
        import backend.tools.taxonomy_index as ti

        tax_dir = tmp_path / "Taxonomy"
        tax_dir.mkdir()
        (tax_dir / "schema.xsd").write_text(
            '<?xml version="1.0"?><schema xmlns="http://www.w3.org/2001/XMLSchema"/>'
        )

        index1 = ti.get_index_for_paths((str(tax_dir),))
        index2 = ti.get_index_for_paths((str(tax_dir),))
        assert index1 is index2  # same object -- not rebuilt

    def test_cache_is_bounded(self):
        import backend.tools.taxonomy_index as ti
        assert ti._INDEX_CACHE._max_size == 32

    def test_concurrent_calls_never_construct_duplicate_indexes(self, tmp_path):
        """The stronger guarantee get_index_for_paths already had (hold the
        lock across check-AND-construct, not just the dict access) must
        survive the migration to FileCache."""
        import backend.tools.taxonomy_index as ti

        tax_dir = tmp_path / "Taxonomy"
        tax_dir.mkdir()
        (tax_dir / "schema.xsd").write_text(
            '<?xml version="1.0"?><schema xmlns="http://www.w3.org/2001/XMLSchema"/>'
        )

        construct_count = {"n": 0}
        real_init = ti.TaxonomyIndex.__init__

        def _counting_init(self, roots):
            construct_count["n"] += 1
            real_init(self, roots)

        import unittest.mock
        with unittest.mock.patch.object(ti.TaxonomyIndex, "__init__", _counting_init):
            results = []

            def _worker():
                results.append(ti.get_index_for_paths((str(tax_dir),)))

            threads = [threading.Thread(target=_worker) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert construct_count["n"] == 1
        assert all(r is results[0] for r in results)
