from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, cast, TypedDict, Any

from .types import Diagnostic

CACHE_FILENAME = ".typewiz_cache.json"


@dataclass(slots=True)
class CacheEntry:
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[dict[str, object]]
    file_hashes: dict[str, dict[str, object]]
    profile: str | None = None
    config_file: str | None = None
    plugin_args: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    overrides: list[dict[str, object]] = field(default_factory=list)
    category_mapping: dict[str, list[str]] = field(default_factory=dict)


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
    category_mapping: dict[str, list[str]] = field(default_factory=dict)


def _normalise_category_mapping(mapping: Mapping[str, Sequence[str]] | None) -> dict[str, list[str]]:
    if not mapping:
        return {}
    normalised: dict[str, list[str]] = {}
    for key in sorted(mapping):
        raw_values = mapping[key]
        key_str = key.strip()
        if not key_str:
            continue
        seen: set[str] = set()
        values: list[str] = []
        for raw in raw_values:
            candidate = raw.strip()
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            values.append(candidate)
        normalised[key_str] = values
    return normalised


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
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        class _DiagJson(TypedDict, total=False):
            tool: str
            severity: str
            path: str
            line: int
            column: int
            code: str
            message: str
            raw: Dict[str, Any]

        class _EntryJson(TypedDict, total=False):
            command: list[str]
            exit_code: int
            duration_ms: float
            diagnostics: list[_DiagJson]
            file_hashes: dict[str, dict[str, object]]
            profile: str | None
            config_file: str | None
            plugin_args: list[str]
            include: list[str]
            exclude: list[str]
            overrides: list[dict[str, object]]
            category_mapping: dict[str, list[str]]

        class _Payload(TypedDict, total=False):
            entries: dict[str, _EntryJson]

        payload = cast(_Payload, raw)
        entries = cast(dict[str, _EntryJson], payload.get("entries", {}))
        for key, entry in entries.items():
            diagnostics_any = cast(list[dict[str, object]], entry.get("diagnostics", []))
            file_hashes_any = cast(dict[str, dict[str, object]], entry.get("file_hashes", {}))
            command_any = cast(list[str], entry.get("command", []))
            exit_code = entry.get("exit_code", 0)
            duration_ms = entry.get("duration_ms", 0.0)
            plugin_args_any = cast(list[str], entry.get("plugin_args", []))
            include_any = cast(list[str], entry.get("include", []))
            exclude_any = cast(list[str], entry.get("exclude", []))
            profile = entry.get("profile")
            config_file = entry.get("config_file")
            overrides_any = cast(list[dict[str, object]], entry.get("overrides", []))
            category_mapping_any = cast(dict[str, list[str]], entry.get("category_mapping", {}))
            # Defensive normalization and typing for JSON-loaded structures
            command_list: list[str] = [str(a) for a in command_any]
            plugin_args_list: list[str] = [str(a) for a in plugin_args_any]
            include_list: list[str] = [str(i) for i in include_any]
            exclude_list: list[str] = [str(i) for i in exclude_any]
            overrides_list: list[dict[str, object]] = []
            for i in overrides_any:
                if isinstance(i, dict):
                    overrides_list.append({str(k): v for k, v in i.items()})
            file_hashes_map: dict[str, dict[str, object]] = {k: dict(v) for k, v in file_hashes_any.items()}
            diagnostics_list: list[dict[str, object]] = [dict(d) for d in diagnostics_any]
            exit_code_int = int(exit_code)
            duration_val = float(duration_ms)
            self._entries[key] = CacheEntry(
                command=command_list,
                exit_code=exit_code_int,
                duration_ms=duration_val,
                diagnostics=diagnostics_list,
                file_hashes=file_hashes_map,
                profile=str(profile) if isinstance(profile, str) and profile.strip() else None,
                config_file=str(config_file) if isinstance(config_file, str) and config_file.strip() else None,
                plugin_args=plugin_args_list,
                include=include_list,
                exclude=exclude_list,
                overrides=overrides_list,
                category_mapping=_normalise_category_mapping(
                    cast(Mapping[str, Sequence[str]] | None, category_mapping_any)
                ),
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
                    "category_mapping": entry.category_mapping,
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
            path_val = raw.get("path")
            if not isinstance(path_val, str):
                continue
            # Normalize numeric fields defensively
            line_val = raw.get("line", 0)
            col_val = raw.get("column", 0)
            if isinstance(line_val, int):
                line_num = line_val
            elif isinstance(line_val, (str, bytes, bytearray)):
                try:
                    line_num = int(line_val)
                except ValueError:
                    line_num = 0
            else:
                line_num = 0
            if isinstance(col_val, int):
                col_num = col_val
            elif isinstance(col_val, (str, bytes, bytearray)):
                try:
                    col_num = int(col_val)
                except ValueError:
                    col_num = 0
            else:
                col_num = 0

            code_val = raw.get("code")
            code_str = str(code_val) if isinstance(code_val, str) else None
            raw_val = raw.get("raw", {})
            raw_dict: dict[str, object] = raw_val if isinstance(raw_val, dict) else {}

            diagnostics.append(
                Diagnostic(
                    tool=str(raw.get("tool", "")),
                    severity=str(raw.get("severity", "error")),
                    path=Path(path_val),
                    line=line_num,
                    column=col_num,
                    code=code_str,
                    message=str(raw.get("message", "")),
                    raw=raw_dict,
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
            category_mapping={k: list(v) for k, v in entry.category_mapping.items()},
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
        category_mapping: Mapping[str, Sequence[str]] | None,
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
            category_mapping=_normalise_category_mapping(category_mapping),
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
            candidates: set[Path] = set()
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
