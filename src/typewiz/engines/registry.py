# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Engine registry and discovery for builtin and plugin-provided type checkers.

This module provides the engine registry system that discovers, loads, and
manages type checker engines. It handles both builtin engines (mypy, pyright)
and plugin-provided engines via entry points, providing a unified interface
for engine resolution and metadata queries.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from functools import lru_cache
from importlib import metadata
from typing import TYPE_CHECKING, Final, cast

from typewiz.core.model_types import LogComponent
from typewiz.core.type_aliases import EngineName
from typewiz.logging import structured_extra

from .builtin.mypy import MypyEngine
from .builtin.pyright import PyrightEngine

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from .base import BaseEngine

logger: logging.Logger = logging.getLogger("typewiz.engine.registry")


def _is_engine_like(value: object) -> bool:
    """Check if an object conforms to the BaseEngine protocol.

    Verifies that the object has the required attributes (name as str) and
    methods (run, fingerprint_targets as callables) to be used as an engine.

    Args:
        value: Object to check for engine conformance.

    Returns:
        bool: True if the object appears to be a valid BaseEngine instance.
    """
    if value is None:
        return False
    name = getattr(value, "name", None)
    run = getattr(value, "run", None)
    fingerprint = getattr(value, "fingerprint_targets", None)
    return isinstance(name, str) and callable(run) and callable(fingerprint)


ENTRY_POINT_GROUP: Final = "typewiz.engines"


def _engine_name(value: str) -> EngineName:
    """Convert a string to an EngineName type alias.

    Args:
        value: String identifier for the engine.

    Returns:
        EngineName: Typed engine name.
    """
    return EngineName(value)


@lru_cache
def builtin_engines() -> dict[EngineName, BaseEngine]:
    """Get the dictionary of builtin type checker engines.

    Returns a cached mapping of builtin engines (pyright and mypy) by name.
    The result is cached to avoid recreating engine instances.

    Returns:
        dict[EngineName, BaseEngine]: Mapping of engine names to instances.
    """
    engines: list[BaseEngine] = [PyrightEngine(), MypyEngine()]
    return {_engine_name(engine.name): engine for engine in engines}


def _instantiate_engine(obj: object, *, source: str) -> BaseEngine:
    """Convert an entry point object into a BaseEngine instance.

    Handles both class-based and instance-based entry points. If the object is
    a class or callable without a run method, it will be invoked as a factory.
    The result is validated to ensure it conforms to the BaseEngine protocol.

    Args:
        obj: The loaded entry point object (class or instance).
        source: Entry point name for error messages.

    Returns:
        BaseEngine: Validated engine instance.

    Raises:
        TypeError: If the object cannot be converted to a valid engine.
    """
    candidate = obj

    if inspect.isclass(candidate) or (callable(candidate) and not hasattr(candidate, "run")):
        factory = cast("Callable[[], object]", candidate)
        candidate = factory()

    if not _is_engine_like(candidate):
        message = f"Entry point '{source}' did not provide a valid engine instance"
        raise TypeError(message)

    return cast("BaseEngine", candidate)


@lru_cache
def entrypoint_engines() -> dict[EngineName, BaseEngine]:
    """Discover and load type checker engines from entry points.

    Searches for plugins registered under the 'typewiz.engines' entry point
    group, loads them, and validates them as BaseEngine instances. Failed
    loads are logged but don't cause the entire discovery to fail.

    Returns:
        dict[EngineName, BaseEngine]: Mapping of plugin engine names to instances,
            sorted alphabetically by name.
    """
    engines: dict[EngineName, BaseEngine] = {}
    try:
        eps = metadata.entry_points()
    except Exception as exc:  # pragma: no cover - guarded importlib behaviour
        logger.debug(
            "Failed to load entry points: %s",
            exc,
            extra=structured_extra(component=LogComponent.ENGINE),
        )
        return engines
    for entry_point in eps.select(group=ENTRY_POINT_GROUP):
        try:
            loaded = entry_point.load()
            engine = _instantiate_engine(loaded, source=entry_point.name)
        except Exception as exc:  # pragma: no cover - plugin misconfiguration
            logger.debug(
                "Failed to load engine entry point '%s': %s",
                entry_point.name,
                exc,
                extra=structured_extra(component=LogComponent.ENGINE, tool=entry_point.name),
            )
            continue
        name = getattr(engine, "name", None)
        if not isinstance(name, str) or not name:
            continue
        engines[_engine_name(name)] = engine
    return dict(sorted(engines.items()))


def engine_map() -> dict[EngineName, BaseEngine]:
    """Get the complete mapping of all available engines.

    Combines builtin engines with plugin-provided engines from entry points.
    Plugin engines can override builtin engines if they use the same name.

    Returns:
        dict[EngineName, BaseEngine]: Complete mapping of all engine names to instances.
    """
    mapping = dict(builtin_engines())
    mapping.update(entrypoint_engines())
    return mapping


def resolve_engines(names: Iterable[str | EngineName] | None) -> list[BaseEngine]:
    """Resolve engine names to their BaseEngine instances.

    Given a list of engine names, looks them up in the engine registry and
    returns the corresponding instances. If names is None or empty, returns
    all available engines.

    Args:
        names: Iterable of engine names to resolve, or None for all engines.

    Returns:
        list[BaseEngine]: List of resolved engine instances in the order specified.

    Raises:
        ValueError: If any requested engine name is not found in the registry.
    """
    mapping = engine_map()
    if not names:
        return list(mapping.values())
    resolved: list[BaseEngine] = []
    for name in names:
        engine_name = _engine_name(str(name))
        if engine_name not in mapping:
            message = f"Unknown engine '{name}'"
            raise ValueError(message)
        resolved.append(mapping[engine_name])
    return resolved


@dataclass(slots=True, frozen=True)
class EngineDescriptor:
    """Metadata description of a discovered type checker engine.

    Contains identifying information about an engine including its name,
    implementation location, and origin (builtin vs plugin).

    Attributes:
        name: Unique engine identifier.
        module: Python module where the engine is defined.
        qualified_name: Fully qualified class/object name.
        origin: Source of the engine ("builtin" or "entry_point").
    """

    name: EngineName
    module: str
    qualified_name: str
    origin: str


def describe_engines() -> list[EngineDescriptor]:
    """Get metadata for all discovered engines.

    Returns descriptive information about all available engines including
    their names, implementation details, and whether they're builtin or
    from plugins.

    Returns:
        list[EngineDescriptor]: Sorted list of engine metadata, ordered by name.
    """
    mapping = engine_map()
    entrypoints = entrypoint_engines()
    descriptors: list[EngineDescriptor] = []
    for name, engine in mapping.items():
        cls = engine.__class__
        origin = "entry_point" if name in entrypoints else "builtin"
        descriptors.append(
            EngineDescriptor(
                name=name,
                module=cls.__module__,
                qualified_name=cls.__qualname__,
                origin=origin,
            ),
        )
    descriptors.sort(key=lambda desc: str(desc.name))
    return descriptors
