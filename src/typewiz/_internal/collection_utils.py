# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence


def dedupe_preserve[T: Hashable](values: Iterable[T]) -> list[T]:
    """Return items in order, dropping subsequent duplicates.

    Args:
        values: Iterable of hashable items whose first occurrence should be
            preserved.

    Returns:
        A list containing the first appearance of each unique value, ordered by
        the original traversal.
    """
    seen: set[T] = set()
    result: list[T] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def merge_preserve[T: Hashable](base: Iterable[T], addition: Sequence[T]) -> list[T]:
    """Combine iterables while preserving the first occurrence order.

    Args:
        base: Initial iterable that establishes the output order.
        addition: Additional values that should be appended only if they have
            not already appeared in ``base``.

    Returns:
        A list starting with ``base`` followed by unseen elements from
        ``addition``.
    """
    result = list(base)
    seen = set(result)
    for value in addition:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
