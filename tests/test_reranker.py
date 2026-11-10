import numpy as np
import pytest
from pytest_mock import MockerFixture
from src.retrieval.reranker import CrossEncoderReranker

SCORE_LOW = 0.10
SCORE_HIGH = 0.95
TOP_N_ONE = 1


def test_should_select_most_relevant_candidate_using_cross_encoder_scores(
    mocker: MockerFixture,
) -> None:
    # Arrange
    reranker = CrossEncoderReranker()
    query = "Wymagania dla bazy BDOT500 w układzie PL-2000"
    candidates = [
        {"id": "1", "content": "Termin wpłaty wadium upływa w piątek."},
        {"id": "2", "content": "Modernizacja bazy danych obiektów topograficznych BDOT500 w układzie PL-2000 pas 7."},
    ]

    mock_model = mocker.MagicMock()
    mock_model.predict.return_value = np.array([SCORE_LOW, SCORE_HIGH], dtype=np.float32)
    mocker.patch.object(reranker, "_get_model", return_value=mock_model)

    # Act
    results = reranker.rerank(query, candidates, top_n=TOP_N_ONE)

    # Assert
    assert len(results) == TOP_N_ONE
    assert results[0]["id"] == "2"
    assert results[0]["cross_encoder_score"] == pytest.approx(SCORE_HIGH)


def test_should_return_empty_list_without_loading_model_when_candidates_are_empty(
    mocker: MockerFixture,
) -> None:
    # Arrange
    reranker = CrossEncoderReranker()
    spy_get_model = mocker.spy(reranker, "_get_model")

    # Act
    results = reranker.rerank("jakieś zapytanie", [], top_n=5)

    # Assert
    assert results == []
    spy_get_model.assert_not_called()


def test_should_handle_single_scalar_prediction_score_from_cross_encoder(
    mocker: MockerFixture,
) -> None:
    # Arrange
    reranker = CrossEncoderReranker()
    candidates = [{"id": "single", "content": "Pojedynczy dokument SWZ"}]

    mock_model = mocker.MagicMock()
    mock_model.predict.return_value = 0.88
    mocker.patch.object(reranker, "_get_model", return_value=mock_model)

    # Act
    results = reranker.rerank("zapytanie", candidates, top_n=3)

    # Assert
    assert len(results) == 1
    assert results[0]["id"] == "single"
    assert results[0]["cross_encoder_score"] == pytest.approx(0.88)


def test_should_lazily_instantiate_cross_encoder_model_once(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    import sys

    fake_st_module = mocker.MagicMock()
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st_module)
    reranker = CrossEncoderReranker(model_name="BAAI/bge-reranker-v2-m3", device="cpu")

    # Act
    first = reranker._get_model()
    second = reranker._get_model()

    # Assert
    assert first is second
    fake_st_module.CrossEncoder.assert_called_once_with("BAAI/bge-reranker-v2-m3", device="cpu")

