"""M-08: files loaded via ``pickle.load`` (SQL agent retrieval metadata, the
DB Q&A intent exemplar index) are now verified against a recorded SHA-256
checksum before they are ever unpickled -- ``pickle.load()`` can execute
arbitrary code embedded in the file, so anyone able to write to one of these
artifact directories previously got code execution the moment this process
next loaded it.

``backend/sql_agent/sqlcore/integrity.py``'s ``safe_pickle_load()`` is the single
shared implementation used by all 4 real call sites (retriever.py,
lexical_search.py, description_fetcher.py, and
backend/db_qa/intents/embedding_index.py). These tests exercise it directly
against temporary files, so they never touch or depend on this machine's
real embeddings/index artifacts.
"""
from __future__ import annotations

import json
import pickle

import pytest

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from sqlcore.integrity import (
    IntegrityError,
    checksum_from_build_stamp,
    safe_pickle_load,
    sha256_of_file,
    verify_checksum,
)


def _write_pickle(path, obj):
    with open(path, "wb") as f:
        pickle.dump(obj, f)


def _write_stamp(path, checksums: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"checksums": checksums}, f)


class TestNormalLoading:
    def test_file_with_no_stamp_loads_normally(self, tmp_path):
        """Preserves today's behavior for a deployment with no
        build_stamp.json at all (e.g. this repo's actual 5.5 embeddings
        set) -- nothing to verify against, so it loads exactly as a bare
        pickle.load() always did."""
        pkl_path = tmp_path / "meta.pkl"
        _write_pickle(pkl_path, {"table": "x", "rows": [1, 2, 3]})
        result = safe_pickle_load(str(pkl_path))
        assert result == {"table": "x", "rows": [1, 2, 3]}

    def test_file_matching_its_recorded_checksum_loads_normally(self, tmp_path):
        pkl_path = tmp_path / "meta.pkl"
        _write_pickle(pkl_path, {"ok": True})
        stamp_path = tmp_path / "build_stamp.json"
        _write_stamp(stamp_path, {"meta.pkl": sha256_of_file(str(pkl_path))})
        result = safe_pickle_load(str(pkl_path), stamp_path=str(stamp_path))
        assert result == {"ok": True}

    def test_file_not_listed_in_an_existing_stamp_loads_normally(self, tmp_path):
        """A stamp exists but simply doesn't mention this particular file --
        treated the same as "nothing to verify against", not an error."""
        pkl_path = tmp_path / "unlisted.pkl"
        _write_pickle(pkl_path, "data")
        stamp_path = tmp_path / "build_stamp.json"
        _write_stamp(stamp_path, {"some_other_file.pkl": "deadbeef" * 8})
        result = safe_pickle_load(str(pkl_path), stamp_path=str(stamp_path))
        assert result == "data"


class TestMissingFiles:
    def test_missing_pickle_file_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "does_not_exist.pkl"
        with pytest.raises(FileNotFoundError):
            safe_pickle_load(str(missing))

    def test_missing_stamp_file_is_handled_safely_not_raised(self, tmp_path):
        pkl_path = tmp_path / "meta.pkl"
        _write_pickle(pkl_path, "fine")
        # stamp_path points nowhere -- checksum_from_build_stamp must return
        # None, not raise.
        assert checksum_from_build_stamp(str(tmp_path / "no_such_stamp.json"), "meta.pkl") is None
        result = safe_pickle_load(str(pkl_path), stamp_path=str(tmp_path / "no_such_stamp.json"))
        assert result == "fine"


class TestInvalidOrCorruptedFiles:
    def test_corrupted_pickle_bytes_raise_an_unpickling_error(self, tmp_path):
        bad_path = tmp_path / "corrupt.pkl"
        bad_path.write_bytes(b"this is not a valid pickle stream at all")
        with pytest.raises(Exception):  # pickle.UnpicklingError or similar
            safe_pickle_load(str(bad_path))

    def test_unreadable_stamp_json_is_handled_safely_not_raised(self, tmp_path):
        pkl_path = tmp_path / "meta.pkl"
        _write_pickle(pkl_path, "ok")
        stamp_path = tmp_path / "build_stamp.json"
        stamp_path.write_text("{not valid json at all")
        # Must log and skip verification, not crash the whole load.
        assert checksum_from_build_stamp(str(stamp_path), "meta.pkl") is None
        result = safe_pickle_load(str(pkl_path), stamp_path=str(stamp_path))
        assert result == "ok"


class TestChecksumMismatchTamperingDetection:
    def test_tampered_file_is_rejected_before_being_unpickled(self, tmp_path):
        """The core M-08 scenario: the file on disk does NOT match its
        recorded checksum (tampered, corrupted-but-still-valid-pickle, or
        stale) -- must be rejected outright, never unpickled."""
        pkl_path = tmp_path / "meta.pkl"
        _write_pickle(pkl_path, {"original": True})
        stamp_path = tmp_path / "build_stamp.json"
        _write_stamp(stamp_path, {"meta.pkl": sha256_of_file(str(pkl_path))})

        # Tamper with the file AFTER the checksum was recorded -- e.g. an
        # attacker (or a corrupted/partial rebuild) replaced it with
        # different, still-valid pickle content.
        _write_pickle(pkl_path, {"tampered": "malicious-payload"})

        with pytest.raises(IntegrityError, match="Checksum mismatch"):
            safe_pickle_load(str(pkl_path), stamp_path=str(stamp_path))

    def test_verify_checksum_raises_on_mismatch(self, tmp_path):
        pkl_path = tmp_path / "x.pkl"
        _write_pickle(pkl_path, "v1")
        with pytest.raises(IntegrityError):
            verify_checksum(str(pkl_path), expected_sha256="0" * 64)

    def test_verify_checksum_passes_on_match(self, tmp_path):
        pkl_path = tmp_path / "x.pkl"
        _write_pickle(pkl_path, "v1")
        verify_checksum(str(pkl_path), expected_sha256=sha256_of_file(str(pkl_path)))  # must not raise

    def test_verify_checksum_skips_when_expected_is_none(self, tmp_path):
        pkl_path = tmp_path / "x.pkl"
        _write_pickle(pkl_path, "v1")
        verify_checksum(str(pkl_path), expected_sha256=None)  # must not raise


class TestRealCallSitesUseTheSharedHelper:
    """Confirms the 4 real production call sites actually route through
    safe_pickle_load() now, not a bare pickle.load() that would skip
    verification entirely."""

    def test_retriever_module_imports_integrity_module_lazily(self):
        import sqlcore.retriever as retriever_module
        import inspect
        source = inspect.getsource(retriever_module._get_index)
        assert "safe_pickle_load" in source

    def test_lexical_search_module_uses_safe_pickle_load(self):
        import sqlcore.lexical_search as lexical_search_module
        import inspect
        source = inspect.getsource(lexical_search_module._load_bm25_index)
        assert "safe_pickle_load" in source

    def test_description_fetcher_module_uses_safe_pickle_load(self):
        import sqlcore.description_fetcher as description_fetcher_module
        import inspect
        source = inspect.getsource(description_fetcher_module.search_labels_with_scores)
        assert "safe_pickle_load" in source

    def test_embedding_index_module_uses_safe_pickle_load(self):
        from backend.db_qa.intents import embedding_index
        import inspect
        source = inspect.getsource(embedding_index._load_index)
        assert "safe_pickle_load" in source
