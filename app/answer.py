"""Step 3 of RAG: search -> build the prompt -> ask the AI -> attach the sources."""
from app.config import KEYWORD_MIN_SCORE, VECTOR_MIN_SCORE
from app.llm import ask_llm
from app.search import search

NOT_COVERED = ("This is not covered in the Indian cancer guidelines available to me. "
               "Please consult a doctor.")
DISCLAIMER = "This is a student prototype for learning purposes, not medical advice."

SYSTEM_PROMPT = (
    "You are a helpful assistant for Indian cancer guidelines. Answer the question using "
    "ONLY the context below, taken from official ICMR guidelines. Do not use any outside "
    "knowledge. If the answer is not in the context, reply exactly: NOT_FOUND. Keep the "
    "answer short and clear, and mention the source numbers like [1], [2]."
)


def not_covered(method):
    return {"answer": NOT_COVERED, "sources": [], "method": method, "disclaimer": DISCLAIMER}


def answer_question(question, method="vector"):
    # 1) Find the top 4 chunks
    results = search(question, method)

    # 2) If even the best chunk is a weak match, stop here (no AI call needed)
    min_score = KEYWORD_MIN_SCORE if method == "keyword" else VECTOR_MIN_SCORE
    if not results or results[0]["score"] < min_score:
        return not_covered(method)

    # 3) Build the numbered context and ask the AI
    context = "\n\n".join(
        f"[{n}] (From {r['file']}, page {r['page']})\n{r['text']}"
        for n, r in enumerate(results, start=1)
    )
    user_message = f"Context:\n{context}\n\nQuestion: {question}"
    reply = ask_llm(SYSTEM_PROMPT, user_message)

    # 4) The AI says the context does not contain the answer
    if "NOT_FOUND" in reply:
        return not_covered(method)

    # 5) Return the answer with its sources
    sources = [
        {"number": n, "file": r["file"], "page": r["page"], "score": r["score"],
         "snippet": r["text"][:200] + "..."}
        for n, r in enumerate(results, start=1)
    ]
    return {"answer": reply, "sources": sources, "method": method, "disclaimer": DISCLAIMER}
