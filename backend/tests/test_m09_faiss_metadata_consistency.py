"""M-09: a FAISS index and its metadata pickle are only the same facts, in
the same order, when both were built together. Nothing previously checked
that `index.ntotal == len(meta)` before serving search() results -- a
partial rebuild or a stale copy of just one of the two files could silently
return the wrong row (or raise IndexError deep inside search()). Nothing
checked the embedding model used to build an index against the one
currently configured either.

Uses temporary on-disk indexes (no dependency on this machine's real
embeddings_*/ artifacts).
"""
from __future__ import annotations

import json

import faiss
import numpy as np
import pytest

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from sqlcore import retriever


def _write_index(tmp_path, name: str, n_vectors: int, dim: int = 8):
    index = faiss.IndexFlatIP(dim)
    vecs = np.random.RandomState(0).rand(n_vectors, dim).astype("float32")
    index.add(vecs)
    index_path = tmp_path / f"{name}.faiss"
    faiss.write_index(index, str(index_path))
    return str(index_path), vecs


def _write_meta(tmp_path, name: str, n_rows: int):
    import pickle
    meta = [{"table": f"t{i}"} for i in range(n_rows)]
    meta_path = tmp_path / f"{name}.pkl"
    with open(meta_path, "wb") as f:
        pickle.dump(meta, f)
    return str(meta_path)


@pytest.fixture(autouse=True)
def _clear_caches():
    retriever._index_cache.clear()
    retriever._build_stamp_cache.clear()
    yield
    retriever._index_cache.clear()
    retriever._build_stamp_cache.clear()


class TestCountMismatch:
    def test_matching_counts_load_normally(self, tmp_path):
        index_path, _ = _write_index(tmp_path, "idx", 5)
        meta_path = _write_meta(tmp_path, "idx", 5)
        index, meta = retriever._get_index(index_path, meta_path)
        assert index is not None
        assert len(meta) == 5

    def test_more_vectors_than_metadata_disables_the_index(self, tmp_path, caplog):
        index_path, _ = _write_index(tmp_path, "idx", 5)
        meta_path = _write_meta(tmp_path, "idx", 3)  # fewer meta rows than vectors
        index, meta = retriever._get_index(index_path, meta_path)
        assert index is None
        assert meta == []

    def test_fewer_vectors_than_metadata_disables_the_index(self, tmp_path):
        index_path, _ = _write_index(tmp_path, "idx", 3)
        meta_path = _write_meta(tmp_path, "idx", 5)
        index, meta = retriever._get_index(index_path, meta_path)
        assert index is None
        assert meta == []

    def test_mismatched_index_search_returns_no_results_not_a_crash(self, tmp_path):
        index_path, _ = _write_index(tmp_path, "idx", 5)
        meta_path = _write_meta(tmp_path, "idx", 2)
        results = retriever.search(index_path, meta_path, np.zeros(8, dtype="float32"), k=3)
        assert results == []

    def test_missing_index_file_still_behaves_as_before(self, tmp_path):
        """Preserves the pre-existing missing-file contract (None, [])."""
        meta_path = _write_meta(tmp_path, "idx", 5)
        index, meta = retriever._get_index(str(tmp_path / "does_not_exist.faiss"), meta_path)
        assert index is None
        assert meta == []


class TestEmbedModelCompatibility:
    def test_no_build_stamp_loads_normally(self, tmp_path):
        """Preserves today's behavior for the real embeddings_*/ directories,
        none of which currently write an embed_model field."""
        index_path, _ = _write_index(tmp_path, "idx", 4)
        meta_path = _write_meta(tmp_path, "idx", 4)
        index, meta = retriever._get_index(index_path, meta_path)
        assert index is not None and len(meta) == 4

    def test_matching_embed_model_is_silent(self, tmp_path, caplog):
        index_path, _ = _write_index(tmp_path, "idx", 4)
        meta_path = _write_meta(tmp_path, "idx", 4)
        (tmp_path / "build_stamp.json").write_text(
            json.dumps({"embed_model": retriever.config.EMBED_MODEL}), encoding="utf-8",
        )
        with caplog.at_level("WARNING"):
            index, meta = retriever._get_index(index_path, meta_path)
        assert index is not None
        assert "mismatch" not in caplog.text.lower()

    def test_mismatched_embed_model_logs_a_warning_but_still_loads(self, tmp_path, caplog):
        """A model mismatch degrades search quality but is not corruption --
        unlike the count mismatch above, this does not fail closed."""
        index_path, _ = _write_index(tmp_path, "idx", 4)
        meta_path = _write_meta(tmp_path, "idx", 4)
        (tmp_path / "build_stamp.json").write_text(
            json.dumps({"embed_model": "some-other-model"}), encoding="utf-8",
        )
        with caplog.at_level("WARNING"):
            index, meta = retriever._get_index(index_path, meta_path)
        assert index is not None  # still usable -- a warning, not a hard failure
        assert "mismatch" in caplog.text.lower()
