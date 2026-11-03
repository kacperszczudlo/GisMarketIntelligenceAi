from typing import Any, Dict, List


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Merges multiple ranked lists of documents using Reciprocal Rank Fusion (RRF).

    Formula: RRF_Score(d) = sum_{m in M} (1.0 / (k + rank_m(d)))
    where k is a smoothing constant (strictly 60 as per system specs).
    """
    scores: Dict[str, float] = {}
    doc_lookup: Dict[str, Dict[str, Any]] = {}

    for ranked_list in ranked_lists:
        for rank_0, doc in enumerate(ranked_list):
            doc_id = str(doc.get("id"))
            if not doc_id:
                continue

            rank_1 = rank_0 + 1
            rrf_contribution = 1.0 / (k + rank_1)
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf_contribution

            if doc_id not in doc_lookup:
                doc_lookup[doc_id] = dict(doc)

    # Sort documents by descending combined RRF score
    sorted_doc_ids = sorted(scores.keys(), key=lambda d_id: scores[d_id], reverse=True)

    results: List[Dict[str, Any]] = []
    for d_id in sorted_doc_ids:
        merged = doc_lookup[d_id]
        merged["rrf_score"] = scores[d_id]
        results.append(merged)

    return results
