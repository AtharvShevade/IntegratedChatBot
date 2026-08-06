from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pickle
import re
from src.config import EMBED_MODEL, QUERY_PREFIX

model = SentenceTransformer(EMBED_MODEL)


def normalize_text(text):
    """Lowercase, collapse whitespace, strip trailing punctuation.

    Applied identically on both the index-build side (embed_documents) and
    the query side (embed_query) so the two are never compared asymmetrically.
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[?.!,;:]+$", "", text)
    return text


def embed_documents(texts):
    texts = [normalize_text(t) for t in texts]
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True,
    )
    return np.array(vectors, dtype="float32")


def embed_query(query):
    query = QUERY_PREFIX + normalize_text(query)
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
    index  : faiss.Index  (IndexFlatIP, L2-normalised vectors)
    records: list of dicts with keys: table, column, value, text
    """
    records = []
    for table, col_map in samples.items():
        for col, values in col_map.items():
            for val in values:
                # Descriptive text so the embedding captures semantic meaning
                text = f"{table} {col} label: {val}"
                records.append({
                    "table": table,
                    "column": col,
                    "value": val,
                    "text": text,
                })

    if not records:
        return None, []

    texts = [r["text"] for r in records]
    vectors = embed_documents(texts)
    index = build_faiss_index(vectors)
    return index, records