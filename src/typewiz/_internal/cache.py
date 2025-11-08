# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, TypedDict, cast

from typewiz._internal.utils import JSONValue, consume, file_lock, normalise_enums_for_json

from ..category_utils import coerce_category_key
from ..core.model_types import SeverityLevel, clone_override_entries
from ..core.type_aliases import (
    CacheKey,
    CategoryKey,
    CategoryName,
    Command,
    PathKey,
    RelPath,
    ToolName,
)
from ..core.types import Diagnostic
from ..data_validation import coerce_int, coerce_object_list, coerce_str_list
from ..typed_manifest import ToolSummary

if TYPE_CHECKING:
    from ..core.model_types import (
        CategoryMapping,
        DiagnosticPayload,
        FileHashPayload,
        Mode,
        OverrideEntry,
    )


logger: logging.Logger = logging.getLogger("typewiz.cache")
CACHE_DIRNAME: Final[str] = ".typewiz_cache"
CACHE_FILENAME: Final[str] = "cache.json"
_HASH_WORKER_ENV: Final[str] = "TYPEWIZ_HASH_WORKERS"


def _default_list_str() -> list[str]:
    return []


def _default_list_relpath() -> list[RelPath]:
    return []


def _default_list_dict_obj() -> list[OverrideEntry]:
    return []


def _default_dict_str_liststr() -> CategoryMapping:
    return {}


@dataclass(slots=True)
class CacheEntry:
    command: Command
    exit_code: int
    duration_ms: float
    diagnostics: list[DiagnosticPayload]
    file_hashes: dict[PathKey, FileHashPayload]
    profile: str | None = None
    config_file: str | None = None
    plugin_args: list[str] = field(default_factory=_default_list_str)
    include: list[RelPath] = field(default_factory=_default_list_relpath)
    exclude: list[RelPath] = field(default_factory=_default_list_relpath)
    overrides: list[OverrideEntry] = field(default_factory=_default_list_dict_obj)
    category_mapping: CategoryMapping = field(default_factory=_default_dict_str_liststr)
    tool_summary: ToolSummary | None = None


@dataclass(slots=True)
class CachedRun:
    command: Command
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    profile: str | None = None
    config_file: Path | None = None
    plugin_args: list[str] = field(default_factory=_default_list_str)
    include: list[RelPath] = field(default_factory=_default_list_relpath)
    exclude: list[RelPath] = field(default_factory=_default_list_relpath)
    overrides: list[OverrideEntry] = field(default_factory=_default_list_dict_obj)
    category_mapping: CategoryMapping = field(default_factory=_default_dict_str_liststr)
    tool_summary: ToolSummary | None = None


def _resolve_hash_workers() -> int:
    raw = os.getenv(_HASH_WORKER_ENV)
    if raw is None:
        return 0
    value = raw.strip().lower()
    if not value:
        return 0
    if value == "auto":
        return max(1, os.cpu_count() or 1)
    try:
        parsed = int(value)
    except ValueError:
        logger.debug("Ignoring invalid %s=%s value", _HASH_WORKER_ENV, raw)
        return 0
    return max(0, parsed)


def _effective_hash_workers(value: int | Literal["auto"] | None) -> int:
    if value is None:
        return _resolve_hash_workers()
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "auto":
            return max(1, os.cpu_count() or 1)
        logger.warning("Unknown hash worker spec '%s'; falling back to defaults", value)
        return _resolve_hash_workers()
    return max(0, value)


def _compute_hashes(
    pending: Sequence[tuple[PathKey, Path]],
    workers: int,
) -> dict[PathKey, FileHashPayload]:
    if not pending:
        return {}
    if workers <= 1:
        return {key: _fingerprint(path) for key, path in pending}
    hashes: dict[PathKey, FileHashPayload] = {}
    max_workers = workers
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_fingerprint, path): key for key, path in pending}
        for future in as_completed(future_map):
            key = future_map[future]
            hashes[key] = future.result()
    return hashes


def _normalise_category_mapping(
    mapping: Mapping[CategoryKey, Sequence[str]]
    | Mapping[CategoryName, Sequence[str]]
    | Mapping[str, Sequence[str]]
    | None,
) -> CategoryMapping:
    if not mapping:
        return {}
    normalised: CategoryMapping = {}
    sorted_items = sorted(mapping.items(), key=lambda item: str(item[0]).strip())
    for raw_key, raw_values in sorted_items:
        category_key = coerce_category_key(raw_key)
        if category_key is None:
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
        normalised[category_key] = values
    return normalised


def _normalise_override_entry(raw: Mapping[str, object]) -> OverrideEntry:
    entry: OverrideEntry = {}
    path = raw.get("path")
    if isinstance(path, str) and path.strip():
        entry["path"] = path.strip()
    profile = raw.get("profile")
    if isinstance(profile, str) and profile.strip():
        entry["profile"] = profile.strip()
    plugin_args = coerce_str_list(raw.get("pluginArgs", []))
    if plugin_args:
        entry["pluginArgs"] = plugin_args
    include_paths = [
        RelPath(str(path)) for path in coerce_str_list(raw.get("include", [])) if str(path).strip()
    ]
    if include_paths:
        entry["include"] = include_paths
    exclude_paths = [
        RelPath(str(path)) for path in coerce_str_list(raw.get("exclude", [])) if str(path).strip()
    ]
    if exclude_paths:
        entry["exclude"] = exclude_paths
    return entry


def _normalise_diagnostic_payload(raw: Mapping[str, JSONValue]) -> DiagnosticPayload:
    payload: DiagnosticPayload = {}
    tool = raw.get("tool")
    if isinstance(tool, str) and tool:
        payload["tool"] = tool
    severity = raw.get("severity")
    if isinstance(severity, str) and severity:
        payload["severity"] = severity
    path_str = raw.get("path")
    if isinstance(path_str, str) and path_str:
        payload["path"] = path_str
    if "line" in raw:
        payload["line"] = coerce_int(raw.get("line"))
    if "column" in raw:
        payload["column"] = coerce_int(raw.get("column"))
    code = raw.get("code")
    if isinstance(code, str) and code:
        payload["code"] = code
    message = raw.get("message")
    if isinstance(message, str) and message:
        payload["message"] = message
    raw_payload = raw.get("raw")
    if isinstance(raw_payload, Mapping):
        raw_mapping = cast("Mapping[str, JSONValue]", raw_payload)
        payload["raw"] = {str(key): value for key, value in raw_mapping.items()}
    return payload


def _normalise_file_hash_payload(raw: Mapping[str, object]) -> FileHashPayload:
    payload: FileHashPayload = {}
    hash_val = raw.get("hash")
    if isinstance(hash_val, str) and hash_val:
        payload["hash"] = hash_val
    if "mtime" in raw:
        payload["mtime"] = coerce_int(raw.get("mtime"))
    if "size" in raw:
        payload["size"] = coerce_int(raw.get("size"))
    missing = raw.get("missing")
    if isinstance(missing, bool):
        payload["missing"] = missing
    unreadable = raw.get("unreadable")
    if isinstance(unreadable, bool):
        payload["unreadable"] = unreadable
    return payload


def fingerprint_path(path: Path) -> FileHashPayload:
    return _fingerprint(path)


class EngineCache:
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.path: Path = project_root / CACHE_DIRNAME / CACHE_FILENAME
        self._entries: dict[CacheKey, CacheEntry] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        class _EntryJson(TypedDict, total=False):
            command: list[str]
            exit_code: int
            duration_ms: float
            diagnostics: list[Mapping[str, object]]
            file_hashes: Mapping[str, Mapping[str, object]]
            profile: str | None
            config_file: str | None
            plugin_args: list[str]
            include: list[str]
            exclude: list[str]
            overrides: list[Mapping[str, object]]
            category_mapping: Mapping[str, Sequence[str]]
            tool_summary: dict[str, int]

        class _Payload(TypedDict, total=False):
            entries: dict[str, _EntryJson]

        payload = cast("_Payload", raw)
        payload_entries = payload.get("entries")
        entries: dict[str, _EntryJson] = payload_entries or {}
        for key_str, entry in entries.items():
            cache_key = CacheKey(key_str)
            diagnostics_any = entry.get("diagnostics", []) or []
            file_hashes_any = entry.get("file_hashes", {}) or {}
            command_any = entry.get("command", []) or []
            exit_code = entry.get("exit_code", 0)
            duration_ms = entry.get("duration_ms", 0.0)
            plugin_args_any = entry.get("plugin_args", []) or []
            include_any = entry.get("include", []) or []
            exclude_any = entry.get("exclude", []) or []
            profile = entry.get("profile")
            config_file = entry.get("config_file")
            overrides_any = entry.get("overrides", []) or []
            category_mapping_any = entry.get("category_mapping", {}) or {}
            tool_summary_any = entry.get("tool_summary")

            command_list: Command = [str(a) for a in command_any]
            plugin_args_list: list[str] = [str(a) for a in plugin_args_any]
            include_list: list[RelPath] = [RelPath(str(i)) for i in include_any]
            exclude_list: list[RelPath] = [RelPath(str(i)) for i in exclude_any]
            overrides_list: list[OverrideEntry] = [
                _normalise_override_entry(cast("Mapping[str, object]", override_raw))
                for override_raw in coerce_object_list(overrides_any)
                if isinstance(override_raw, Mapping)
            ]
            file_hashes_map: dict[PathKey, FileHashPayload] = {}
            file_hashes_mapping: Mapping[str, Mapping[str, object]] = file_hashes_any
            for hash_key, hash_payload in file_hashes_mapping.items():
                file_hashes_map[PathKey(hash_key)] = _normalise_file_hash_payload(hash_payload)
            diagnostics_list: list[DiagnosticPayload] = [
                _normalise_diagnostic_payload(cast("Mapping[str, JSONValue]", diag_raw))
                for diag_raw in coerce_object_list(diagnostics_any)
                if isinstance(diag_raw, Mapping)
            ]
            exit_code_int = int(exit_code)
            duration_val = float(duration_ms)
            self._entries[cache_key] = CacheEntry(
                command=command_list,
                exit_code=exit_code_int,
                duration_ms=duration_val,
                diagnostics=diagnostics_list,
                file_hashes=file_hashes_map,
                profile=str(profile) if isinstance(profile, str) and profile.strip() else None,
                config_file=(
                    str(config_file)
                    if isinstance(config_file, str) and config_file.strip()
                    else None
                ),
                plugin_args=plugin_args_list,
                include=include_list,
                exclude=exclude_list,
                overrides=overrides_list,
                category_mapping=_normalise_category_mapping(category_mapping_any),
                tool_summary=(
                    {
                        "errors": int(tool_summary_any.get("errors", 0)),
                        "warnings": int(tool_summary_any.get("warnings", 0)),
                        "information": int(tool_summary_any.get("information", 0)),
                        "total": int(tool_summary_any.get("total", 0)),
                    }
                    if isinstance(tool_summary_any, dict)
                    else None
                ),
            )

    def save(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "entries": {
                str(key): {
                    "command": entry.command,
                    "exit_code": entry.exit_code,
                    "duration_ms": entry.duration_ms,
                    "diagnostics": entry.diagnostics,
                    "file_hashes": {
                        str(path_key): payload for path_key, payload in entry.file_hashes.items()
                    },
                    "profile": entry.profile,
                    "config_file": entry.config_file,
                    "plugin_args": entry.plugin_args,
                    "include": entry.include,
                    "exclude": entry.exclude,
                    "overrides": clone_override_entries(entry.overrides),
                    "category_mapping": entry.category_mapping,
                    "tool_summary": entry.tool_summary,
                }
                for key, entry in sorted(self._entries.items())
            },
        }
        payload_json = normalise_enums_for_json(payload)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        tmp_path = self.path.with_suffix(".tmp")
        with file_lock(lock_path):
            consume(
                tmp_path.write_text(json.dumps(payload_json, indent=2) + "\n", encoding="utf-8")
            )
            consume(tmp_path.replace(self.path))
        self._dirty = False

    def peek_file_hashes(self, key: CacheKey) -> dict[PathKey, FileHashPayload] | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        return {
            path_key: cast("FileHashPayload", dict(payload))
            for path_key, payload in entry.file_hashes.items()
        }

    def key_for(
        self,
        engine: str,
        mode: Mode,
        paths: Sequence[RelPath],
        flags: Sequence[str],
    ) -> CacheKey:
        path_part = ",".join(sorted({str(item) for item in paths}))
        flag_part = ",".join(str(flag) for flag in flags)
        return CacheKey(f"{engine}:{mode}:{path_part}:{flag_part}")

    def get(self, key: CacheKey, file_hashes: dict[PathKey, FileHashPayload]) -> CachedRun | None:
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
            try:
                line_num = int(line_val)
            except (TypeError, ValueError):
                line_num = 0
            col_val = raw.get("column", 0)
            try:
                col_num = int(col_val)
            except (TypeError, ValueError):
                col_num = 0

            code_val = raw.get("code")
            code_str = str(code_val) if isinstance(code_val, str) else None
            raw_val = raw.get("raw")
            if isinstance(raw_val, Mapping):
                raw_dict: dict[str, JSONValue] = {str(k): v for k, v in raw_val.items()}
            else:
                raw_dict = {}

            diagnostics.append(
                Diagnostic(
                    tool=ToolName(str(raw.get("tool", ""))),
                    severity=SeverityLevel.coerce(raw.get("severity") or "error"),
                    path=Path(path_val),
                    line=line_num,
                    column=col_num,
                    code=code_str,
                    message=str(raw.get("message", "")),
                    raw=raw_dict,
                ),
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
            overrides=clone_override_entries(entry.overrides),
            category_mapping={k: list(v) for k, v in entry.category_mapping.items()},
            tool_summary=(
                cast("ToolSummary", dict(entry.tool_summary))
                if entry.tool_summary is not None
                else None
            ),
        )

    def update(
        self,
        key: CacheKey,
        file_hashes: dict[PathKey, FileHashPayload],
        command: Sequence[str],
        exit_code: int,
        duration_ms: float,
        diagnostics: Sequence[Diagnostic],
        *,
        profile: str | None,
        config_file: Path | None,
        plugin_args: Sequence[str],
        include: Sequence[RelPath],
        exclude: Sequence[RelPath],
        overrides: Sequence[OverrideEntry],
        category_mapping: Mapping[CategoryKey, Sequence[str]] | None,
        tool_summary: ToolSummary | None,
    ) -> None:
        canonical_diags = sorted(
            diagnostics,
            key=lambda diag: (str(diag.path), diag.line, diag.column),
        )
        file_hash_payloads: dict[PathKey, FileHashPayload] = {
            hash_key: cast("FileHashPayload", dict(hash_payload))
            for hash_key, hash_payload in file_hashes.items()
        }
        command_list: Command = [str(arg) for arg in command]
        include_list: list[RelPath] = [RelPath(str(path)) for path in include]
        exclude_list: list[RelPath] = [RelPath(str(path)) for path in exclude]

        self._entries[key] = CacheEntry(
            command=command_list,
            exit_code=exit_code,
            duration_ms=duration_ms,
            diagnostics=[
                cast(
                    "DiagnosticPayload",
                    {
                        "tool": diag.tool,
                        "severity": diag.severity.value,
                        "path": str(diag.path),
                        "line": diag.line,
                        "column": diag.column,
                        "code": diag.code,
                        "message": diag.message,
                        "raw": diag.raw,
                    },
                )
                for diag in canonical_diags
            ],
            file_hashes=file_hash_payloads,
            profile=profile,
            config_file=config_file.as_posix() if config_file else None,
            plugin_args=[str(arg) for arg in plugin_args],
            include=include_list,
            exclude=exclude_list,
            overrides=clone_override_entries(overrides),
            category_mapping=_normalise_category_mapping(category_mapping),
            tool_summary=(
                ToolSummary(
                    errors=int(tool_summary.get("errors", 0)),
                    warnings=int(tool_summary.get("warnings", 0)),
                    information=int(tool_summary.get("information", 0)),
                    total=int(tool_summary.get("total", 0)),
                )
                if tool_summary is not None
                else None
            ),
        )
        self._dirty = True


def _git_repo_root(path: Path) -> Path | None:
    cur = path.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _git_list_files(repo_root: Path) -> set[str]:
    """Return repo files respecting .gitignore using git, if available.

    Falls back to empty set on failure.
    """
    git_cmd = shutil.which("git")
    if git_cmd is None:
        logger.debug("git executable not found; skipping gitignore-aware listing")
        return set()

    try:
        import subprocess

        completed = subprocess.run(  # noqa: S603
            [git_cmd, "ls-files", "-co", "--exclude-standard"],
            check=False,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("git ls-files failed: %s", exc)
        return set()

    if completed.returncode != 0:
        return set()

    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def collect_file_hashes(
    project_root: Path,
    paths: Iterable[str],
    *,
    respect_gitignore: bool = False,
    max_files: int | None = None,
    baseline: dict[PathKey, FileHashPayload] | None = None,
    max_bytes: int | None = None,
    hash_workers: int | Literal["auto"] | None = None,
) -> tuple[dict[PathKey, FileHashPayload], bool]:
    hashes: dict[PathKey, FileHashPayload] = {}
    seen: set[PathKey] = set()
    project_root = project_root.resolve()
    allowed_project_files: set[str] | None = None
    if respect_gitignore:
        repo_root = _git_repo_root(project_root)
        if repo_root:
            git_files = _git_list_files(repo_root)
            if git_files:
                allowed_project_files = set()
                for rel_path in git_files:
                    abs_path = (repo_root / rel_path).resolve()
                    try:
                        rel_to_project = abs_path.relative_to(project_root)
                    except ValueError:
                        continue
                    allowed_project_files.add(rel_to_project.as_posix())
    truncated = False
    bytes_budget = max_bytes if isinstance(max_bytes, int) and max_bytes >= 0 else None
    bytes_seen = 0
    pending: list[tuple[PathKey, Path]] = []
    stop = False
    worker_count = _effective_hash_workers(hash_workers)

    def _maybe_add(file_path: Path) -> None:
        nonlocal truncated, bytes_seen, stop
        if stop:
            return
        key = _relative_key(project_root, file_path)
        if key in seen:
            return
        if allowed_project_files is not None and str(key) not in allowed_project_files:
            return
        try:
            st = file_path.stat()
        except FileNotFoundError:
            st = None
        if baseline is not None and st is not None and key in baseline:
            prev = baseline.get(key) or {}
            try:
                prev_mtime = int(prev.get("mtime", -1))
            except (TypeError, ValueError):
                prev_mtime = -1
            try:
                prev_size = int(prev.get("size", -1))
            except (TypeError, ValueError):
                prev_size = -1
            cur_mtime = int(getattr(st, "st_mtime_ns", 0))
            cur_size = int(getattr(st, "st_size", 0))
            if prev_mtime == cur_mtime and prev_size == cur_size:
                hashes[key] = cast("FileHashPayload", dict(prev))
                seen.add(key)
                if max_files is not None and len(seen) >= max_files:
                    truncated = True
                    stop = True
                return
        if bytes_budget is not None:
            size = int(getattr(st, "st_size", 0)) if st is not None else 0
            if bytes_seen + size > bytes_budget:
                truncated = True
                stop = True
                return
            bytes_seen += size
        seen.add(key)
        pending.append((key, file_path))
        if max_files is not None and len(seen) >= max_files:
            truncated = True
            stop = True

    for path_str in sorted({path for path in paths if path}):
        raw_path = Path(path_str)
        absolute = raw_path if raw_path.is_absolute() else (project_root / raw_path)
        absolute = absolute.resolve()
        if absolute.is_dir():
            for root, dirs, files in os.walk(absolute, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink())
                for fname in sorted(files):
                    if not (fname.endswith(".py") or fname.endswith(".pyi")):
                        continue
                    _maybe_add(Path(root) / fname)
                    if stop:
                        break
                if stop:
                    break
            if stop:
                break
        elif absolute.is_file():
            _maybe_add(absolute)
            if stop:
                break

    new_hashes = _compute_hashes(pending, worker_count)
    hashes.update(new_hashes)
    ordered_hashes: dict[PathKey, FileHashPayload] = dict(
        sorted(hashes.items(), key=lambda item: str(item[0])),
    )
    return (ordered_hashes, truncated)


def _relative_key(project_root: Path, path: Path) -> PathKey:
    try:
        return PathKey(path.resolve().relative_to(project_root).as_posix())
    except ValueError:
        return PathKey(path.resolve().as_posix())


def _fingerprint(path: Path) -> FileHashPayload:
    try:
        stat = path.stat()
        hasher = hashlib.blake2b(digest_size=16)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                if not chunk:
                    break
                hasher.update(chunk)
        return {
            "hash": hasher.hexdigest(),
            "mtime": int(stat.st_mtime_ns),
            "size": int(stat.st_size),
        }
    except FileNotFoundError:
        return {"missing": True}
    except OSError:
        return {"unreadable": True}
