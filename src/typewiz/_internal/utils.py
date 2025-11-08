# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import importlib
import json
import logging
import subprocess
import sys
import time
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, Protocol, cast

if TYPE_CHECKING:
    from ..core.type_aliases import Command, ToolName

logger: logging.Logger = logging.getLogger("typewiz")

# JSON typing helpers
# A recursive JSON value used for parsing engine outputs safely.
type JSONValue = str | int | float | bool | None | dict[str, "JSONValue"] | list["JSONValue"]
type JSONMapping = dict[str, JSONValue]
type JSONList = list[JSONValue]
type RootMarker = Literal["typewiz.toml", ".typewiz.toml", "pyproject.toml"]

ROOT_MARKERS: Final[tuple[RootMarker, RootMarker, RootMarker]] = (
    "typewiz.toml",
    ".typewiz.toml",
    "pyproject.toml",
)


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

_HAS_FCNTL: Final[bool] = fcntl_module is not None
_HAS_MSVCRT: Final[bool] = msvcrt_module is not None


def consume(value: object | None) -> None:
    """Explicitly mark a value as intentionally unused."""

    _ = value


@dataclass(slots=True)
class CommandOutput:
    args: Command
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float


def run_command(
    args: Iterable[str],
    cwd: Path | None = None,
    *,
    allowed: set[str] | None = None,
) -> CommandOutput:
    """Run a subprocess safely and return its captured output.

    Security guardrails:
    - Requires an iterable of string arguments; never uses ``shell=True``.
    - Optionally enforces an allowlist for the executable (first arg) via ``allowed``.
    """
    argv: Command = list(args)
    if not argv:
        raise ValueError
    if not all(a for a in argv):
        raise TypeError
    executable = argv[0]
    if allowed is not None and executable not in allowed:
        raise ValueError
    start = time.perf_counter()
    logger.debug("Executing command: %s", " ".join(argv))
    completed = subprocess.run(  # noqa: S603 - command arguments provided by caller
        argv,
        check=False,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    duration_ms = (time.perf_counter() - start) * 1000
    if completed.returncode != 0:
        logger.warning("Command failed (exit=%s): %s", completed.returncode, " ".join(argv))
    return CommandOutput(
        args=argv,
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
        duration_ms=duration_ms,
    )


def _safe_version_from_output(output: str) -> str | None:
    text = (output or "").strip()
    if not text:
        return None
    # Grab the first token that looks like a version (digits and dots)
    for token in text.replace("(", " ").replace(")", " ").split():
        if any(ch.isdigit() for ch in token) and any(ch == "." for ch in token):
            return token.strip()
    # Fallback to the entire line
    return text.splitlines()[0].strip() if text else None


def detect_tool_versions(tools: Sequence[str | ToolName]) -> dict[str, str]:
    """Return a mapping of tool -> version by invoking their version commands.

    Supports built-ins: pyright, mypy. Ignores unknown tools.
    Best-effort: failures are skipped.
    """
    versions: dict[str, str] = {}
    seen: set[str] = set()
    for tool in tools:
        name = str(tool).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            if name == "pyright":
                out = run_command(["pyright", "--version"], allowed={"pyright"}).stdout
                ver = _safe_version_from_output(out)
                if ver:
                    versions[name] = ver
            elif name == "mypy":
                py = python_executable()
                out = run_command([py, "-m", "mypy", "--version"], allowed={py}).stdout
                ver = _safe_version_from_output(out)
                if ver:
                    versions[name] = ver
        except Exception as exc:
            # Ignore errors — version detection is optional
            logger.debug("Failed to detect version for %s: %s", name, exc)
            continue
    return versions


def require_json(payload: str, fallback: str | None = None) -> JSONMapping:
    data_str = payload.strip() or (fallback or "")
    if not data_str:
        message = "Expected JSON output but received empty string"
        raise ValueError(message)
    return cast(JSONMapping, json.loads(data_str))


def as_mapping(value: object) -> JSONMapping:
    return cast(JSONMapping, value) if isinstance(value, dict) else {}


def as_list(value: object) -> JSONList:
    return cast(JSONList, value) if isinstance(value, list) else []


def as_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def as_int(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def resolve_project_root(start: Path | None = None) -> Path:
    base = (start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent

    checked: list[Path] = []
    for candidate in (base, *base.parents):
        checked.append(candidate)
        for marker in ROOT_MARKERS:
            if (candidate / marker).exists():
                return candidate

    if start is not None:
        if not base.exists():
            message = f"Provided project root {start} does not exist."
            raise FileNotFoundError(message)
        logger.debug(
            "No project markers found; using provided path %s as project root",
            base,
        )
        return base

    logger.debug(
        "No project markers found in %s; using current working directory as root",
        ", ".join(str(path) for path in checked),
    )
    return base


def normalise_enums_for_json(value: object) -> JSONValue:
    """Recursively convert Enum keys/values to their string payloads for JSON serialisation."""

    def _convert(obj: object) -> JSONValue:
        if isinstance(obj, Enum):
            return cast(JSONValue, obj.value)
        if isinstance(obj, dict):
            mapping_obj = cast(dict[object, object], obj)
            result: dict[str, JSONValue] = {}
            for key, raw_val in mapping_obj.items():
                if isinstance(key, Enum):
                    norm_key: str = str(key.value)
                elif isinstance(key, str):
                    norm_key = key
                else:
                    norm_key = str(key)
                result[norm_key] = _convert(raw_val)
            return cast(JSONValue, result)
        if isinstance(obj, list):
            list_obj = cast(list[object], obj)
            return cast(JSONValue, [_convert(item) for item in list_obj])
        if isinstance(obj, tuple):
            tuple_obj = cast(tuple[object, ...], obj)
            return cast(JSONValue, [_convert(item) for item in tuple_obj])
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return cast(JSONValue, obj)
        return cast(JSONValue, str(obj))

    return _convert(value)


def _contains_python(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_file() and path.suffix in {".py", ".pyi"}:
        return True
    if not path.is_dir():
        return False
    for child in path.iterdir():
        if child.is_file() and child.suffix in {".py", ".pyi"}:
            return True
        if child.is_dir() and _contains_python(child):
            return True
    return False


def default_full_paths(root: Path) -> list[str]:
    candidates = [
        "typewiz",
        "apps",
        "packages",
        "config",
        "infra",
        "tests",
    ]
    paths: list[str] = []
    for item in candidates:
        full = root / item
        if _contains_python(full):
            paths.append(item)
    if not paths:
        paths.append(".")
    return paths


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Best-effort file lock usable across platforms."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if _HAS_FCNTL and fcntl_module:
        with path.open("a+b") as handle:
            fcntl_module.flock(handle.fileno(), fcntl_module.LOCK_EX)
            try:
                yield
            finally:
                fcntl_module.flock(handle.fileno(), fcntl_module.LOCK_UN)
        return
    if _HAS_MSVCRT and msvcrt_module:
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


def python_executable() -> str:
    return sys.executable
