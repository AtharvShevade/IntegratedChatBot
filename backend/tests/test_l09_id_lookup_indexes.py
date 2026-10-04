"""L-09: `period_name_by_id`, `return_name_by_id`, and `option_name_by_id`
(backend/db_qa/xml_store.py) each did an O(n) linear scan on every single
call. Now each builds a dict index once per XMLStore lifetime (same
caching convention as the existing `_user_index()`), reused for every
subsequent lookup.
"""
from __future__ import annotations

from backend.db_qa.xml_store import XMLStore


def _bare_store() -> XMLStore:
    """An XMLStore with an empty _cache dict and no file I/O -- methods
    under test only touch self._cache and the already-monkeypatched
    periods()/returns()/non_xbrl_returns()/options() accessors, never the
    real XML files."""
    store = XMLStore.__new__(XMLStore)
    store._cache = {}
    return store


class TestPeriodNameByIdIndex:
    def test_result_matches_original_linear_scan_behavior(self, monkeypatch):
        store = _bare_store()
        periods = [
            {"Period_Id": "1", "PeriodName": "Quarterly"},
            {"PeriodId": "2", "PeriodName": "Monthly"},  # alternate key name
            {"Id": "3", "PeriodName": "Yearly"},          # another alternate
        ]
        monkeypatch.setattr(store, "periods", lambda: periods)

        assert store.period_name_by_id("1") == "Quarterly"
        assert store.period_name_by_id("2") == "Monthly"
        assert store.period_name_by_id("3") == "Yearly"

    def test_missing_id_returns_the_id_unchanged(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "periods", lambda: [{"Period_Id": "1", "PeriodName": "Quarterly"}])
        assert store.period_name_by_id("999") == "999"

    def test_index_dict_is_built_once_and_reused(self, monkeypatch):
        """The cheap accessor (periods()) is called on every lookup so that
        _load()'s mtime-based eviction (_INDEX_DEPS) always gets a chance to
        fire -- see _period_name_index()'s docstring. What must only happen
        ONCE is the actual O(n) dict-building scan, which this test observes
        via object identity of the returned dict across calls."""
        store = _bare_store()
        monkeypatch.setattr(store, "periods", lambda: [{"Period_Id": "1", "PeriodName": "Quarterly"}])

        store.period_name_by_id("1")
        first_index = store._cache["__period_name_index__"]
        store.period_name_by_id("1")
        store.period_name_by_id("999")
        second_index = store._cache["__period_name_index__"]

        assert first_index is second_index, "the index dict must be reused (same object), not rebuilt per lookup"

    def test_duplicate_period_id_keeps_first_match_like_the_original_scan(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "periods", lambda: [
            {"Period_Id": "1", "PeriodName": "Quarterly"},
            {"Period_Id": "1", "PeriodName": "Duplicate Later Row"},
        ])
        assert store.period_name_by_id("1") == "Quarterly"


class TestReturnNameByIdIndex:
    def test_matches_by_internal_id(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "returns", lambda: [{"Id": "2029", "ReturnId": "R018", "Name": "CIMS_RAQ"}])
        monkeypatch.setattr(store, "non_xbrl_returns", lambda: [])
        assert store.return_name_by_id("2029") == "CIMS_RAQ"

    def test_matches_by_return_id_code(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "returns", lambda: [{"Id": "2029", "ReturnId": "R018", "Name": "CIMS_RAQ"}])
        monkeypatch.setattr(store, "non_xbrl_returns", lambda: [])
        assert store.return_name_by_id("R018") == "CIMS_RAQ"

    def test_checks_non_xbrl_returns_too(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "returns", lambda: [])
        monkeypatch.setattr(store, "non_xbrl_returns", lambda: [{"Id": "5000", "Name": "NonXBRL Return"}])
        assert store.return_name_by_id("5000") == "NonXBRL Return"

    def test_returns_checked_before_non_xbrl_returns_on_a_collision(self, monkeypatch):
        """Preserves the original scan order's priority: returns() was
        always checked first."""
        store = _bare_store()
        monkeypatch.setattr(store, "returns", lambda: [{"Id": "1", "Name": "FromReturns"}])
        monkeypatch.setattr(store, "non_xbrl_returns", lambda: [{"Id": "1", "Name": "FromNonXbrl"}])
        assert store.return_name_by_id("1") == "FromReturns"

    def test_missing_id_returns_the_id_unchanged(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "returns", lambda: [])
        monkeypatch.setattr(store, "non_xbrl_returns", lambda: [])
        assert store.return_name_by_id("unknown") == "unknown"

    def test_index_dict_is_built_once_and_reused(self, monkeypatch):
        """See TestPeriodNameByIdIndex.test_index_dict_is_built_once_and_reused
        -- returns()/non_xbrl_returns() may be called on every lookup (cheap,
        needed for eviction), but the dict-building scan must only run once."""
        store = _bare_store()
        monkeypatch.setattr(store, "returns", lambda: [{"Id": "1", "ReturnId": "R1", "Name": "X"}])
        monkeypatch.setattr(store, "non_xbrl_returns", lambda: [])

        store.return_name_by_id("1")
        first_index = store._cache["__return_name_index__"]
        store.return_name_by_id("R1")
        store.return_name_by_id("unknown")
        second_index = store._cache["__return_name_index__"]

        assert first_index is second_index, "the index dict must be reused (same object), not rebuilt per lookup"


class TestIndexInvalidatesOnFileReload:
    """Real end-to-end test (actual XMLStore, actual file on disk, actual
    mtime-based reload) -- not mockable via monkeypatching periods() itself,
    since that would bypass the exact _load()/_INDEX_DEPS eviction path this
    is meant to prove is wired correctly for the 3 NEW cached indexes, the
    same way it already was for _user_index()."""

    def _write_period_xml(self, path, period_id: str, name: str) -> None:
        path.write_text(
            f'<?xml version="1.0"?><Periods><Row Period_Id="{period_id}" '
            f'PeriodName="{name}" /></Periods>',
            encoding="utf-8",
        )

    def test_changing_the_file_on_disk_invalidates_the_cached_index(self, tmp_path):
        import time
        from backend.db_qa.xml_store import XMLStore

        xml_path = tmp_path / "XML_Period.xml"
        self._write_period_xml(xml_path, "1", "Quarterly")

        store = XMLStore(str(tmp_path))
        assert store.period_name_by_id("1") == "Quarterly"

        # Force a detectable mtime change, then rewrite the file with a
        # different name for the SAME id.
        time.sleep(0.05)
        self._write_period_xml(xml_path, "1", "Monthly")
        os_utime_future = time.time() + 5
        import os
        os.utime(str(xml_path), (os_utime_future, os_utime_future))

        assert store.period_name_by_id("1") == "Monthly", (
            "the cached index must be evicted and rebuilt once the source "
            "file's mtime changes -- a stale 'Quarterly' here means "
            "__period_name_index__ was never registered in _INDEX_DEPS"
        )


class TestOptionNameByIdIndex:
    def test_result_matches_original_linear_scan_behavior(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "options", lambda: [{"OptionId": "10", "OptionName": "Users"}])
        assert store.option_name_by_id("10") == "Users"

    def test_missing_id_returns_the_id_unchanged(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "options", lambda: [{"OptionId": "10", "OptionName": "Users"}])
        assert store.option_name_by_id("999") == "999"

    def test_index_dict_is_built_once_and_reused(self, monkeypatch):
        """See TestPeriodNameByIdIndex.test_index_dict_is_built_once_and_reused
        -- options() may be called on every lookup (cheap, needed for
        eviction), but the dict-building scan must only run once."""
        store = _bare_store()
        monkeypatch.setattr(store, "options", lambda: [{"OptionId": "10", "OptionName": "Users"}])

        store.option_name_by_id("10")
        first_index = store._cache["__option_name_index__"]
        store.option_name_by_id("10")
        store.option_name_by_id("999")
        second_index = store._cache["__option_name_index__"]

        assert first_index is second_index, "the index dict must be reused (same object), not rebuilt per lookup"

    def test_duplicate_option_id_keeps_first_match_like_the_original_scan(self, monkeypatch):
        """The original implementation was `for o in options(): if match:
        return` -- first match wins. The index-building loop must preserve
        that, not let a later duplicate OptionId silently overwrite it."""
        store = _bare_store()
        monkeypatch.setattr(store, "options", lambda: [
            {"OptionId": "10", "OptionName": "Report Log"},
            {"OptionId": "10", "OptionName": "Duplicate Later Row"},
        ])
        assert store.option_name_by_id("10") == "Report Log"

    def test_enrich_role_access_still_works(self, monkeypatch):
        store = _bare_store()
        monkeypatch.setattr(store, "options", lambda: [{"OptionId": "10", "OptionName": "Users"}])
        enriched = store.enrich_role_access({"OptionId": "10", "CanView": "True"})
        assert enriched["OptionName"] == "Users"

    def test_changing_the_file_on_disk_invalidates_the_cached_index(self, tmp_path):
        """Real end-to-end test mirroring TestIndexInvalidatesOnFileReload for
        periods -- proves __option_name_index__'s eviction via _INDEX_DEPS
        actually fires, not just that the index is built once."""
        import os
        import time
        from backend.db_qa.xml_store import XMLStore

        xml_path = tmp_path / "XML_Option.xml"
        xml_path.write_text(
            '<?xml version="1.0"?><Options><Row OptionId="10" OptionName="Users" /></Options>',
            encoding="utf-8",
        )

        store = XMLStore(str(tmp_path))
        assert store.option_name_by_id("10") == "Users"

        time.sleep(0.05)
        xml_path.write_text(
            '<?xml version="1.0"?><Options><Row OptionId="10" OptionName="User Management" /></Options>',
            encoding="utf-8",
        )
        future = time.time() + 5
        os.utime(str(xml_path), (future, future))

        assert store.option_name_by_id("10") == "User Management", (
            "the cached index must be evicted and rebuilt once the source "
            "file's mtime changes -- a stale 'Users' here means "
            "__option_name_index__ was never registered in _INDEX_DEPS"
        )
