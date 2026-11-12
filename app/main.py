"""The web API. Start it with:  uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs to try every endpoint."""
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.answer import answer_question
from app.ingest import build_index
from app.llm import LLMError
from app.search import IndexNotReady, chunk_count, get_model, load_index


@asynccontextmanager
async def lifespan(app):
    """Runs once when the server starts: load the embedding model and the saved index."""
    get_model()
    try:
        n = load_index()
        print(f"Loaded {n} chunks.")
    except IndexNotReady:
        print("No index yet. Please run /ingest first.")
    yield


app = FastAPI(title="Indian Cancer Guideline Chatbot (RAG prototype)", lifespan=lifespan)


# ---- Request formats ----
class AskRequest(BaseModel):
    question: str
    method: Literal["vector", "keyword"] = "vector"


class CompareRequest(BaseModel):
    question: str


def run(question, method):
    """Call answer_question and turn our errors into clear HTTP error messages."""
    if not question.strip():
        raise HTTPException(400, "Question is empty.")
    try:
        return answer_question(question, method)
    except IndexNotReady as e:
        raise HTTPException(400, str(e))
    except LLMError as e:
        raise HTTPException(500, str(e))


# ---- Endpoints ----
@app.get("/health")
def health():
    return {"status": "running", "chunks_loaded": chunk_count()}


@app.post("/ingest")
def ingest():
    try:
        summary = build_index()
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    load_index()  # load the new index into memory
    return {"message": "Index built.", **summary}


@app.post("/ask")
def ask(req: AskRequest):
    return run(req.question, req.method)


@app.post("/compare")
def compare(req: CompareRequest):
    return {
        "question": req.question,
        "vector": run(req.question, "vector"),
        "keyword": run(req.question, "keyword"),
    }
