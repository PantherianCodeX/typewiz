from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from .data_validation import coerce_int, coerce_object_list, coerce_str_list
from .model_types import clone_override_entries
from .typed_manifest import ToolSummary
from .types import Diagnostic

if TYPE_CHECKING:
    from .model_types import (
        CategoryMapping,
        DiagnosticPayload,
        FileHashPayload,
        Mode,
        OverrideEntry,
    )


logger = logging.getLogger("typewiz.cache")
CACHE_DIRNAME = ".typewiz_cache"
CACHE_FILENAME = "cache.json"


def _default_list_str() -> list[str]:
    return []


def _default_list_dict_obj() -> list[OverrideEntry]:
    return []


def _default_dict_str_liststr() -> CategoryMapping:
    return {}


@dataclass(slots=True)
class CacheEntry:
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[DiagnosticPayload]
    file_hashes: dict[str, FileHashPayload]
    profile: str | None = None
    config_file: str | None = None
    plugin_args: list[str] = field(default_factory=_default_list_str)
    include: list[str] = field(default_factory=_default_list_str)
    exclude: list[str] = field(default_factory=_default_list_str)
    overrides: list[OverrideEntry] = field(default_factory=_default_list_dict_obj)
    category_mapping: CategoryMapping = field(default_factory=_default_dict_str_liststr)
    tool_summary: ToolSummary | None = None


@dataclass(slots=True)
class CachedRun:
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    profile: str | None = None
    config_file: Path | None = None
    plugin_args: list[str] = field(default_factory=_default_list_str)
    include: list[str] = field(default_factory=_default_list_str)
    exclude: list[str] = field(default_factory=_default_list_str)
    overrides: list[OverrideEntry] = field(default_factory=_default_list_dict_obj)
    category_mapping: CategoryMapping = field(default_factory=_default_dict_str_liststr)
    tool_summary: ToolSummary | None = None


def _normalise_category_mapping(
    mapping: Mapping[str, Sequence[str]] | None,
) -> CategoryMapping:
    if not mapping:
        return {}
    normalised: CategoryMapping = {}
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
    include_paths = coerce_str_list(raw.get("include", []))
    if include_paths:
        entry["include"] = include_paths
    exclude_paths = coerce_str_list(raw.get("exclude", []))
    if exclude_paths:
        entry["exclude"] = exclude_paths
    return entry


def _normalise_diagnostic_payload(raw: Mapping[str, object]) -> DiagnosticPayload:
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
        raw_mapping = cast("Mapping[str, object]", raw_payload)
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
        self.project_root = project_root
        self.path = project_root / CACHE_DIRNAME / CACHE_FILENAME
        self._entries: dict[str, CacheEntry] = {}
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
        for key, entry in entries.items():
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
            # Defensive normalization and typing for JSON-loaded structures
            category_mapping_input: Mapping[str, Sequence[str]] = category_mapping_any

            command_list: list[str] = [str(a) for a in command_any]
            plugin_args_list: list[str] = [str(a) for a in plugin_args_any]
            include_list: list[str] = [str(i) for i in include_any]
            exclude_list: list[str] = [str(i) for i in exclude_any]
            overrides_list: list[OverrideEntry] = []
            for override_raw in coerce_object_list(overrides_any):
                if isinstance(override_raw, Mapping):
                    overrides_list.append(
                        _normalise_override_entry(cast("Mapping[str, object]", override_raw))
                    )
            file_hashes_map: dict[str, FileHashPayload] = {}
            file_hashes_mapping: Mapping[str, Mapping[str, object]] = file_hashes_any
            for hash_key, hash_payload in file_hashes_mapping.items():
                file_hashes_map[hash_key] = _normalise_file_hash_payload(hash_payload)
            diagnostics_list: list[DiagnosticPayload] = []
            for diag_raw in coerce_object_list(diagnostics_any):
                if isinstance(diag_raw, Mapping):
                    diagnostics_list.append(
                        _normalise_diagnostic_payload(cast("Mapping[str, object]", diag_raw))
                    )
            exit_code_int = int(exit_code)
            duration_val = float(duration_ms)
            self._entries[key] = CacheEntry(
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
                category_mapping=_normalise_category_mapping(category_mapping_input),
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
                    "overrides": clone_override_entries(entry.overrides),
                    "category_mapping": entry.category_mapping,
                    "tool_summary": entry.tool_summary,
                }
                for key, entry in sorted(self._entries.items())
            }
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._dirty = False

    def peek_file_hashes(self, key: str) -> dict[str, FileHashPayload] | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        return {
            hash_key: cast("FileHashPayload", dict(payload))
            for hash_key, payload in entry.file_hashes.items()
        }

    def key_for(self, engine: str, mode: Mode, paths: Sequence[str], flags: Sequence[str]) -> str:
        path_part = ",".join(sorted({str(item) for item in paths}))
        flag_part = ",".join(str(flag) for flag in flags)
        return f"{engine}:{mode}:{path_part}:{flag_part}"

    def get(self, key: str, file_hashes: dict[str, FileHashPayload]) -> CachedRun | None:
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
                raw_dict = {str(k): v for k, v in raw_val.items()}
            else:
                raw_dict = {}

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
            overrides=clone_override_entries(entry.overrides),
            category_mapping={k: list(v) for k, v in entry.category_mapping.items()},
            tool_summary=(
                cast(ToolSummary, dict(entry.tool_summary))
                if entry.tool_summary is not None
                else None
            ),
        )

    def update(
        self,
        key: str,
        file_hashes: dict[str, FileHashPayload],
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
        overrides: Sequence[OverrideEntry],
        category_mapping: Mapping[str, Sequence[str]] | None,
        tool_summary: ToolSummary | None,
    ) -> None:
        canonical_diags = sorted(
            diagnostics, key=lambda diag: (str(diag.path), diag.line, diag.column)
        )
        file_hash_payloads: dict[str, FileHashPayload] = {
            hash_key: cast("FileHashPayload", dict(hash_payload))
            for hash_key, hash_payload in file_hashes.items()
        }

        self._entries[key] = CacheEntry(
            command=[str(arg) for arg in command],
            exit_code=exit_code,
            duration_ms=duration_ms,
            diagnostics=[
                cast(
                    "DiagnosticPayload",
                    {
                        "tool": diag.tool,
                        "severity": diag.severity,
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
            include=[str(path) for path in include],
            exclude=[str(path) for path in exclude],
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
    baseline: dict[str, FileHashPayload] | None = None,
    max_bytes: int | None = None,
) -> tuple[dict[str, FileHashPayload], bool]:
    hashes: dict[str, FileHashPayload] = {}
    seen: set[str] = set()
    project_root = project_root.resolve()
    allowed_git_files: set[str] | None = None
    if respect_gitignore:
        repo_root = _git_repo_root(project_root)
        if repo_root:
            allowed_git_files = _git_list_files(repo_root)
    truncated = False
    bytes_budget = max_bytes if isinstance(max_bytes, int) and max_bytes >= 0 else None
    bytes_seen = 0

    def _maybe_add(file_path: Path) -> bool:
        nonlocal truncated, bytes_seen
        key = _relative_key(project_root, file_path)
        if key in seen:
            return True
        if allowed_git_files is not None and key not in allowed_git_files:
            return True
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
                return not (max_files is not None and len(seen) >= max_files)
        # size budget check before hashing to avoid heavy IO
        if bytes_budget is not None:
            size = int(getattr(st, "st_size", 0)) if st is not None else 0
            if bytes_seen + size > bytes_budget:
                truncated = True
                return False
            bytes_seen += size
        hashes[key] = _fingerprint(file_path)
        seen.add(key)
        if max_files is not None and len(seen) >= max_files:
            truncated = True
            return False
        return True

    for path_str in sorted({path for path in paths if path}):
        raw_path = Path(path_str)
        absolute = raw_path if raw_path.is_absolute() else (project_root / raw_path)
        absolute = absolute.resolve()
        if absolute.is_dir():
            for root, dirs, files in os.walk(absolute, followlinks=False):
                dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
                for fname in sorted(files):
                    if not (fname.endswith(".py") or fname.endswith(".pyi")):
                        continue
                    if not _maybe_add(Path(root) / fname):
                        return (dict(sorted(hashes.items())), truncated)
        elif absolute.is_file() and not _maybe_add(absolute):
            return (dict(sorted(hashes.items())), truncated)
    ordered_hashes: dict[str, FileHashPayload] = dict(sorted(hashes.items()))
    return (ordered_hashes, truncated)


def _relative_key(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


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
