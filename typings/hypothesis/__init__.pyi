# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import Enum
from typing import Any, ParamSpec, TypeVar

from .strategies import SearchStrategy

P = ParamSpec("P")
T = TypeVar("T")

class HealthCheck(Enum):
    function_scoped_fixture = ...
    too_slow = ...

def assume(condition: bool) -> None: ...
def given(
    *strategies: SearchStrategy[Any],
    **named_strategies: SearchStrategy[Any],
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...
def settings(
    *,
    suppress_health_check: Sequence[HealthCheck] | None = ...,
    max_examples: int | None = ...,
    deadline: int | None = ...,
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...

__all__ = ["HealthCheck", "assume", "given", "settings"]
