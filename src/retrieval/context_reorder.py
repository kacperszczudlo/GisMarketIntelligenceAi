from typing import List, TypeVar

T = TypeVar("T")


def reorder_lost_in_the_middle(items: List[T]) -> List[T]:
    """Reorders candidate chunks into a U-shaped distribution to counteract the 'Lost in the Middle' effect.

    Rank 1 is placed at the start, Rank 2 at the end, Rank 3 next to start, Rank 4 next to end,
    with the least relevant items clustered in the middle of the context window.
    """
    if len(items) <= 2:
        return list(items)

    left_items = [items[i] for i in range(0, len(items), 2)]
    right_items = [items[i] for i in range(1, len(items), 2)]

    return left_items + list(reversed(right_items))
