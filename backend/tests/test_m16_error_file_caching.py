"""M-16: the same error-explanation HTML document was re-read and re-parsed
from disk for every batch of "Explain next" requests. Three parse functions
(`backend.tools.report_lookup.parse_backtrack_html_errors`,
`backend.tools.formula_error.parse_formula_errors_v2`,
`backend.tools.formula_error_generic.parse_generic_formula_errors`) are now
memoized by `(path, mtime)` via `backend.tools.mtime_cache.cached_by_mtime`.
"""
from __future__ import annotations

import time

from backend.tools.mtime_cache import cached_by_mtime, _cache


class TestCachedByMtime:
    def test_first_access_calls_parse(self, tmp_path):
        f = tmp_path / "x.html"
        f.write_text("<html>v1</html>")
        calls = []
        def parse():
            calls.append(1)
            return "parsed-v1"
        result = cached_by_mtime(str(f), parse)
        assert result == "parsed-v1"
        assert len(calls) == 1

    def test_repeated_access_with_unchanged_mtime_uses_cache(self, tmp_path):
        f = tmp_path / "x.html"
        f.write_text("<html>v1</html>")
        calls = []
        def parse():
            calls.append(1)
            return "parsed-v1"
        cached_by_mtime(str(f), parse)
        cached_by_mtime(str(f), parse)
        cached_by_mtime(str(f), parse)
        assert len(calls) == 1, "parse() must only run once while the file is unchanged"

    def test_modified_file_causes_a_fresh_parse(self, tmp_path):
        f = tmp_path / "x.html"
        f.write_text("<html>v1</html>")
        calls = []
        def parse_v1():
            calls.append("v1")
            return "parsed-v1"
        result1 = cached_by_mtime(str(f), parse_v1)
        assert result1 == "parsed-v1"

        # Force a distinct mtime (some filesystems have 1s+ resolution).
        time.sleep(0.01)
        new_time = time.time() + 5
        f.write_text("<html>v2</html>")
        import os
        os.utime(str(f), (new_time, new_time))

        def parse_v2():
            calls.append("v2")
            return "parsed-v2"
        result2 = cached_by_mtime(str(f), parse_v2)
        assert result2 == "parsed-v2"
        assert calls == ["v1", "v2"], "a changed mtime must trigger a fresh parse"

    def test_missing_file_is_never_cached(self, tmp_path):
        missing = str(tmp_path / "does_not_exist.html")
        calls = []
        def parse():
            calls.append(1)
            return []
        cached_by_mtime(missing, parse)
        cached_by_mtime(missing, parse)
        assert len(calls) == 2, "a missing file must not be cached as a false negative"

    def test_cache_stores_at_most_one_entry_per_path(self, tmp_path):
        f = tmp_path / "x.html"
        f.write_text("<html>v1</html>")
        before = len(_cache)
        cached_by_mtime(str(f), lambda: "a")
        cached_by_mtime(str(f), lambda: "b")  # same file, same mtime -> cache hit, not a new entry
        after = len(_cache)
        assert after == before + 1


class TestRealParsersAreMemoized:
    """Confirms the actual production parse functions route through the
    cache, using a real temp HTML file (not mocking the cache itself)."""

    def test_parse_backtrack_html_errors_is_memoized(self, tmp_path, monkeypatch):
        from backend.tools import report_lookup

        html = tmp_path / "errors.html"
        html.write_text("<html><body>no recognizable table</body></html>")

        call_count = {"n": 0}
        original = report_lookup._parse_backtrack_html_errors_uncached

        def _counting(path):
            call_count["n"] += 1
            return original(path)

        monkeypatch.setattr(report_lookup, "_parse_backtrack_html_errors_uncached", _counting)

        r1 = report_lookup.parse_backtrack_html_errors(str(html))
        r2 = report_lookup.parse_backtrack_html_errors(str(html))
        assert r1 == r2 == []
        assert call_count["n"] == 1, "second call with unchanged mtime must hit the cache"

    def test_parse_formula_errors_v2_is_memoized(self, tmp_path, monkeypatch):
        from backend.tools import formula_error

        html = tmp_path / "errors.html"
        html.write_text("<html><body>no recognizable formula panel</body></html>")

        call_count = {"n": 0}
        original = formula_error._parse_formula_errors_v2_uncached

        def _counting(path):
            call_count["n"] += 1
            return original(path)

        monkeypatch.setattr(formula_error, "_parse_formula_errors_v2_uncached", _counting)

        r1 = formula_error.parse_formula_errors_v2(str(html))
        r2 = formula_error.parse_formula_errors_v2(str(html))
        assert r1 == r2 == []
        assert call_count["n"] == 1

    def test_parse_generic_formula_errors_is_memoized(self, tmp_path, monkeypatch):
        from backend.tools import formula_error_generic

        html = tmp_path / "errors.html"
        html.write_text("<html><body>no recognizable table</body></html>")

        call_count = {"n": 0}
        original = formula_error_generic._parse_generic_formula_errors_uncached

        def _counting(path):
            call_count["n"] += 1
            return original(path)

        monkeypatch.setattr(formula_error_generic, "_parse_generic_formula_errors_uncached", _counting)

        r1 = formula_error_generic.parse_generic_formula_errors(str(html))
        r2 = formula_error_generic.parse_generic_formula_errors(str(html))
        assert r1 == r2 == []
        assert call_count["n"] == 1

    def test_parse_formula_errors_v2_output_identical_to_before(self, tmp_path):
        """Confirms the OUTPUT (not just call count) is unchanged by
        caching -- the exact same result object/content for the same input."""
        from backend.tools import formula_error

        html = tmp_path / "errors.html"
        html.write_text("<html><body>irrelevant</body></html>")

        uncached_result = formula_error._parse_formula_errors_v2_uncached(str(html))
        cached_result = formula_error.parse_formula_errors_v2(str(html))
        assert uncached_result == cached_result
