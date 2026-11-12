"""Step 2 of RAG: find the chunks that best match a question.

Two methods, so we can compare them:
  - vector : meaning-based search (embeddings + FAISS)
  - keyword: word-matching search (BM25)
"""
import json
import pickle
import re

import faiss
from sentence_transformers import SentenceTransformer

from app.config import EMBED_MODEL, INDEX_DIR, TOP_K

# Everything is loaded once and kept in memory here
_model = None
_store = {"chunks": [], "faiss": None, "bm25": None}


class IndexNotReady(Exception):
    """Raised when someone searches before the index has been built."""


def get_model():
    """Load the embedding model once (first call downloads it, ~90 MB)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL, device="cpu")
    return _model


# Very common words that carry no meaning; BM25 ignores them
STOPWORDS = set("""a an and are as at be by can do does for from has have how i in is it
its of on or should the this to was were what when where which who why will with""".split())


def tokenize(text):
    """Lowercase, split into words and drop stop words. Used by BM25."""
    return [w for w in re.findall(r"\w+", text.lower()) if w not in STOPWORDS]


def load_index():
    """Read the saved index files from data/index/. Returns how many chunks were loaded."""
    if not (INDEX_DIR / "chunks.json").exists():
        raise IndexNotReady("Index not found. Please run /ingest first.")
    with open(INDEX_DIR / "chunks.json", encoding="utf-8") as f:
        _store["chunks"] = json.load(f)
    _store["faiss"] = faiss.read_index(str(INDEX_DIR / "faiss.index"))
    with open(INDEX_DIR / "bm25.pkl", "rb") as f:
        _store["bm25"] = pickle.load(f)
    return len(_store["chunks"])


def chunk_count():
    return len(_store["chunks"])


def _result(i, score):
    """Package one chunk as a result dictionary."""
    c = _store["chunks"][i]
    return {"text": c["text"], "file": c["file"], "page": c["page"], "score": round(float(score), 3)}


def vector_search(question, k=TOP_K):
    """Embed the question and find the chunks with the closest meaning."""
    q_vec = get_model().encode([question], normalize_embeddings=True)
    scores, ids = _store["faiss"].search(q_vec, k)
    return [_result(i, s) for i, s in zip(ids[0], scores[0]) if i != -1]


def keyword_search(question, k=TOP_K):
    """Score every chunk by how many question words it contains (BM25)."""
    scores = _store["bm25"].get_scores(tokenize(question))
    best = scores.argsort()[::-1][:k]  # indexes of the k highest scores
    return [_result(i, scores[i]) for i in best]


def search(question, method="vector", k=TOP_K):
    """Run the chosen search method and return the top k chunks."""
    if not _store["chunks"]:
        raise IndexNotReady("Index not loaded. Please run /ingest first.")
    if method == "keyword":
        return keyword_search(question, k)
    return vector_search(question, k)


if __name__ == "__main__":
    # Quick manual test:  python -m app.search
    load_index()
    q = "What is the screening method for cervical cancer?"
    for m in ["vector", "keyword"]:
        print(f"\n=== {m} ===")
        for r in search(q, m):
            print(f"{r['score']:>7}  {r['file']} p.{r['page']}  {r['text'][:90]}...")
