import pytest
from src.retrieval.context_reorder import reorder_lost_in_the_middle


def test_reorder_lost_in_the_middle_u_shape():
    # Input sorted by relevance descending: rank 1, rank 2, rank 3, rank 4, rank 5
    items = ["rank1", "rank2", "rank3", "rank4", "rank5"]
    reordered = reorder_lost_in_the_middle(items)

    # Rank 1 must be at index 0 (start)
    assert reordered[0] == "rank1"
    # Rank 2 must be at the very end
    assert reordered[-1] == "rank2"
    # All items preserved
    assert set(reordered) == set(items)


def test_reorder_small_lists():
    assert reorder_lost_in_the_middle([]) == []
    assert reorder_lost_in_the_middle(["r1"]) == ["r1"]
    assert reorder_lost_in_the_middle(["r1", "r2"]) == ["r1", "r2"]
