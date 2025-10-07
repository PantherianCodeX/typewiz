from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Sequence

from .types import Diagnostic

CACHE_FILENAME = ".typewiz_cache.json"


@dataclass(slots=True)
class CacheEntry:
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[dict]
    file_hashes: dict[str, dict[str, object]]
    profile: str | None = None
    config_file: str | None = None
    plugin_args: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    overrides: list[dict[str, object]] = field(default_factory=list)


@dataclass(slots=True)
class CachedRun:
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    profile: str | None = None
    config_file: Path | None = None
    plugin_args: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    overrides: list[dict[str, object]] = field(default_factory=list)


class EngineCache:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.path = project_root / CACHE_FILENAME
        self._entries: Dict[str, CacheEntry] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for key, entry in payload.get("entries", {}).items():
            diagnostics = entry.get("diagnostics", [])
            file_hashes = entry.get("file_hashes", {})
            command = entry.get("command", [])
            exit_code = entry.get("exit_code")
            duration_ms = entry.get("duration_ms")
            plugin_args = entry.get("plugin_args", [])
            include = entry.get("include", [])
            exclude = entry.get("exclude", [])
            profile = entry.get("profile")
            config_file = entry.get("config_file")
            overrides = entry.get("overrides", [])
            if (
                isinstance(diagnostics, list)
                and isinstance(file_hashes, dict)
                and isinstance(command, list)
                and isinstance(exit_code, int)
                and isinstance(duration_ms, (int, float))
                and isinstance(plugin_args, list)
                and isinstance(include, list)
                and isinstance(exclude, list)
                and (isinstance(overrides, list))
            ):
                self._entries[key] = CacheEntry(
                    command=[str(arg) for arg in command],
                    exit_code=exit_code,
                    duration_ms=float(duration_ms),
                    diagnostics=diagnostics,
                    file_hashes=file_hashes,
                    profile=str(profile) if isinstance(profile, str) and profile.strip() else None,
                    config_file=str(config_file) if isinstance(config_file, str) and config_file.strip() else None,
                    plugin_args=[str(arg) for arg in plugin_args],
                    include=[str(item) for item in include],
                    exclude=[str(item) for item in exclude],
                    overrides=[dict(item) for item in overrides if isinstance(item, dict)],
                )

    def save(self) -> None:
        if not self._dirty:
            return
        payload = {
            "entries": {
                key: {
                    "command": entry.command,
                    "exit_code": entry.exit_code,
                    "duration_ms": entry.duration_ms,
                    "diagnostics": entry.diagnostics,
                    "file_hashes": entry.file_hashes,
                    "profile": entry.profile,
                    "config_file": entry.config_file,
                    "plugin_args": entry.plugin_args,
                    "include": entry.include,
                    "exclude": entry.exclude,
                    "overrides": entry.overrides,
                }
                for key, entry in sorted(self._entries.items())
            }
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._dirty = False

    def key_for(self, engine: str, mode: str, paths: Sequence[str], flags: Sequence[str]) -> str:
        path_part = ",".join(sorted({str(item) for item in paths}))
        flag_part = ",".join(str(flag) for flag in flags)
        return f"{engine}:{mode}:{path_part}:{flag_part}"

    def get(self, key: str, file_hashes: dict[str, dict[str, object]]) -> CachedRun | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry.file_hashes != file_hashes:
            return None

        diagnostics: list[Diagnostic] = []
        for raw in entry.diagnostics:
            path_str = raw.get("path")
            if not isinstance(path_str, str):
                continue
            diagnostics.append(
                Diagnostic(
                    tool=str(raw.get("tool", "")),
                    severity=str(raw.get("severity", "error")),
                    path=Path(path_str),
                    line=int(raw.get("line", 0)),
                    column=int(raw.get("column", 0)),
                    code=raw.get("code"),
                    message=str(raw.get("message", "")),
                    raw=dict(raw.get("raw", {})),
                )
            )
        diagnostics.sort(key=lambda diag: (str(diag.path), diag.line, diag.column))
        return CachedRun(
            command=list(entry.command),
            exit_code=entry.exit_code,
            duration_ms=entry.duration_ms,
            diagnostics=diagnostics,
            profile=entry.profile,
            config_file=Path(entry.config_file) if entry.config_file else None,
            plugin_args=list(entry.plugin_args),
            include=list(entry.include),
            exclude=list(entry.exclude),
            overrides=[dict(item) for item in entry.overrides],
        )

    def update(
        self,
        key: str,
        file_hashes: dict[str, dict[str, object]],
        command: Sequence[str],
        exit_code: int,
        duration_ms: float,
        diagnostics: Sequence[Diagnostic],
        *,
        profile: str | None,
        config_file: Path | None,
        plugin_args: Sequence[str],
        include: Sequence[str],
        exclude: Sequence[str],
        overrides: Sequence[dict[str, object]],
    ) -> None:
        canonical_diags = sorted(diagnostics, key=lambda diag: (str(diag.path), diag.line, diag.column))
        self._entries[key] = CacheEntry(
            command=[str(arg) for arg in command],
            exit_code=exit_code,
            duration_ms=duration_ms,
            diagnostics=[
                {
                    "tool": diag.tool,
                    "severity": diag.severity,
                    "path": str(diag.path),
                    "line": diag.line,
                    "column": diag.column,
                    "code": diag.code,
                    "message": diag.message,
                    "raw": diag.raw,
                }
                for diag in canonical_diags
            ],
            file_hashes=file_hashes,
            profile=profile,
            config_file=config_file.as_posix() if config_file else None,
            plugin_args=[str(arg) for arg in plugin_args],
            include=[str(path) for path in include],
            exclude=[str(path) for path in exclude],
            overrides=[dict(item) for item in overrides],
        )
        self._dirty = True


def collect_file_hashes(project_root: Path, paths: Iterable[str]) -> dict[str, dict[str, object]]:
    hashes: dict[str, dict[str, object]] = {}
    seen: set[str] = set()
    project_root = project_root.resolve()
    for path_str in sorted({path for path in paths if path}):
        raw_path = Path(path_str)
        absolute = raw_path if raw_path.is_absolute() else (project_root / raw_path)
        absolute = absolute.resolve()
        if absolute.is_dir():
            candidates = set()
            for pattern in ("*.py", "*.pyi"):
                candidates.update(absolute.rglob(pattern))
            for child in sorted(candidates):
                key = _relative_key(project_root, child)
                if key in seen:
                    continue
                hashes[key] = _fingerprint(child)
                seen.add(key)
        elif absolute.exists():
            key = _relative_key(project_root, absolute)
            if key in seen:
                continue
            hashes[key] = _fingerprint(absolute)
            seen.add(key)
    return dict(sorted(hashes.items()))


def _relative_key(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _fingerprint(path: Path) -> dict[str, object]:
    try:
        stat = path.stat()
        hasher = hashlib.blake2b(digest_size=16)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                if not chunk:
                    break
                hasher.update(chunk)
        return {"hash": hasher.hexdigest(), "mtime": int(stat.st_mtime_ns), "size": stat.st_size}
    except FileNotFoundError:
        return {"missing": True}
    except OSError:
        return {"unreadable": True}
