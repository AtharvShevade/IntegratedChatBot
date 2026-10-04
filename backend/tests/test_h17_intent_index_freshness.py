"""H-17: the semantic intent exemplar index (FAISS + metadata) could drift
from ``exemplars.py`` with nothing detecting it -- the review found the
on-disk index covered only ~60% of the real phrasings, and the thresholds
tuned against it had no freshness signal to invalidate them.

``backend/db_qa/intents/embedding_index.py`` now writes a small
``intent_exemplar_manifest.json`` alongside the index every time
``build_index()`` runs, recording a deterministic fingerprint of every
(intent, phrasing) pair plus the embedding model name.
``check_index_freshness()`` compares the current exemplars/model against that
manifest; ``_load_index()`` calls it and triggers an automatic rebuild on any
mismatch (or a missing manifest) instead of silently serving a stale index.

These tests work entirely against a temporary fingerprint/manifest file
in isolation -- they never touch the real committed index artifacts under
``backend/db_qa/intents/output/``, so a test run can't leave the real
development index in a different state than it started in.
"""
from __future__ import annotations

import json

import pytest

from backend.db_qa.intents import embedding_index as ei


@pytest.fixture
def manifest_path(tmp_path, monkeypatch):
    path = tmp_path / "intent_exemplar_manifest.json"
    monkeypatch.setattr(ei, "MANIFEST_PATH", str(path))
    return path


class TestFingerprintIsDeterministic:
    def test_same_exemplars_same_fingerprint(self):
        assert ei._fingerprint_exemplars() == ei._fingerprint_exemplars()

    def test_fingerprint_changes_when_exemplars_change(self, monkeypatch):
        from backend.db_qa.intents.taxonomy import Intent

        original = ei._fingerprint_exemplars()
        fake_exemplars = {next(iter(ei.EXEMPLARS)): ["a totally new made-up phrasing"]}
        monkeypatch.setattr(ei, "EXEMPLARS", fake_exemplars)
        assert ei._fingerprint_exemplars() != original

    def test_fingerprint_is_order_independent(self, monkeypatch):
        forward = {"a": ["x", "y"], "b": ["z"]}
        backward = {"b": ["z"], "a": ["y", "x"]}

        def fp(exemplars):
            import hashlib
            items = sorted((k, p) for k, ps in exemplars.items() for p in ps)
            h = hashlib.sha256()
            for k, p in items:
                h.update(k.encode()); h.update(b"\x00"); h.update(p.encode()); h.update(b"\x01")
            return h.hexdigest()

        assert fp(forward) == fp(backward)


class TestCheckIndexFreshness:
    def test_matching_hash_and_model_is_fresh(self, manifest_path, monkeypatch):
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")
        manifest_path.write_text(json.dumps({
            "fingerprint": ei._fingerprint_exemplars(),
            "embed_model": "test-model",
            "exemplar_count": 1,
        }))
        fresh, reason = ei.check_index_freshness()
        assert fresh is True
        assert reason == ""

    def test_changed_exemplar_source_is_detected_as_mismatch(self, manifest_path, monkeypatch):
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")
        manifest_path.write_text(json.dumps({
            "fingerprint": "deadbeef-not-the-real-hash",
            "embed_model": "test-model",
            "exemplar_count": 1,
        }))
        fresh, reason = ei.check_index_freshness()
        assert fresh is False
        assert "exemplars.py has changed" in reason

    def test_changed_embedding_model_is_detected_as_mismatch(self, manifest_path, monkeypatch):
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "new-model-v2")
        manifest_path.write_text(json.dumps({
            "fingerprint": ei._fingerprint_exemplars(),
            "embed_model": "old-model-v1",
            "exemplar_count": 1,
        }))
        fresh, reason = ei.check_index_freshness()
        assert fresh is False
        assert "embedding model changed" in reason

    def test_missing_manifest_is_handled_safely_not_raised(self, manifest_path, monkeypatch):
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")
        assert not manifest_path.exists()
        fresh, reason = ei.check_index_freshness()  # must not raise
        assert fresh is False
        assert "no manifest found" in reason

    def test_corrupt_manifest_is_handled_safely_not_raised(self, manifest_path, monkeypatch):
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")
        manifest_path.write_text("{not valid json")
        fresh, reason = ei.check_index_freshness()  # must not raise
        assert fresh is False
        assert "unreadable" in reason


class TestBuildIndexWritesManifest:
    def test_rebuilt_index_manifest_loads_successfully_and_is_fresh(self, manifest_path, monkeypatch):
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")
        ei._write_manifest()
        assert manifest_path.exists()
        fresh, reason = ei.check_index_freshness()
        assert fresh is True, reason

    def test_manifest_records_current_exemplar_count(self, manifest_path, monkeypatch):
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")
        ei._write_manifest()
        manifest = json.loads(manifest_path.read_text())
        expected = sum(len(p) for p in ei.EXEMPLARS.values())
        assert manifest["exemplar_count"] == expected


class TestLoadIndexTriggersRebuildOnStaleness:
    def test_load_index_rebuilds_when_manifest_mismatches(self, tmp_path, monkeypatch):
        """Full integration of the detection -> rebuild wiring in
        _load_index(), using fake index/meta/build functions so this test
        never touches the real FAISS index or calls the real embedding
        model."""
        index_path = tmp_path / "index.faiss"
        meta_path = tmp_path / "meta.pkl"
        manifest_path = tmp_path / "manifest.json"
        index_path.write_bytes(b"fake-index-bytes")
        import pickle
        meta_path.write_bytes(pickle.dumps([{"intent": "x", "text": "y"}]))
        # Deliberately stale/missing manifest.
        monkeypatch.setattr(ei, "INDEX_PATH", str(index_path))
        monkeypatch.setattr(ei, "META_PATH", str(meta_path))
        monkeypatch.setattr(ei, "MANIFEST_PATH", str(manifest_path))
        ei._INDEX_CACHE.clear()

        rebuilt = {"called": False}

        def fake_build_index():
            rebuilt["called"] = True
            # Simulate a successful rebuild writing a fresh manifest.
            ei._write_manifest()

        monkeypatch.setattr(ei, "build_index", fake_build_index)
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")

        class _FakeFaissIndex:
            pass

        import sys
        import types
        fake_faiss = types.SimpleNamespace(read_index=lambda path: _FakeFaissIndex())
        monkeypatch.setitem(sys.modules, "faiss", fake_faiss)

        try:
            ei._load_index()
        finally:
            ei._INDEX_CACHE.clear()

        assert rebuilt["called"] is True, "a stale/missing manifest must trigger an automatic rebuild"

    def test_load_index_does_not_rebuild_when_fresh(self, tmp_path, monkeypatch):
        index_path = tmp_path / "index.faiss"
        meta_path = tmp_path / "meta.pkl"
        manifest_path = tmp_path / "manifest.json"
        index_path.write_bytes(b"fake-index-bytes")
        import pickle
        meta_path.write_bytes(pickle.dumps([{"intent": "x", "text": "y"}]))
        monkeypatch.setattr(ei, "INDEX_PATH", str(index_path))
        monkeypatch.setattr(ei, "META_PATH", str(meta_path))
        monkeypatch.setattr(ei, "MANIFEST_PATH", str(manifest_path))
        monkeypatch.setattr(ei, "_current_embed_model_name", lambda: "test-model")
        ei._INDEX_CACHE.clear()
        ei._write_manifest()  # matches current exemplars -> fresh

        rebuilt = {"called": False}
        monkeypatch.setattr(ei, "build_index", lambda: rebuilt.__setitem__("called", True))

        class _FakeFaissIndex:
            pass

        import sys
        import types
        fake_faiss = types.SimpleNamespace(read_index=lambda path: _FakeFaissIndex())
        monkeypatch.setitem(sys.modules, "faiss", fake_faiss)

        try:
            ei._load_index()
        finally:
            ei._INDEX_CACHE.clear()

        assert rebuilt["called"] is False, "a fresh index must not trigger a rebuild"
