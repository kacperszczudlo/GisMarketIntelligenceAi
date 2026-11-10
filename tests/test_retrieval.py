from typing import Any
import pytest
from pytest_mock import MockerFixture
from src.indexing.embedder import EXPECTED_EMBEDDING_DIM, BgeM3Embedder
from src.retrieval.dense_search import DenseRetriever
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.parent_resolver import ParentNodeResolver
from src.retrieval.sparse_search import SparseRetriever

DEFAULT_RRF_K = 60
TOP_K_THREE = 3


def test_should_combine_dense_and_sparse_candidates_via_rrf_in_hybrid_search(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_dense = mocker.MagicMock(spec=DenseRetriever)
    mock_dense.search.return_value = [
        {"id": "doc1", "content": "Modernizacja BDOT500", "score": 0.85},
        {"id": "doc2", "content": "Wymagania formalne", "score": 0.70},
    ]

    mock_sparse = mocker.MagicMock(spec=SparseRetriever)
    mock_sparse.search.return_value = [
        {"id": "doc2", "content": "Wymagania formalne", "score": 1.5},
        {"id": "doc3", "content": "Format plików .str", "score": 1.2},
    ]

    engine = HybridSearchEngine(
        dense_retriever=mock_dense,
        sparse_retriever=mock_sparse,
        k=DEFAULT_RRF_K,
    )

    # Act
    results = engine.search("BDOT500 i format .str", top_k=TOP_K_THREE, procurement_id="ocds-123")

    # Assert
    assert len(results) == TOP_K_THREE
    assert results[0]["id"] == "doc2"
    assert results[0]["rrf_score"] > results[1]["rrf_score"]
    mock_dense.search.assert_called_once_with(
        "BDOT500 i format .str",
        top_k=TOP_K_THREE,
        parent_id=None,
        procurement_id="ocds-123",
    )
    mock_sparse.search.assert_called_once_with(
        "BDOT500 i format .str",
        top_k=TOP_K_THREE,
        parent_id=None,
        procurement_id="ocds-123",
    )


def test_should_compute_cosine_similarity_and_fallback_when_scoped_dense_search_is_empty(
    mocker: MockerFixture,
    mock_db_cursor: Any,
) -> None:
    # Arrange
    mock_embedder = mocker.MagicMock(spec=BgeM3Embedder)
    mock_embedder.embed_query.return_value = [1.0] + [0.0] * (EXPECTED_EMBEDDING_DIM - 1)
    mock_db_cursor.fetchall.side_effect = [
        [],
        [("chunk-1", "parent-1", 0, "Wymóg formatu .str", {"section_title": "OPZ"}, 0.15)],
    ]
    retriever = DenseRetriever(embedder=mock_embedder)

    # Act
    results = retriever.search(
        "format .str",
        top_k=5,
        parent_id="parent-1",
        procurement_id="ocds-148610-niepolomice",
    )

    # Assert
    assert len(results) == 1
    assert results[0]["id"] == "chunk-1"
    assert results[0]["parent_id"] == "parent-1"
    assert results[0]["distance"] == pytest.approx(0.15)
    assert results[0]["score"] == pytest.approx(0.85)
    assert results[0]["retrieval_mode"] == "dense"
    assert mock_db_cursor.execute.call_count == 2


def test_should_sanitize_natural_query_and_execute_tsvector_search_in_sparse_retriever(
    mock_db_cursor: Any,
) -> None:
    # Arrange
    mock_db_cursor.fetchall.side_effect = [
        [],
        [("chunk-2", "parent-2", 1, "Modernizacja bazy GESUT", {}, 2.4)],
    ]
    retriever = SparseRetriever()

    # Act
    tsquery = retriever._prepare_tsquery_terms("Modernizacja? bazy! GESUT (2026) a")
    results = retriever.search(
        "Modernizacja? bazy! GESUT",
        top_k=5,
        parent_id="parent-2",
        procurement_id="ocds-148610-niepolomice",
    )

    # Assert
    assert tsquery == "Modernizacja | bazy | GESUT | 2026"
    assert len(results) == 1
    assert results[0]["id"] == "chunk-2"
    assert results[0]["score"] == pytest.approx(2.4)
    assert results[0]["retrieval_mode"] == "sparse"
    assert mock_db_cursor.execute.call_count == 2


def test_should_return_empty_list_when_sparse_query_has_no_valid_terms_or_db_fails(
    mock_db_cursor: Any,
) -> None:
    # Arrange
    retriever = SparseRetriever()
    mock_db_cursor.execute.side_effect = RuntimeError("tsquery syntax error")

    # Act
    empty_terms_res = retriever.search("?! .")
    failed_db_res = retriever.search("poprawne zapytanie")

    # Assert
    assert empty_terms_res == []
    assert failed_db_res == []


def test_should_deduplicate_parents_and_preserve_highest_score_order_in_parent_resolver(
    mock_db_cursor: Any,
) -> None:
    # Arrange
    resolver = ParentNodeResolver()
    child_candidates = [
        {"id": "c0", "parent_id": None, "cross_encoder_score": 0.99},
        {"id": "c1", "parent_id": "p1", "cross_encoder_score": 0.92},
        {"id": "c2", "parent_id": "p2", "cross_encoder_score": 0.85},
        {"id": "c3", "parent_id": "p1", "cross_encoder_score": 0.97},
    ]
    mock_db_cursor.fetchall.return_value = [
        ("p2", "att-1", "Rozdział II", 120, "Treść rozdziału II"),
        ("p1", "att-1", "Rozdział I", 150, "Treść rozdziału I"),
    ]

    # Act
    resolved = resolver.resolve(child_candidates)

    # Assert
    assert [r["id"] for r in resolved] == ["p1", "p2"]
    assert resolved[0]["score"] == pytest.approx(0.97)
    assert resolved[1]["score"] == pytest.approx(0.85)
    assert resolver.resolve([]) == []
    assert resolver.resolve([{"id": "c0", "parent_id": None}]) == []
