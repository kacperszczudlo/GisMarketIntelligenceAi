from unittest.mock import MagicMock
import pytest
from src.retrieval.hybrid_search import HybridSearchEngine


def test_hybrid_search_combines_dense_and_sparse():
    mock_dense = MagicMock()
    mock_dense.search.return_value = [
        {"id": "doc1", "content": "Modernizacja BDOT500", "score": 0.85},
        {"id": "doc2", "content": "Wymagania formalne", "score": 0.70},
    ]

    mock_sparse = MagicMock()
    mock_sparse.search.return_value = [
        {"id": "doc2", "content": "Wymagania formalne", "score": 1.5},
        {"id": "doc3", "content": "Format plików .str", "score": 1.2},
    ]

    engine = HybridSearchEngine(
        dense_retriever=mock_dense,
        sparse_retriever=mock_sparse,
        k=60,
    )

    results = engine.search("BDOT500 i format .str", top_k=3)

    assert len(results) == 3
    # doc2 appeared in both dense and sparse, so RRF must score it highest!
    assert results[0]["id"] == "doc2"
    assert "rrf_score" in results[0]
    assert results[0]["rrf_score"] > results[1]["rrf_score"]
