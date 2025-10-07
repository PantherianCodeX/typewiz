from __future__ import annotations

from functools import lru_cache
from importlib import metadata
from typing import Dict, Iterable, List

from .base import BaseEngine
from .mypy import MypyEngine
from .pyright import PyrightEngine

ENTRY_POINT_GROUP = "typewiz.engines"


@lru_cache()
def builtin_engines() -> Dict[str, BaseEngine]:
    engines: List[BaseEngine] = [PyrightEngine(), MypyEngine()]
    return {engine.name: engine for engine in engines}


@lru_cache()
def entrypoint_engines() -> Dict[str, BaseEngine]:
    engines: Dict[str, BaseEngine] = {}
    try:
        eps = metadata.entry_points()
    except Exception:  # pragma: no cover
        return engines
    for entry_point in eps.select(group=ENTRY_POINT_GROUP):
        engine = entry_point.load()
        name = getattr(engine, "name", None)
        if not name:
            continue
        engines[name] = engine
    return dict(sorted(engines.items()))


def engine_map() -> Dict[str, BaseEngine]:
    mapping = dict(builtin_engines())
    mapping.update(entrypoint_engines())
    return mapping


def resolve_engines(names: Iterable[str] | None) -> List[BaseEngine]:
    mapping = engine_map()
    if not names:
        return list(mapping.values())
    resolved: List[BaseEngine] = []
    for name in names:
        if name not in mapping:
            raise ValueError(f"Unknown engine '{name}'")
        resolved.append(mapping[name])
    return resolved
