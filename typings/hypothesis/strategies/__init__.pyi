# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Generic, TypeVar

_T = TypeVar("_T")
_U = TypeVar("_U")

class SearchStrategy(Generic[_T]):  # noqa: UP046  # JUSTIFIED: public stub mirrors upstream generic class name
    def map(self, function: Callable[[_T], _U]) -> SearchStrategy[_U]: ...
    def filter(self, predicate: Callable[[_T], bool]) -> SearchStrategy[_T]: ...

def builds(
    factory: Callable[..., _T],
    /,
    *args: SearchStrategy[Any],
    **kwargs: SearchStrategy[Any],
) -> SearchStrategy[_T]: ...
def composite(function: Callable[..., _T]) -> Callable[..., SearchStrategy[_T]]: ...
def fixed_dictionaries(
    mapping: Mapping[str, SearchStrategy[_T]],
) -> SearchStrategy[dict[str, _T]]: ...
def from_regex(pattern: str, *, fullmatch: bool = ...) -> SearchStrategy[str]: ...
def dictionaries(
    keys: SearchStrategy[_T],
    values: SearchStrategy[_U],
    *,
    min_size: int | None = ...,
    max_size: int | None = ...,
    dict_class: type[dict[_T, _U]] | None = ...,
) -> SearchStrategy[dict[_T, _U]]: ...
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
    strategy: SearchStrategy[_T],
    *,
    min_size: int | None = ...,
    max_size: int | None = ...,
    unique: bool = ...,
) -> SearchStrategy[list[_T]]: ...
def just(value: _T) -> SearchStrategy[_T]: ...
def sampled_from(values: Sequence[_T]) -> SearchStrategy[_T]: ...
def text(
    *,
    min_size: int | None = ...,
    max_size: int | None = ...,
) -> SearchStrategy[str]: ...
def one_of(*strategies: SearchStrategy[Any]) -> SearchStrategy[Any]: ...
def none() -> SearchStrategy[None]: ...

__all__ = [
    "SearchStrategy",
    "builds",
    "composite",
    "dictionaries",
    "fixed_dictionaries",
    "floats",
    "from_regex",
    "integers",
    "just",
    "lists",
    "none",
    "one_of",
    "sampled_from",
    "text",
]
