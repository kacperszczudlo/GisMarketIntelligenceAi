from unittest.mock import MagicMock, patch
import pytest
from src.retrieval.reranker import CrossEncoderReranker


def test_cross_encoder_selects_most_relevant():
    reranker = CrossEncoderReranker()
    query = "Wymagania dla bazy BDOT500 w układzie PL-2000"
    candidates = [
        {"id": "1", "content": "Termin wpłaty wadium upływa w piątek."},
        {"id": "2", "content": "Modernizacja bazy danych obiektów topograficznych BDOT500 w układzie PL-2000 pas 7."},
    ]

    mock_model = MagicMock()
    # Mock scores: doc1 -> 0.1, doc2 -> 0.95
    mock_model.predict.return_value = [0.10, 0.95]

    with patch.object(reranker, "_get_model", return_value=mock_model):
        results = reranker.rerank(query, candidates, top_n=1)

        assert len(results) == 1
        assert results[0]["id"] == "2"
        assert results[0]["cross_encoder_score"] == 0.95


def test_cross_encoder_empty_candidates():
    reranker = CrossEncoderReranker()
    assert reranker.rerank("jakieś zapytanie", [], top_n=5) == []
