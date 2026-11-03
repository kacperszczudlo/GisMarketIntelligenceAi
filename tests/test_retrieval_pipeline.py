from unittest.mock import MagicMock, patch
import pytest
from src.retrieval.pipeline import RetrievalPipeline


def test_retrieval_pipeline_end_to_end_flow():
    mock_hybrid = MagicMock()
    mock_hybrid.search.return_value = [
        {"id": "c1", "parent_id": "p1", "content": "Wymóg formatu .str dla bazy EWMAPA", "rrf_score": 0.03},
        {"id": "c2", "parent_id": "p2", "content": "Kryterium ceny 60%", "rrf_score": 0.02},
        {"id": "c3", "parent_id": "p3", "content": "Termin wykonania zamówienia", "rrf_score": 0.01},
    ]

    mock_reranker = MagicMock()
    # Let reranker order: c1 (0.95), c3 (0.80), c2 (0.60)
    mock_reranker.rerank.return_value = [
        {"id": "c1", "parent_id": "p1", "content": "Wymóg formatu .str", "cross_encoder_score": 0.95},
        {"id": "c3", "parent_id": "p3", "content": "Termin wykonania", "cross_encoder_score": 0.80},
        {"id": "c2", "parent_id": "p2", "content": "Kryterium ceny", "cross_encoder_score": 0.60},
    ]

    mock_resolver = MagicMock()
    mock_resolver.resolve.return_value = [
        {"id": "p1", "section_title": "Rozdział III: Opis Przedmiotu Zamówienia", "content": "Pełna treść OPZ...", "score": 0.95},
        {"id": "p3", "section_title": "Rozdział V: Terminy", "content": "Pełna treść terminów...", "score": 0.80},
        {"id": "p2", "section_title": "Rozdział IV: Kryteria Oceny", "content": "Pełna treść kryteriów...", "score": 0.60},
    ]

    pipeline = RetrievalPipeline(
        hybrid_engine=mock_hybrid,
        reranker=mock_reranker,
        parent_resolver=mock_resolver,
    )

    query = "Jakie są wymagania dotyczące formatu plików .str?"
    results = pipeline.retrieve(query, top_candidates=10, top_k=3, reorder_context=True)

    assert len(results) == 3
    # With 3 items in U-shape: [Rank 1, Rank 3, Rank 2]
    # Rank 1 (p1) at index 0
    assert results[0]["id"] == "p1"
    # Rank 2 (p3) at index -1
    assert results[-1]["id"] == "p3"
    # Rank 3 (p2) in middle (index 1)
    assert results[1]["id"] == "p2"


def test_retrieval_pipeline_empty_hybrid_results():
    mock_hybrid = MagicMock()
    mock_hybrid.search.return_value = []

    pipeline = RetrievalPipeline(hybrid_engine=mock_hybrid)
    results = pipeline.retrieve("Pytanie bez odpowiedzi")
    assert results == []
