"""M-20: `_get_stub_xsd_path()`'s lazy temp-dir initialization
(`backend/tools/xbrl_comparator.py`) had a classic check-then-create race:
two concurrent callers could both see `_STUB_TEMP_DIR is None`, both
`tempfile.mkdtemp()` their own directory, and both `atexit.register()` a
cleanup for it -- leaking one directory and double-registering cleanup.
Now guarded by `_STUB_TEMP_DIR_LOCK` with a double-checked-locking pattern.
"""
from __future__ import annotations

import threading

import backend.tools.xbrl_comparator as xbrl_comparator


def _reset_stub_temp_dir(monkeypatch):
    monkeypatch.setattr(xbrl_comparator, "_STUB_TEMP_DIR", None)


class TestNormalInitialization:
    def test_single_call_creates_the_temp_dir_and_returns_a_path(self, monkeypatch):
        _reset_stub_temp_dir(monkeypatch)
        fname = next(iter(xbrl_comparator._SCHEMA_STUBS))
        path = xbrl_comparator._get_stub_xsd_path(fname)
        assert path is not None
        assert xbrl_comparator._STUB_TEMP_DIR is not None
        import os
        assert os.path.isfile(path)

    def test_unknown_filename_returns_none_without_creating_a_dir(self, monkeypatch):
        _reset_stub_temp_dir(monkeypatch)
        result = xbrl_comparator._get_stub_xsd_path("totally-unrecognized-file.xsd")
        assert result is None
        assert xbrl_comparator._STUB_TEMP_DIR is None

    def test_repeated_calls_reuse_the_same_temp_dir(self, monkeypatch):
        _reset_stub_temp_dir(monkeypatch)
        fname = next(iter(xbrl_comparator._SCHEMA_STUBS))
        xbrl_comparator._get_stub_xsd_path(fname)
        first_dir = xbrl_comparator._STUB_TEMP_DIR
        xbrl_comparator._get_stub_xsd_path(fname)
        assert xbrl_comparator._STUB_TEMP_DIR == first_dir


class TestConcurrentInitializationIsSafe:
    def test_many_concurrent_callers_create_exactly_one_temp_dir(self, monkeypatch):
        _reset_stub_temp_dir(monkeypatch)

        created_dirs = []
        original_mkdtemp = xbrl_comparator.tempfile.mkdtemp

        def _tracking_mkdtemp(*args, **kwargs):
            # Widen the check-then-create window deterministically (rather
            # than hoping the GIL happens to interleave within the real,
            # very fast mkdtemp() call) -- this is what makes the race
            # reproducible on every run instead of being timing-luck
            # dependent, and is exactly what distinguishes "lock present"
            # from "lock absent" regardless of machine speed.
            import time
            time.sleep(0.05)
            d = original_mkdtemp(*args, **kwargs)
            created_dirs.append(d)
            return d

        monkeypatch.setattr(xbrl_comparator.tempfile, "mkdtemp", _tracking_mkdtemp)

        atexit_registrations = []
        monkeypatch.setattr(
            xbrl_comparator.atexit, "register",
            lambda *a, **kw: atexit_registrations.append((a, kw)),
        )

        fname = next(iter(xbrl_comparator._SCHEMA_STUBS))
        results = []
        errors = []

        def worker():
            try:
                results.append(xbrl_comparator._get_stub_xsd_path(fname))
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"concurrent calls raised: {errors}"
        assert len(created_dirs) == 1, (
            f"expected exactly 1 temp dir created across 50 concurrent callers, "
            f"got {len(created_dirs)}: {created_dirs}"
        )
        assert len(atexit_registrations) == 1, (
            "cleanup must be registered exactly once, not once per racing thread"
        )
        assert len(set(results)) == 1, "every caller must get the same stub path"

        # Cleanup the real temp dir this test actually created on disk.
        import shutil
        shutil.rmtree(xbrl_comparator._STUB_TEMP_DIR, ignore_errors=True)


class TestExistingComparisonBehaviorUnchanged:
    def test_stub_file_content_matches_the_known_schema(self, monkeypatch):
        _reset_stub_temp_dir(monkeypatch)
        fname = next(iter(xbrl_comparator._SCHEMA_STUBS))
        path = xbrl_comparator._get_stub_xsd_path(fname)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert content == xbrl_comparator._SCHEMA_STUBS[fname]

    def test_is_valid_xsd_still_works_on_the_generated_stub(self, monkeypatch):
        _reset_stub_temp_dir(monkeypatch)
        fname = next(iter(xbrl_comparator._SCHEMA_STUBS))
        path = xbrl_comparator._get_stub_xsd_path(fname)
        assert xbrl_comparator._is_valid_xsd(path) is True
