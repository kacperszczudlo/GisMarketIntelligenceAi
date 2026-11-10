from typing import List
import pytest
from src.retrieval.context_reorder import reorder_lost_in_the_middle


def test_should_reorder_five_ranked_items_into_u_shaped_distribution() -> None:
    # Arrange
    items = ["rank1", "rank2", "rank3", "rank4", "rank5"]

    # Act
    reordered = reorder_lost_in_the_middle(items)

    # Assert
    assert reordered == ["rank1", "rank3", "rank5", "rank4", "rank2"]


def test_should_reorder_four_ranked_items_placing_top_two_at_edges() -> None:
    # Arrange
    items = ["rank1", "rank2", "rank3", "rank4"]

    # Act
    reordered = reorder_lost_in_the_middle(items)

    # Assert
    assert reordered == ["rank1", "rank3", "rank4", "rank2"]


@pytest.mark.parametrize(
    ("input_items", "expected_output"),
    [
        ([], []),
        (["r1"], ["r1"]),
        (["r1", "r2"], ["r1", "r2"]),
    ],
    ids=["empty_list", "single_element", "two_elements"],
)
def test_should_return_unchanged_sequence_when_length_is_at_most_two(
    input_items: List[str],
    expected_output: List[str],
) -> None:
    # Arrange & Act
    result = reorder_lost_in_the_middle(input_items)

    # Assert
    assert result == expected_output


def test_should_not_mutate_original_input_list() -> None:
    # Arrange
    original = ["rank1", "rank2", "rank3"]
    snapshot = list(original)

    # Act
    _ = reorder_lost_in_the_middle(original)

    # Assert
    assert original == snapshot
