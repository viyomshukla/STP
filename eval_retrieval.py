"""Measures how good the SEARCH step is (no AI needed, no API key needed).

For each question we know (by reading the PDF) which page holds the answer.
We run both search methods and check where that page appears in the top 4 results.

Metrics (all between 0 and 1, higher is better):
  Hit@1    : is the very first result the correct page?
  Recall@4 : what fraction of the correct pages appear somewhere in the top 4?
  MRR      : 1 / (position of the first correct result). 1st -> 1.0, 2nd -> 0.5, 3rd -> 0.33 ...
  nDCG@4   : rewards correct results more when they are higher up the list
             (1.0 = all correct results are at the very top).

Run it with:  python eval_retrieval.py      -> prints a table and saves retrieval_eval.csv
"""
import csv
import math

from app.search import _store, load_index, search

K = 4  # we evaluate the same top 4 results that are sent to the AI

# (question, pages that contain the answer)  -- labelled by reading Breast_Cancer_ICMR_clinical.pdf
LABELLED_QUESTIONS = [
    ("How often should follow up visits be done after breast cancer treatment?", [21]),
    ("When is BRCA1/2 genetic testing recommended?", [25]),
    ("At what age should screening start for BRCA mutation carriers?", [25]),
    ("Who should be referred for a genetic risk assessment?", [25]),
    ("Is routine breast MRI needed before breast conserving surgery?", [8]),
    ("Which type of biopsy is preferred to confirm breast cancer?", [8]),
    ("What tests are done for white nipple discharge in a woman who is not pregnant?", [8]),
    ("What is the treatment for DCIS (ductal carcinoma in situ)?", [10]),
    ("What radiotherapy dose is used for painful bone metastasis?", [24]),
    ("What radiotherapy dose is recommended for brain metastasis?", [24]),
    ("What is the incidence of breast cancer in rural and urban India?", [3]),
    ("What is the hypofractionated radiotherapy schedule for the breast?", [20]),
    ("What is the role of Ki67 testing in breast cancer?", [16, 17]),
    ("How long should adjuvant trastuzumab be given for HER2 positive breast cancer?", [18]),
    ("What is the standard adjuvant hormone therapy for premenopausal women?", [18]),
    ("What hormone therapy is used for metastatic breast cancer in premenopausal women?", [23]),
    ("How often is zoledronic acid given for bone metastases?", [23]),
    ("When is a bone scan needed in the staging work up?", [6]),
    ("What is the standard adjuvant chemotherapy for node positive breast cancer?", [17]),
    ("Which assay is recommended for HER2neu IHC testing?", [16]),
    ("When is a HER2 IHC result interpreted as score 3 positive?", [16]),
    ("What are the research issues for breast cancer in India?", [27]),
]


def evaluate(question, relevant_pages, method):
    results = search(question, method, k=K)
    # 1 if this result comes from a correct page, else 0
    hits = [1 if r["page"] in relevant_pages else 0 for r in results]

    hit_at_1 = hits[0]
    found_pages = {r["page"] for r in results if r["page"] in relevant_pages}
    recall = len(found_pages) / len(relevant_pages)
    mrr = next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0)

    # DCG: each correct result is worth 1 / log2(position + 1)
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    # Ideal DCG: all correct chunks placed at the very top
    n_relevant_chunks = sum(1 for c in _store["chunks"] if c["page"] in relevant_pages)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(K, n_relevant_chunks)))
    ndcg = dcg / ideal

    return {"hit@1": hit_at_1, "recall@4": recall, "mrr": mrr, "ndcg@4": ndcg,
            "top_pages": [r["page"] for r in results]}


def main():
    load_index()
    rows = []
    totals = {m: {"hit@1": 0, "recall@4": 0, "mrr": 0, "ndcg@4": 0} for m in ["vector", "keyword"]}

    for question, pages in LABELLED_QUESTIONS:
        for method in ["vector", "keyword"]:
            s = evaluate(question, pages, method)
            for metric in totals[method]:
                totals[method][metric] += s[metric]
            rows.append({"question": question, "method": method, "correct_pages": pages,
                         "top4_pages": s["top_pages"], "hit@1": s["hit@1"],
                         "recall@4": round(s["recall@4"], 2), "mrr": round(s["mrr"], 2),
                         "ndcg@4": round(s["ndcg@4"], 2)})

    # Per-question table
    print(f"{'Question':<62} {'Method':<8} {'Correct':<9} {'Top 4 pages':<18} Hit@1  nDCG")
    for r in rows:
        print(f"{r['question'][:60]:<62} {r['method']:<8} {str(r['correct_pages']):<9} "
              f"{str(r['top4_pages']):<18} {r['hit@1']:<6} {r['ndcg@4']}")

    # Averages
    n = len(LABELLED_QUESTIONS)
    print(f"\nAVERAGE over {n} questions (top {K} results)")
    print(f"{'Method':<10}{'Hit@1':>8}{'Recall@4':>10}{'MRR':>8}{'nDCG@4':>9}")
    for method, t in totals.items():
        print(f"{method:<10}{t['hit@1']/n:>8.2f}{t['recall@4']/n:>10.2f}"
              f"{t['mrr']/n:>8.2f}{t['ndcg@4']/n:>9.2f}")

    with open("retrieval_eval.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("\nSaved per-question results to retrieval_eval.csv")


if __name__ == "__main__":
    main()
