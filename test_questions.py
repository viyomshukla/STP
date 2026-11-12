"""Runs 10 sample questions with both search methods and saves the answers to results.csv.

Run it with:  python test_questions.py
(The index must be built first:  python -m app.ingest)
"""
import csv

from app.answer import answer_question
from app.search import load_index

# 8 questions whose answers ARE in the ICMR breast cancer guideline (PDF page in brackets)
IN_GUIDELINES = [
    "How often should follow up visits be done after breast cancer treatment?",          # p21
    "When is genetic testing for BRCA1/2 recommended?",                                   # p25
    "At what age should screening start for BRCA mutation carriers?",                     # p25
    "Is routine breast MRI needed before breast conserving surgery?",                     # p8
    "Which type of biopsy is preferred to confirm breast cancer?",                        # p8
    "What is the treatment for DCIS (ductal carcinoma in situ)?",                         # p10
    "What radiotherapy dose is used for painful bone metastasis from breast cancer?",     # p24
    "What is the incidence of breast cancer in rural and urban India?",                   # p3
]

# 2 questions that are NOT in the guidelines -> should say "not covered"
NOT_IN_GUIDELINES = [
    "Who won the cricket World Cup?",
    "What is the best phone to buy under 20000 rupees?",
]


def main():
    load_index()
    rows = []
    for question in IN_GUIDELINES + NOT_IN_GUIDELINES:
        for method in ["vector", "keyword"]:
            result = answer_question(question, method)
            sources = "; ".join(f"{s['file']} p.{s['page']}" for s in result["sources"])
            rows.append({"question": question, "method": method,
                         "answer": result["answer"], "sources": sources})
            print(f"[{method:7}] {question}\n          -> {result['answer'][:100]}\n")

    # utf-8-sig so the file opens correctly in Excel
    with open("results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "method", "answer", "sources"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows to results.csv")


if __name__ == "__main__":
    main()
