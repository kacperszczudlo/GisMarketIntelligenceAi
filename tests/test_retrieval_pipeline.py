from pytest_mock import MockerFixture
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.parent_resolver import ParentNodeResolver
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.reranker import CrossEncoderReranker

TOP_CANDIDATES = 10
TOP_K = 3


def test_should_execute_four_stage_retrieval_pipeline_and_apply_u_shape_reordering(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_hybrid = mocker.MagicMock(spec=HybridSearchEngine)
    mock_hybrid.search.return_value = [
        {"id": "c1", "parent_id": "p1", "content": "Wymóg formatu .str dla bazy EWMAPA", "rrf_score": 0.03},
        {"id": "c2", "parent_id": "p2", "content": "Kryterium ceny 60%", "rrf_score": 0.02},
        {"id": "c3", "parent_id": "p3", "content": "Termin wykonania zamówienia", "rrf_score": 0.01},
    ]

    mock_reranker = mocker.MagicMock(spec=CrossEncoderReranker)
    mock_reranker.rerank.return_value = [
        {"id": "c1", "parent_id": "p1", "content": "Wymóg formatu .str", "cross_encoder_score": 0.95},
        {"id": "c3", "parent_id": "p3", "content": "Termin wykonania", "cross_encoder_score": 0.80},
        {"id": "c2", "parent_id": "p2", "content": "Kryterium ceny", "cross_encoder_score": 0.60},
    ]

    mock_resolver = mocker.MagicMock(spec=ParentNodeResolver)
    mock_resolver.resolve.return_value = [
        {"id": "p1", "section_title": "Rozdział III: OPZ", "content": "Pełna treść OPZ...", "score": 0.95},
        {"id": "p3", "section_title": "Rozdział V: Terminy", "content": "Pełna treść terminów...", "score": 0.80},
        {"id": "p2", "section_title": "Rozdział IV: Kryteria", "content": "Pełna treść kryteriów...", "score": 0.60},
    ]

    pipeline = RetrievalPipeline(
        hybrid_engine=mock_hybrid,
        reranker=mock_reranker,
        parent_resolver=mock_resolver,
    )
    query = "Jakie są wymagania dotyczące formatu plików .str?"

    # Act
    results = pipeline.retrieve(
        query,
        top_candidates=TOP_CANDIDATES,
        top_k=TOP_K,
        procurement_id="ocds-148610-niepolomice",
        reorder_context=True,
    )

    # Assert
    assert [r["id"] for r in results] == ["p1", "p2", "p3"]
    mock_hybrid.search.assert_called_once_with(
        query,
        top_k=TOP_CANDIDATES,
        parent_id=None,
        procurement_id="ocds-148610-niepolomice",
    )
    mock_reranker.rerank.assert_called_once_with(query, mock_hybrid.search.return_value, top_n=TOP_K)
    mock_resolver.resolve.assert_called_once_with(mock_reranker.rerank.return_value)


def test_should_return_empty_list_and_skip_reranker_when_hybrid_search_finds_nothing(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_hybrid = mocker.MagicMock(spec=HybridSearchEngine)
    mock_hybrid.search.return_value = []
    mock_reranker = mocker.MagicMock(spec=CrossEncoderReranker)
    mock_resolver = mocker.MagicMock(spec=ParentNodeResolver)

    pipeline = RetrievalPipeline(
        hybrid_engine=mock_hybrid,
        reranker=mock_reranker,
        parent_resolver=mock_resolver,
    )

    # Act
    results = pipeline.retrieve("Pytanie bez odpowiedzi")

    # Assert
    assert results == []
    mock_reranker.rerank.assert_not_called()
    mock_resolver.resolve.assert_not_called()


def test_should_preserve_original_reranked_order_when_reorder_context_is_false(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_hybrid = mocker.MagicMock(spec=HybridSearchEngine)
    mock_hybrid.search.return_value = [{"id": "c1", "parent_id": "p1"}]
    mock_reranker = mocker.MagicMock(spec=CrossEncoderReranker)
    mock_reranker.rerank.return_value = [{"id": "c1", "parent_id": "p1"}]
    mock_resolver = mocker.MagicMock(spec=ParentNodeResolver)
    expected_parents = [
        {"id": "p1", "content": "A"},
        {"id": "p2", "content": "B"},
        {"id": "p3", "content": "C"},
    ]
    mock_resolver.resolve.return_value = expected_parents

    pipeline = RetrievalPipeline(
        hybrid_engine=mock_hybrid,
        reranker=mock_reranker,
        parent_resolver=mock_resolver,
    )

    # Act
    results = pipeline.retrieve("Zapytanie", reorder_context=False)

    # Assert
    assert results == expected_parents

