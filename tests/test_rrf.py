import pytest
from src.retrieval.rrf import reciprocal_rank_fusion


def test_rrf_scoring_order():
    list_dense = [{"id": "doc1", "text": "A"}, {"id": "doc2", "text": "B"}, {"id": "doc3", "text": "C"}]
    list_sparse = [{"id": "doc2", "text": "B"}, {"id": "doc1", "text": "A"}, {"id": "doc4", "text": "D"}]

    fused = reciprocal_rank_fusion([list_dense, list_sparse], k=60)

    # Both doc1 and doc2 appear in top 2 in both lists, so they must be at the top
    top_ids = [fused[0]["id"], fused[1]["id"]]
    assert "doc1" in top_ids
    assert "doc2" in top_ids
    assert "rrf_score" in fused[0]
    assert fused[0]["rrf_score"] >= fused[1]["rrf_score"]


def test_rrf_prioritizes_intersecting_items():
    list1 = [{"id": "docA"}, {"id": "docB"}]
    list2 = [{"id": "docB"}, {"id": "docC"}]
    fused = reciprocal_rank_fusion([list1, list2], k=60)

    # docB is at rank 2 in list1 and rank 1 in list2
    # docA is rank 1 in list1 only
    # score(docB) = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.03252
    # score(docA) = 1/(60+1) = 1/61 = 0.01639
    assert fused[0]["id"] == "docB"
    assert fused[1]["id"] == "docA"
    assert fused[2]["id"] == "docC"


def test_rrf_empty_lists():
    assert reciprocal_rank_fusion([], k=60) == []
    assert reciprocal_rank_fusion([[]], k=60) == []
