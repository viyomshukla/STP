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
8. **Terminal: `python eval_retrieval.py`:** live search-quality metrics (see section 6).

**Before the viva:** make sure your internet works, because the answer step calls Groq. The search itself runs offline on the laptop.

**Note on page numbers:** sources show the page number in the PDF viewer, not the number printed on the page. For the breast cancer PDF, the printed number is 10 higher (PDF page 21 = printed page 31).

## 6. Evaluation: does search put the correct result on top?

The answer can only be correct if the search step finds the right page first. So we measure
**search quality separately**, using standard information-retrieval metrics.

### How the test was made
1. We wrote **22 questions** about the breast cancer guideline (`LABELLED_QUESTIONS` in `eval_retrieval.py`).
2. For each question, we **searched the PDF text for the answer** and wrote down the page that contains it.
   Example: *"How often should follow up visits be done?"* → page 21, which says *"every 6 months ... annual up to 10 years and then 2 yearly"*.
3. The script runs each question through **both** search methods, takes the **top 4 results** (the same 4 that are sent to the AI),
   and checks where the correct page appears.

### Metrics (0 to 1, higher is better)

| Metric | Meaning | Example |
|---|---|---|
| **Hit@1** | Is the **first** result the correct page? | correct page 1st → 1, otherwise 0 |
| **Recall@4** | Is the correct page **anywhere in the top 4**? | found → 1, missing → 0 |
| **MRR** | 1 ÷ position of the first correct result | 1st → 1.0, 2nd → 0.5, 3rd → 0.33, 4th → 0.25 |
| **nDCG@4** | Gives more credit when correct results are **higher** in the list | all correct results at the top → 1.0 |

### Results (22 questions, top 4 results, 500-word chunks)

| Method | Hit@1 | Recall@4 | MRR | nDCG@4 |
|---|---|---|---|---|
| vector (meaning) | 0.55 | 0.86 | 0.69 | 0.72 |
| keyword (BM25) | **0.82** | **0.98** | **0.88** | **0.88** |

**What this means**
- The correct page is in the top 4 results **86% (vector)** and **98% (keyword)** of the time. The AI receives all 4 results,
  so it almost always has the right text. This is why all 20 answers in `results.csv` are correct.
- Keyword search puts the correct page **first** in 82% of questions. Vector search does so in 55%.
- **Why vector is weaker here:** the embedding model `all-MiniLM-L6-v2` reads only the first **256 tokens (about 180 words)**
  of each chunk. Our chunks are 500 words, so the end of each page is not embedded. For example, the Ki67 and trastuzumab answers
  sit near the bottom of their pages, and vector search missed them.
- **Possible improvement (tested):** with **150-word chunks**, vector search Hit@1 rises from **0.55 to 0.86** and MRR from **0.69 to 0.90**.
- **Limitations:** this is a small test (one PDF, 22 questions). The questions were written after reading the PDF and reuse
  its words, which slightly favours keyword search.

### How to show it live
Make sure the venv is active. No API key or internet is needed for this step.
```powershell
python eval_retrieval.py
```
This prints a table for every question:
```
Question                                   Method   Correct   Top 4 pages        Hit@1  nDCG
How often should follow up visits be ...   vector   [21]      [21, 1, 1, 22]     1      1.0
```
- **Correct** is the page that really contains the answer.
- **Top 4 pages** is what search returned, best first.
- At the bottom is the **AVERAGE** table with Hit@1, Recall@4, MRR and nDCG@4.

All rows are also saved to `retrieval_eval.csv`, which you can open in Excel.

**To prove one result by hand:**
1. Pick a row, e.g. *"How often should follow up visits be done..."*, with correct page **21**.
2. In Swagger (`/docs`) or Postman, call `/ask` with that question. The sources show `"page": 21` first.
3. Open `data/guidelines/Breast_Cancer_ICMR_clinical.pdf` at PDF page 21 and show the answer text on that page.

**To add a new test question:** add a line like `("your question", [page]),` to `LABELLED_QUESTIONS`
in `eval_retrieval.py` and run the script again.

## 7. How it works (files)

| File | Job |
|---|---|
| `app/config.py` | reads settings from `.env` |
| `app/ingest.py` | PDF → clean text → 500-word chunks (50 overlap) → FAISS + BM25 index |
| `app/search.py` | `vector` (meaning, FAISS) and `keyword` (BM25) search, top 4 chunks |
| `app/llm.py` | sends the prompt to the AI model (temperature 0) |
| `app/answer.py` | search → score check → prompt → answer + sources |
| `app/main.py` | FastAPI endpoints |
| `test_questions.py` | 10 questions × 2 methods → full answers saved to `results.csv` |
| `eval_retrieval.py` | search quality metrics (Hit@1, Recall@4, MRR, nDCG@4) → `retrieval_eval.csv` |

Two safety checks stop made-up answers: (1) if the best search score is below the threshold in
`.env`, we answer "not covered" without calling the AI; (2) the AI is told to reply `NOT_FOUND`
when the context does not contain the answer.

## 8. Cost

**Everything is free.** All libraries are open-source, embeddings (`all-MiniLM-L6-v2`) and search
(FAISS, BM25) run locally on the CPU, and the Groq API has a free tier.

*This is a student prototype for learning purposes, not medical advice.*
