"""Step 1 of RAG: read the guideline PDFs, cut them into chunks, and build the search indexes.

Run it with:  python -m app.ingest
"""
import json
import pickle
import re

import faiss
import pymupdf  # reads PDF files
from rank_bm25 import BM25Okapi

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, GUIDELINES_DIR, INDEX_DIR
from app.search import get_model, tokenize

# Pages whose heading contains one of these words are front matter, not medical content
FRONT_PAGE_WORDS = [
    "foreword", "message", "preface", "acknowledgement", "acknowledgment",
    "committee", "contributors", "expert group", "members", "table of contents",
]
MIN_WORDS_PER_PAGE = 40  # pages with fewer words are skipped (blank, images, titles)


def clean_page(text):
    """Remove the repeated page header and fix small PDF text problems."""
    text = text.replace("\x08", "").replace("••", ";")  # PDF bullet symbols -> ";"
    # Drop the header line "Consensus Document for Management of ___ Cancer" and bare page numbers
    lines = [line for line in text.splitlines()
             if not re.match(r"^\s*(\d+\s*)?Consensus Document for Management of .*Cancer\s*$", line)
             and not re.match(r"^\s*\d+\s*$", line)]
    text = "\n".join(lines)
    # Join big first letters printed on their own line: "B\nreast" -> "Breast"
    return re.sub(r"(?m)^([A-Z])\n(?=[a-z])", r"\1", text)


def is_front_page(text):
    """True if the top of the page looks like Foreword / Message / committee list etc."""
    heading = text[:80].lower()
    return any(word in heading for word in FRONT_PAGE_WORDS)


def split_into_chunks(words, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Cut a list of words into pieces of `size` words, each overlapping the last by `overlap`."""
    chunks = []
    step = size - overlap
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        chunks.append(" ".join(piece))
        if start + size >= len(words):
            break
    return chunks


def read_pdfs():
    """Read every PDF page by page and return a list of chunks (text + file name + page)."""
    pdf_files = sorted(GUIDELINES_DIR.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {GUIDELINES_DIR}. Please add the guideline PDFs.")

    chunks = []
    pages_used = 0
    for pdf_path in pdf_files:
        doc = pymupdf.open(pdf_path)
        for page_number, page in enumerate(doc, start=1):
            text = clean_page(page.get_text())
            words = text.split()
            # Skip almost-empty pages and front pages
            if len(words) < MIN_WORDS_PER_PAGE or is_front_page(text):
                continue
            pages_used += 1
            # We chunk each page separately so every chunk has one exact page number
            for piece in split_into_chunks(words):
                chunks.append({"text": piece, "file": pdf_path.name, "page": page_number})
        doc.close()
    return pdf_files, pages_used, chunks


def build_index():
    """Read PDFs, make embeddings, build FAISS + BM25, and save everything to data/index/."""
    pdf_files, pages_used, chunks = read_pdfs()
    texts = [c["text"] for c in chunks]

    # 1) Vector index: turn every chunk into a 384-number vector (embedding)
    model = get_model()
    print(f"Making embeddings for {len(texts)} chunks (CPU, may take a minute)...")
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    # Normalised vectors + inner product = cosine similarity
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    # 2) Keyword index: BM25 over the words of each chunk
    bm25 = BM25Okapi([tokenize(t) for t in texts])

    # 3) Save to disk
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / "faiss.index"))
    with open(INDEX_DIR / "bm25.pkl", "wb") as f:
        pickle.dump(bm25, f)
    with open(INDEX_DIR / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=1)

    summary = {"pdfs": len(pdf_files), "pages": pages_used, "chunks": len(chunks)}
    print(f"Done: {summary['pdfs']} PDFs, {summary['pages']} pages, {summary['chunks']} chunks.")
    return summary


if __name__ == "__main__":
    build_index()
