from typing import Any, Dict, List
import pytest
from src.retrieval.rrf import reciprocal_rank_fusion

DEFAULT_RRF_K = 60
CUSTOM_RRF_K = 10


def test_should_boost_documents_appearing_in_both_dense_and_sparse_rankings() -> None:
    # Arrange
    list_dense = [
        {"id": "doc1", "text": "A"},
        {"id": "doc2", "text": "B"},
        {"id": "doc3", "text": "C"},
    ]
    list_sparse = [
        {"id": "doc2", "text": "B"},
        {"id": "doc1", "text": "A"},
        {"id": "doc4", "text": "D"},
    ]

    # Act
    fused = reciprocal_rank_fusion([list_dense, list_sparse], k=DEFAULT_RRF_K)

    # Assert
    top_ids = {fused[0]["id"], fused[1]["id"]}
    assert top_ids == {"doc1", "doc2"}
    assert fused[0]["rrf_score"] == pytest.approx(1.0 / 61 + 1.0 / 62)
    assert fused[0]["rrf_score"] >= fused[1]["rrf_score"] > fused[2]["rrf_score"]


def test_should_prioritize_intersecting_document_over_single_list_rank_one() -> None:
    # Arrange
    list1 = [{"id": "docA"}, {"id": "docB"}]
    list2 = [{"id": "docB"}, {"id": "docC"}]

    # Act
    fused = reciprocal_rank_fusion([list1, list2], k=DEFAULT_RRF_K)

    # Assert
    expected_doc_b_score = (1.0 / (DEFAULT_RRF_K + 2)) + (1.0 / (DEFAULT_RRF_K + 1))
    expected_doc_a_score = 1.0 / (DEFAULT_RRF_K + 1)
    assert [d["id"] for d in fused] == ["docB", "docA", "docC"]
    assert fused[0]["rrf_score"] == pytest.approx(expected_doc_b_score)
    assert fused[1]["rrf_score"] == pytest.approx(expected_doc_a_score)


@pytest.mark.parametrize(
    "empty_input",
    [
        [],
        [[]],
        [[], []],
    ],
    ids=["no_lists", "single_empty_list", "multiple_empty_lists"],
)
def test_should_return_empty_list_when_rankings_are_empty(
    empty_input: List[List[Dict[str, Any]]],
) -> None:
    # Arrange & Act
    result = reciprocal_rank_fusion(empty_input, k=DEFAULT_RRF_K)

    # Assert
    assert result == []


def test_should_skip_records_with_empty_identifier_and_preserve_metadata() -> None:
    # Arrange
    ranked = [
        [{"id": "", "content": "Ignored"}, {"id": "valid-1", "content": "Preserved", "extra": 42}],
    ]

    # Act
    fused = reciprocal_rank_fusion(ranked, k=CUSTOM_RRF_K)

    # Assert
    assert len(fused) == 1
    assert fused[0]["id"] == "valid-1"
    assert fused[0]["extra"] == 42
    assert fused[0]["rrf_score"] == pytest.approx(1.0 / (CUSTOM_RRF_K + 2))
