# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence


def dedupe_preserve[T: Hashable](values: Iterable[T]) -> list[T]:
    """Return items in order, dropping subsequent duplicates."""

    seen: set[T] = set()
    result: list[T] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def merge_preserve[T: Hashable](base: Iterable[T], addition: Sequence[T]) -> list[T]:
    """Combine iterables while preserving the first occurrence order."""

    result = list(base)
    seen = set(result)
    for value in addition:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
