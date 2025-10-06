from __future__ import annotations

from functools import lru_cache
from importlib import metadata
from typing import Dict, Iterable, List

from .base import TypingRunner
from .mypy import MypyRunner
from .pyright import PyrightRunner


@lru_cache()
def builtin_runners() -> Dict[str, TypingRunner]:
    return {runner.name: runner for runner in (PyrightRunner(), MypyRunner())}


@lru_cache()
def entrypoint_runners() -> Dict[str, TypingRunner]:
    runners: Dict[str, TypingRunner] = {}
    try:
        eps = metadata.entry_points()
    except Exception:  # pragma: no cover - defensive for old importlib
        return runners

    for entry_point in eps.select(group="pytc.plugins"):
        runner = entry_point.load()
        name = getattr(runner, "name", None)
        if not name:
            continue
        runners[name] = runner
    return runners


def runner_map() -> Dict[str, TypingRunner]:
    mapping = dict(builtin_runners())
    mapping.update(entrypoint_runners())
    return mapping


def resolve_runners(names: Iterable[str] | None) -> List[TypingRunner]:
    mapping = runner_map()
    if not names:
        return list(mapping.values())
    result: List[TypingRunner] = []
    for name in names:
        if name not in mapping:
            raise ValueError(f"Unknown runner '{name}'")
        result.append(mapping[name])
    return result
