# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Cross-platform file locking helpers."""

from __future__ import annotations

import importlib
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol, cast

from .common import consume

__all__ = ["file_lock"]


class _FcntlModule(Protocol):
    LOCK_EX: int
    LOCK_UN: int

    def flock(self, fd: int, operation: int) -> None: ...


class _MsvcrtModule(Protocol):
    LK_LOCK: int
    LK_UNLCK: int

    def locking(self, fd: int, mode: int, size: int) -> None: ...


def _import_optional(name: str) -> object | None:
    try:  # pragma: no cover - platform dependent
        return importlib.import_module(name)
    except ImportError:  # pragma: no cover - platform dependent
        return None


fcntl_module = cast("_FcntlModule | None", _import_optional("fcntl"))
msvcrt_module = cast("_MsvcrtModule | None", _import_optional("msvcrt"))


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Best-effort file lock usable across platforms."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl_module:
        with path.open("a+b") as handle:
            fcntl_module.flock(handle.fileno(), fcntl_module.LOCK_EX)
            try:
                yield
            finally:
                fcntl_module.flock(handle.fileno(), fcntl_module.LOCK_UN)
        return
    if msvcrt_module:
        handle = path.open("a+b")
        try:
            while True:
                try:
                    msvcrt_module.locking(handle.fileno(), msvcrt_module.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
            yield
        finally:
            consume(handle.seek(0))
            try:
                msvcrt_module.locking(handle.fileno(), msvcrt_module.LK_UNLCK, 1)
            finally:
                handle.close()
        return
    handle = path.open("a+b")
    try:
        yield
    finally:
        handle.close()
