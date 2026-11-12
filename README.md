# Indian Cancer Guideline Chatbot (RAG prototype)

A question-answering backend that answers cancer questions **only** from the official ICMR
"Consensus Document for Management of ___ Cancer" guidelines (Government of India).
It finds the matching parts of the guideline PDFs, lets an AI model write a short answer using
**only that text**, and shows the **file and page** it came from. If the guidelines don't cover
the question, it says so instead of guessing.

```
PDF  →  chunks  →  search (vector / keyword)  →  AI  →  answer + source (file, page)
```

## 1. Setup (Windows)

```bash
python -m venv venv                 # or: py -3.11 -m venv venv
venv\Scripts\activate               # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env
```

AI model: **Groq** (free). Get a free key at https://console.groq.com/keys and paste it into
`.env` after `LLM_API_KEY=`. Never put the key in the code.

## 2. Get the guidelines

Download the cancer consensus documents from the ICMR website (**icmr.gov.in → Guidelines**),
e.g. breast, lung, oral, cervical and colorectal cancer, and put the PDFs in `data/guidelines/`.

## 3. Run from the terminal (PowerShell)

Open a terminal in the project folder (`PS C:\Users\asus\OneDrive\Desktop\STP_cancer>`).

**Step 1: Activate the venv.** You should then see `(venv)` at the start of the line.
```powershell
venv\Scripts\activate
```
If you get *"running scripts is disabled on this system"*, run this once, then activate again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Step 2: Build the index.** Only needed the first time, or after adding or changing PDFs.
```powershell
python -m app.ingest
```
Expected output: `Done: 1 PDFs, 27 pages, 29 chunks.`

**Step 3: Start the server.**
```powershell
uvicorn app.main:app --reload
```
It is ready when you see `Loaded 29 chunks.` and `Uvicorn running on http://127.0.0.1:8000`.
The first start takes 10–20 seconds because it loads the embedding model.
**Keep this terminal open** during the demo. Press `Ctrl + C` to stop the server.

**Step 4 (optional): Run the 10 test questions.** Run this in a second terminal, after activating the venv there too.
```powershell
python test_questions.py
```
This saves the question, method, answer and sources for every run to `results.csv`.

## 4. Test the API

### Option A: Swagger (browser)
Open **http://127.0.0.1:8000/docs**. For any endpoint, click **Try it out**, edit the JSON, and press **Execute**.

### Option B: Postman
In Postman, click **New → HTTP Request** for each request below.
For every **POST** request, open the **Body** tab, choose **raw**, and pick **JSON** from the dropdown.
Tip: create a collection (**New → Collection**, e.g. "Cancer Chatbot") and save all requests in it.

**1. Health check**
- Method: `GET`
- URL: `http://127.0.0.1:8000/health`
- Body: none
- Expected: `{"status": "running", "chunks_loaded": 29}`

**2. Ask a question (vector search)**
- Method: `POST`
- URL: `http://127.0.0.1:8000/ask`
- Body:
```json
{
  "question": "How often should follow up visits be done after breast cancer treatment?",
  "method": "vector"
}
```
- Expected: every 6 months for 5 years, then yearly up to 10 years, then every 2 years. The sources show **page 21**.

**3. Ask a question (keyword search)**
- Method: `POST`
- URL: `http://127.0.0.1:8000/ask`
- Body:
```json
{
  "question": "When is genetic testing for BRCA1/2 recommended?",
  "method": "keyword"
}
```
- Expected: an answer based on **page 25** (hereditary breast cancer).

**4. Compare both methods**
- Method: `POST`
- URL: `http://127.0.0.1:8000/compare`
- Body:
```json
{
  "question": "What radiotherapy dose is used for painful bone metastasis from breast cancer?"
}
```
- Expected: the `vector` and `keyword` answers side by side, each with its own sources and scores.

**5. Question not in the guidelines**
- Method: `POST`
- URL: `http://127.0.0.1:8000/ask`
- Body:
```json
{
  "question": "Who won the cricket World Cup?",
  "method": "vector"
}
```
- Expected: *"This is not covered in the Indian cancer guidelines available to me. Please consult a doctor."*

**6. Rebuild the index (optional)**
- Method: `POST`
- URL: `http://127.0.0.1:8000/ingest`
- Body: none
- Expected: `{"message": "Index built.", "pdfs": 1, "pages": 27, "chunks": 29}`. This takes about 30 seconds.

## 5. Viva demo order

1. **Terminal:** show the server starting with `Loaded 29 chunks.`
2. **`/health`:** the server is running and the guideline data is loaded.
3. **`/ask` (follow-up question):** show the answer and `"page": 21` in the sources. Open the PDF at page 21 to prove the answer comes from the guideline.
4. **`/compare`:** compare meaning-based search (vector) with word-matching search (keyword), including their scores.
5. **`/ask` (cricket):** show that it does not guess. It returns "not covered" because the search score is too low, so the AI is not even called.
6. **`/ask` with `How is lung cancer treated?`:** it says "not covered" because only the breast cancer PDF is loaded. The AI replied `NOT_FOUND` instead of using its own knowledge.
7. **`results.csv`:** 10 test questions × 2 methods, all with correct results.

**Before the viva:** make sure your internet works, because the answer step calls Groq. The search itself runs offline on the laptop.

**Note on page numbers:** sources show the page number in the PDF viewer, not the number printed on the page. For the breast cancer PDF, the printed number is 10 higher (PDF page 21 = printed page 31).

## 6. How it works (files)

| File | Job |
|---|---|
| `app/config.py` | reads settings from `.env` |
| `app/ingest.py` | PDF → clean text → 500-word chunks (50 overlap) → FAISS + BM25 index |
| `app/search.py` | `vector` (meaning, FAISS) and `keyword` (BM25) search, top 4 chunks |
| `app/llm.py` | sends the prompt to the AI model (temperature 0) |
| `app/answer.py` | search → score check → prompt → answer + sources |
| `app/main.py` | FastAPI endpoints |

Two safety checks stop made-up answers: (1) if the best search score is below the threshold in
`.env`, we answer "not covered" without calling the AI; (2) the AI is told to reply `NOT_FOUND`
when the context does not contain the answer.

## 7. Cost

**Everything is free.** All libraries are open-source, embeddings (`all-MiniLM-L6-v2`) and search
(FAISS, BM25) run locally on the CPU, and the Groq API has a free tier.

*This is a student prototype for learning purposes, not medical advice.*
