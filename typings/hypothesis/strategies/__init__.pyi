# ruff: noqa: UP047
# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")

class SearchStrategy(Generic[T]):  # noqa: UP046
    def map(self, function: Callable[[T], U]) -> SearchStrategy[U]: ...
    def filter(self, predicate: Callable[[T], bool]) -> SearchStrategy[T]: ...

def builds(
    callable: Callable[..., T],
    /,
    *args: SearchStrategy[Any],
    **kwargs: SearchStrategy[Any],
) -> SearchStrategy[T]: ...  # noqa: UP047
def composite(function: Callable[..., T]) -> Callable[..., SearchStrategy[T]]: ...  # noqa: UP047
def fixed_dictionaries(
    mapping: Mapping[str, SearchStrategy[T]],
) -> SearchStrategy[dict[str, T]]: ...  # noqa: UP047
def from_regex(pattern: str, *, fullmatch: bool = ...) -> SearchStrategy[str]: ...
def dictionaries(
    keys: SearchStrategy[T],
    values: SearchStrategy[U],
    *,
    min_size: int | None = ...,
    max_size: int | None = ...,
    dict_class: type[dict[T, U]] | None = ...,
) -> SearchStrategy[dict[T, U]]: ...  # noqa: UP047
def floats(
    *,
    min_value: float | None = ...,
    max_value: float | None = ...,
    allow_nan: bool = ...,
    allow_infinity: bool = ...,
) -> SearchStrategy[float]: ...
def integers(
    *,
    min_value: int | None = ...,
    max_value: int | None = ...,
) -> SearchStrategy[int]: ...
def lists(
    strategy: SearchStrategy[T],
    *,
    min_size: int | None = ...,
    max_size: int | None = ...,
    unique: bool = ...,
) -> SearchStrategy[list[T]]: ...  # noqa: UP047
def just(value: T) -> SearchStrategy[T]: ...  # noqa: UP047
def sampled_from(values: Sequence[T]) -> SearchStrategy[T]: ...  # noqa: UP047
def text(
    *,
    min_size: int | None = ...,
    max_size: int | None = ...,
) -> SearchStrategy[str]: ...

__all__ = [
    "SearchStrategy",
    "builds",
    "composite",
    "dictionaries",
    "floats",
    "fixed_dictionaries",
    "from_regex",
    "integers",
    "just",
    "lists",
    "sampled_from",
    "text",
]
