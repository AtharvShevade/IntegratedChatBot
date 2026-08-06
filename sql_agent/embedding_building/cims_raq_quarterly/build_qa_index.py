"""
Embeds qa_pairs.json's questions into a FAISS index — the "question -> gold
SQL" signal that src/retriever.py's search_qa()/get_relevant_schema() already
knows how to consume (it's the same qa_index.faiss/qa_meta.pkl shape the
retriever looks for, generically, under whatever EMBEDDING_DIR points at).

Usage:
    python embedding_building/cims_raq_quarterly/build_qa_index.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
QA_PAIRS_PATH = os.path.join(OUT_DIR, "qa_pairs.json")

from src.vectorizer import embed_documents, build_faiss_index, save_index


def build_qa_records(qa_pairs):
    return [
        {"text": qa["question"], "table": qa["table"], "question": qa["question"], "sql": qa["sql"]}
        for qa in qa_pairs
    ]


def main():
    with open(QA_PAIRS_PATH, encoding="utf-8") as f:
        qa_pairs = json.load(f)
    print(f"Loaded {len(qa_pairs)} question/SQL pairs from {QA_PAIRS_PATH}")

    records = build_qa_records(qa_pairs)
    vecs = embed_documents([r["text"] for r in records])
    index = build_faiss_index(vecs)

    save_index(index, records,
               os.path.join(OUT_DIR, "qa_index.faiss"), os.path.join(OUT_DIR, "qa_meta.pkl"))
    print(f"-> qa_index.faiss ({index.ntotal} vectors)")


if __name__ == "__main__":
    main()
