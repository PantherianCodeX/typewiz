# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Iterable
from functools import lru_cache
from importlib import metadata
from typing import cast

from .base import BaseEngine
from .mypy import MypyEngine
from .pyright import PyrightEngine

logger: logging.Logger = logging.getLogger("typewiz.engine.registry")


def _is_engine_like(value: object) -> bool:
    """Return True if ``value`` looks like a ``BaseEngine`` instance."""

    if value is None:
        return False
    name = getattr(value, "name", None)
    run = getattr(value, "run", None)
    fingerprint = getattr(value, "fingerprint_targets", None)
    return isinstance(name, str) and callable(run) and callable(fingerprint)


ENTRY_POINT_GROUP = "typewiz.engines"


@lru_cache
def builtin_engines() -> dict[str, BaseEngine]:
    engines: list[BaseEngine] = [PyrightEngine(), MypyEngine()]
    return {engine.name: engine for engine in engines}


def _instantiate_engine(obj: object, *, source: str) -> BaseEngine:
    """Best-effort coercion of an entry point object into a ``BaseEngine`` instance."""

    candidate = obj

    if inspect.isclass(candidate) or (callable(candidate) and not hasattr(candidate, "run")):
        factory = cast(Callable[[], object], candidate)
        candidate = factory()

    if not _is_engine_like(candidate):
        message = f"Entry point '{source}' did not provide a valid engine instance"
        raise TypeError(message)

    return cast(BaseEngine, candidate)


@lru_cache
def entrypoint_engines() -> dict[str, BaseEngine]:
    engines: dict[str, BaseEngine] = {}
    try:
        eps = metadata.entry_points()
    except Exception:  # pragma: no cover - guarded importlib behaviour
        return engines
    for entry_point in eps.select(group=ENTRY_POINT_GROUP):
        try:
            loaded = entry_point.load()
            engine = _instantiate_engine(loaded, source=entry_point.name)
        except Exception as exc:  # pragma: no cover - plugin misconfiguration
            logger.debug("Failed to load engine entry point '%s': %s", entry_point.name, exc)
            continue
        name = getattr(engine, "name", None)
        if not isinstance(name, str) or not name:
            continue
        engines[name] = engine
    return dict(sorted(engines.items()))


def engine_map() -> dict[str, BaseEngine]:
    mapping = dict(builtin_engines())
    mapping.update(entrypoint_engines())
    return mapping


def resolve_engines(names: Iterable[str] | None) -> list[BaseEngine]:
    mapping = engine_map()
    if not names:
        return list(mapping.values())
    resolved: list[BaseEngine] = []
    for name in names:
        if name not in mapping:
            message = f"Unknown engine '{name}'"
            raise ValueError(message)
        resolved.append(mapping[name])
    return resolved
