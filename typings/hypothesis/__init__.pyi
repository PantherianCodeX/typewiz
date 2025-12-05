# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from collections.abc import Callable, Sequence
from enum import Enum
from typing import Any, ParamSpec, TypeVar

from .strategies import SearchStrategy

_P = ParamSpec("_P")
_T = TypeVar("_T")

class HealthCheck(Enum):
    function_scoped_fixture = ...
    too_slow = ...

def assume(condition: bool) -> None: ...
def given(
    *strategies: SearchStrategy[Any],
    **named_strategies: SearchStrategy[Any],
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
def settings(
    *,
    suppress_health_check: Sequence[HealthCheck] | None = ...,
    max_examples: int | None = ...,
    deadline: int | None = ...,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

__all__ = ["HealthCheck", "assume", "given", "settings"]
