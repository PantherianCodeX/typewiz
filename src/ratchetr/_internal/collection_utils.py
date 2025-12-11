# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper functions for deterministic collection operations."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence
from typing import TypeVar

T = TypeVar("T", bound=Hashable)


def dedupe_preserve(values: Iterable[T]) -> list[T]:
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


def merge_preserve(base: Iterable[T], addition: Sequence[T]) -> list[T]:
    """Combine iterables while preserving the first occurrence order.

    Args:
        base: Initial iterable that establishes the output order.
        addition: Additional values that should be appended only if they have
            not already appeared in ``base``.

    Returns:
        A list starting with `base`followed by unseen elements from
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
