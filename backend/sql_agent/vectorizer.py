from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pickle
from backend.sql_agent.config import EMBED_MODEL, QUERY_PREFIX

model = SentenceTransformer(EMBED_MODEL)


def embed_documents(texts):
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True,
    )
    return np.array(vectors, dtype="float32")


def embed_query(query):
    query = QUERY_PREFIX + query
    return model.encode([query], normalize_embeddings=True)[0]


def build_faiss_index(vectors):
    vectors = np.array(vectors, dtype="float32")

    if len(vectors.shape) == 1:
        raise ValueError("Embedding output is 1D — check input texts")

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


def save_index(index, meta, index_path, meta_path):
    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(meta, f)


def build_row_label_index(samples: dict):
    """
    Build a FAISS index over every distinct row-label value fetched from the DB.

    Parameters
    ----------
    samples : dict
        Output of description_fetcher.fetch_and_save():
        { table_name: { col_name: [val1, val2, ...] } }

    Returns
    -------
    (index, records) — index is a faiss.Index; records is list of dicts
    { table, column, value } in the same order as the indexed vectors.
    """
    records = []
    texts   = []
    for table, col_map in samples.items():
        for col, values in col_map.items():
            for val in values:
                records.append({"table": table, "column": col, "value": val})
                texts.append(f"{table} {col} {val}")

    if not texts:
        return None, []

    vectors = embed_documents(texts)
    index   = build_faiss_index(vectors)
    return index, records
