# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Execution helpers for running engines during an audit."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from typewiz.audit.options import normalise_category_mapping, prepare_category_mapping
from typewiz.audit.paths import fingerprint_targets as build_fingerprint_targets
from typewiz.audit.paths import normalise_override_entries, normalise_paths, relative_override_path
from typewiz.cache import CachedRun, EngineCache, collect_file_hashes, fingerprint_path
from typewiz.collections import merge_preserve
from typewiz.config import AuditConfig, EngineProfile, EngineSettings, PathOverride
from typewiz.core.model_types import FileHashPayload, LogComponent, Mode, OverrideEntry
from typewiz.core.type_aliases import CacheKey, EngineName, PathKey, ProfileName, RelPath, ToolName
from typewiz.core.types import RunResult
from typewiz.engines import EngineContext, EngineOptions
from typewiz.engines.base import BaseEngine, EngineResult
from typewiz.logging import StructuredLogExtra, structured_extra
from typewiz.manifest.typed import ToolSummary


@dataclass(slots=True)
class _EngineOptionState:
    plugin_args: list[str]
    include: list[RelPath]
    exclude: list[RelPath]
    profile: ProfileName | None
    config_file: Path | None

    def copy(self) -> _EngineOptionState:
        return _EngineOptionState(
            plugin_args=list(self.plugin_args),
            include=list(self.include),
            exclude=list(self.exclude),
            profile=self.profile,
            config_file=self.config_file,
        )


def _resolve_base_profile(
    audit_config: AuditConfig,
    engine_name: EngineName,
) -> tuple[EngineSettings | None, ProfileName | None, EngineProfile | None]:
    settings = audit_config.engine_settings.get(engine_name)
    profile_name = audit_config.active_profiles.get(engine_name)
    if not profile_name and settings:
        profile_name = settings.default_profile
    profile = settings.profiles.get(profile_name) if settings and profile_name else None
    return settings, profile_name, profile


def _merge_base_plugin_args(
    audit_config: AuditConfig,
    engine_name: EngineName,
    settings: EngineSettings | None,
    profile: EngineProfile | None,
) -> list[str]:
    plugin_args = list(audit_config.plugin_args.get(engine_name, []))
    if settings:
        plugin_args = merge_preserve(plugin_args, settings.plugin_args)
    if profile:
        plugin_args = merge_preserve(plugin_args, profile.plugin_args)
    return plugin_args


def _merge_base_paths(
    settings: EngineSettings | None,
    profile: EngineProfile | None,
) -> tuple[list[str], list[str]]:
    include_raw: list[str] = []
    exclude_raw: list[str] = []
    if settings:
        include_raw = merge_preserve(include_raw, settings.include)
        exclude_raw = merge_preserve(exclude_raw, settings.exclude)
    if profile:
        include_raw = merge_preserve(include_raw, profile.include)
        exclude_raw = merge_preserve(exclude_raw, profile.exclude)
    return include_raw, exclude_raw


def _initial_option_state(  # noqa: PLR0913
    project_root: Path,
    audit_config: AuditConfig,
    engine_name: EngineName,
    settings: EngineSettings | None,
    profile_name: ProfileName | None,
    profile: EngineProfile | None,
) -> _EngineOptionState:
    plugin_args = _merge_base_plugin_args(audit_config, engine_name, settings, profile)
    include_raw, exclude_raw = _merge_base_paths(settings, profile)
    include = normalise_paths(project_root, include_raw)
    exclude = normalise_paths(project_root, exclude_raw)
    config_file = None
    if profile and profile.config_file:
        config_file = profile.config_file
    elif settings and settings.config_file:
        config_file = settings.config_file
    return _EngineOptionState(
        plugin_args=plugin_args,
        include=include,
        exclude=exclude,
        profile=profile_name,
        config_file=config_file,
    )


def _sort_overrides(project_root: Path, overrides: Sequence[PathOverride]) -> list[PathOverride]:
    def _override_sort_key(item: PathOverride) -> tuple[int, str]:
        try:
            rel = item.path.resolve().relative_to(project_root.resolve())
            depth = len(rel.parts)
        except ValueError:
            depth = len(item.path.resolve().parts)
        return (depth, item.path.as_posix())

    return sorted(overrides, key=_override_sort_key)


def _diff_override_entry(
    *,
    before: _EngineOptionState,
    after: _EngineOptionState,
    project_root: Path,
    override_path: Path,
    engine_name: EngineName,
) -> OverrideEntry | None:
    after_args = [arg for arg in after.plugin_args if arg not in before.plugin_args]
    after_include = [item for item in after.include if item not in before.include]
    after_exclude = [item for item in after.exclude if item not in before.exclude]
    profile_changed = after.profile != before.profile and after.profile is not None
    profile_removed = after.profile is None and after.profile != before.profile
    if not (profile_changed or profile_removed or after_args or after_include or after_exclude):
        return None
    entry: OverrideEntry = {
        "path": relative_override_path(project_root, override_path),
    }
    if profile_changed and after.profile is not None:
        entry["profile"] = after.profile
    elif profile_removed:
        logger.warning(
            "Active profile change detected for engine '%s' but profile is missing",
            engine_name,
            extra=structured_extra(component=LogComponent.CLI, tool=engine_name),
        )
    if after_args:
        entry["pluginArgs"] = after_args
    if after_include:
        entry["include"] = after_include
    if after_exclude:
        entry["exclude"] = after_exclude
    return entry


def _apply_path_override(
    project_root: Path,
    override: PathOverride,
    engine_name: EngineName,
    state: _EngineOptionState,
) -> OverrideEntry | None:
    before = state.copy()
    override_profile = override.active_profiles.get(engine_name)
    if override_profile:
        state.profile = override_profile
    path_settings = override.engine_settings.get(engine_name)
    if path_settings:
        state.plugin_args = merge_preserve(state.plugin_args, path_settings.plugin_args)
        include_override = normalise_override_entries(
            project_root,
            override.path,
            path_settings.include,
        )
        exclude_override = normalise_override_entries(
            project_root,
            override.path,
            path_settings.exclude,
        )
        state.include = merge_preserve(state.include, include_override)
        state.exclude = merge_preserve(state.exclude, exclude_override)
        if path_settings.config_file:
            state.config_file = path_settings.config_file
        if path_settings.default_profile:
            state.profile = path_settings.default_profile
    profile_override = None
    if path_settings and state.profile and path_settings.profiles:
        profile_override = path_settings.profiles.get(state.profile)
    if profile_override:
        state.plugin_args = merge_preserve(state.plugin_args, profile_override.plugin_args)
        include_profile_override = normalise_override_entries(
            project_root,
            override.path,
            profile_override.include,
        )
        exclude_profile_override = normalise_override_entries(
            project_root,
            override.path,
            profile_override.exclude,
        )
        state.include = merge_preserve(state.include, include_profile_override)
        state.exclude = merge_preserve(state.exclude, exclude_profile_override)
        if profile_override.config_file:
            state.config_file = profile_override.config_file
    return _diff_override_entry(
        before=before,
        after=state,
        project_root=project_root,
        override_path=override.path,
        engine_name=engine_name,
    )


def _paths_for_mode(
    mode: Mode,
    engine_options: EngineOptions,
    full_paths_normalised: Sequence[RelPath],
) -> list[RelPath]:
    if mode is Mode.FULL:
        return apply_engine_paths(
            full_paths_normalised,
            engine_options.include,
            engine_options.exclude,
        )
    return []


def _build_cache_flags(
    engine_name: str,
    engine_options: EngineOptions,
    tool_versions: Mapping[str, str],
) -> list[str]:
    cache_flags = list(engine_options.plugin_args)
    if engine_options.profile:
        cache_flags.append(f"profile={engine_options.profile}")
    if engine_options.config_file:
        cfg_path = engine_options.config_file
        cache_flags.append(f"config={cfg_path.as_posix()}")
        try:
            fingerprint = fingerprint_path(cfg_path)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Unable to fingerprint config %s: %s",
                cfg_path,
                exc,
                extra=structured_extra(component=LogComponent.CACHE, tool=engine_name),
            )
        else:
            if "hash" in fingerprint:
                cache_flags.append(f"config_hash={fingerprint['hash']}")
            if "mtime" in fingerprint:
                cache_flags.append(f"config_mtime={fingerprint['mtime']}")
    cache_flags.extend(f"include={path}" for path in engine_options.include)
    cache_flags.extend(f"exclude={path}" for path in engine_options.exclude)
    version = tool_versions.get(engine_name)
    if version:
        cache_flags.append(f"version={version}")
    return cache_flags


def _fingerprint_targets_for_run(
    *,
    engine: BaseEngine,
    context: EngineContext,
    root: Path,
    mode_paths: Sequence[RelPath],
    full_paths_normalised: Sequence[RelPath],
) -> list[RelPath]:
    fingerprint_result = list(engine.fingerprint_targets(context, list(mode_paths)))
    engine_fingerprints = normalise_paths(root, fingerprint_result)
    return build_fingerprint_targets(
        root,
        list(mode_paths),
        full_paths_normalised,
        extra=engine_fingerprints,
    )


def _prepare_cache_inputs(  # noqa: PLR0913
    *,
    engine: BaseEngine,
    mode: Mode,
    engine_options: EngineOptions,
    cache: EngineCache,
    tool_versions: Mapping[str, str],
    context: EngineContext,
    audit_config: AuditConfig,
    root: Path,
    full_paths_normalised: Sequence[RelPath],
    mode_paths: Sequence[RelPath],
) -> tuple[CacheKey, dict[PathKey, FileHashPayload], bool]:
    cache_flags = _build_cache_flags(engine.name, engine_options, tool_versions)
    cache_key = cache.key_for(engine.name, mode, list(mode_paths), cache_flags)
    prev_hashes = cache.peek_file_hashes(cache_key)
    fingerprint_targets = _fingerprint_targets_for_run(
        engine=engine,
        context=context,
        root=root,
        mode_paths=mode_paths,
        full_paths_normalised=full_paths_normalised,
    )
    file_hashes, truncated = collect_file_hashes(
        root,
        fingerprint_targets,
        respect_gitignore=bool(audit_config.respect_gitignore),
        max_files=audit_config.max_files,
        baseline=prev_hashes,
        max_bytes=getattr(audit_config, "max_bytes", None),
        hash_workers=audit_config.hash_workers,
    )
    return cache_key, file_hashes, truncated


def _build_cached_run_result(
    *,
    engine_name: ToolName,
    mode: Mode,
    cached_run: CachedRun,
    mode_paths: Sequence[RelPath],
) -> RunResult:
    return RunResult(
        tool=engine_name,
        mode=mode,
        command=list(cached_run.command),
        exit_code=cached_run.exit_code,
        duration_ms=cached_run.duration_ms,
        diagnostics=list(cached_run.diagnostics),
        cached=True,
        profile=cached_run.profile,
        config_file=cached_run.config_file,
        plugin_args=list(cached_run.plugin_args),
        include=list(cached_run.include),
        exclude=list(cached_run.exclude),
        overrides=[cast("OverrideEntry", dict(item)) for item in cached_run.overrides],
        category_mapping={k: list(v) for k, v in cached_run.category_mapping.items()},
        tool_summary=(
            cast("ToolSummary", dict(cached_run.tool_summary))
            if cached_run.tool_summary is not None
            else None
        ),
        scanned_paths=list(mode_paths),
    )


def _build_run_result(
    *,
    engine_options: EngineOptions,
    result: EngineResult,
    mode_paths: Sequence[RelPath],
) -> RunResult:
    return RunResult(
        tool=result.engine,
        mode=result.mode,
        command=list(result.command),
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=list(result.diagnostics),
        cached=False,
        profile=engine_options.profile,
        config_file=engine_options.config_file,
        plugin_args=list(engine_options.plugin_args),
        include=list(engine_options.include),
        exclude=list(engine_options.exclude),
        overrides=[cast("OverrideEntry", dict(item)) for item in engine_options.overrides],
        category_mapping={k: list(v) for k, v in engine_options.category_mapping.items()},
        tool_summary=result.tool_summary,
        scanned_paths=list(mode_paths),
    )


logger: logging.Logger = logging.getLogger("typewiz.audit.execution")


def _path_matches(candidate: RelPath, pattern: RelPath) -> bool:
    if not pattern:
        return False
    candidate_norm = str(candidate).rstrip("/")
    pattern_norm = str(pattern).rstrip("/")
    return candidate_norm == pattern_norm or (
        pattern_norm != "" and candidate_norm.startswith(f"{pattern_norm}/")
    )


def apply_engine_paths(
    default_paths: Sequence[RelPath],
    include: Sequence[RelPath],
    exclude: Sequence[RelPath],
) -> list[RelPath]:
    """Merge include/exclude directives with default paths for a run."""
    ordered: list[RelPath] = []
    seen: set[str] = set()

    def _add(path: RelPath) -> None:
        path_str = str(path)
        if path_str and path_str not in seen:
            seen.add(path_str)
            ordered.append(path)

    for path in default_paths:
        _add(path)
    for path in include:
        _add(path)

    if not exclude:
        return ordered

    filtered = [
        path for path in ordered if not any(_path_matches(path, pattern) for pattern in exclude)
    ]
    return filtered or ordered


def resolve_engine_options(
    project_root: Path,
    audit_config: AuditConfig,
    engine: BaseEngine,
) -> EngineOptions:
    """Compute engine options including overrides and category mappings."""
    engine_name = EngineName(engine.name)
    settings, profile_name, profile = _resolve_base_profile(audit_config, engine_name)
    state = _initial_option_state(
        project_root,
        audit_config,
        engine_name,
        settings,
        profile_name,
        profile,
    )
    applied_details: list[OverrideEntry] = []
    for override in _sort_overrides(project_root, audit_config.path_overrides):
        entry = _apply_path_override(project_root, override, engine_name, state)
        if entry:
            applied_details.append(entry)
    cat_map_input = prepare_category_mapping(engine.category_mapping())
    return EngineOptions(
        plugin_args=state.plugin_args,
        config_file=state.config_file,
        include=state.include,
        exclude=state.exclude,
        profile=state.profile,
        overrides=applied_details,
        category_mapping=normalise_category_mapping(cat_map_input),
    )


def execute_engine_mode(  # noqa: PLR0913
    *,
    engine: BaseEngine,
    mode: Mode,
    context: EngineContext,
    audit_config: AuditConfig,
    cache: EngineCache,
    tool_versions: Mapping[str, str],
    root: Path,
    full_paths_normalised: Sequence[RelPath],
) -> tuple[RunResult, bool]:
    """Execute or fetch a cached engine run and return the result."""
    engine_options = context.engine_options
    mode_paths = _paths_for_mode(mode, engine_options, full_paths_normalised)
    cache_key, file_hashes, truncated = _prepare_cache_inputs(
        engine=engine,
        mode=mode,
        engine_options=engine_options,
        cache=cache,
        tool_versions=tool_versions,
        context=context,
        audit_config=audit_config,
        root=root,
        full_paths_normalised=full_paths_normalised,
        mode_paths=mode_paths,
    )

    cached_run = cache.get(cache_key, file_hashes)
    if cached_run:
        cache_hit_extra: StructuredLogExtra = structured_extra(
            component=LogComponent.CACHE,
            tool=engine.name,
            mode=mode,
            cached=True,
        )
        logger.info(
            "Cache hit for %s:%s",
            engine.name,
            mode,
            extra=cache_hit_extra,
        )
        return _build_cached_run_result(
            engine_name=ToolName(engine.name),
            mode=mode,
            cached_run=cached_run,
            mode_paths=mode_paths,
        ), truncated

    cache_miss_extra: StructuredLogExtra = structured_extra(
        component=LogComponent.CACHE,
        tool=engine.name,
        mode=mode,
        cached=False,
    )
    logger.info(
        "Cache miss for %s:%s",
        engine.name,
        mode,
        extra=cache_miss_extra,
    )

    try:
        result = engine.run(context, mode_paths)
    except Exception as exc:
        logger.error(
            "Engine %s:%s failed",
            engine.name,
            mode,
            exc_info=True,
            extra=structured_extra(
                component=LogComponent.ENGINE,
                tool=engine.name,
                mode=mode,
            ),
        )
        run_result = RunResult(
            tool=ToolName(engine.name),
            mode=mode,
            command=[engine.name, mode],
            exit_code=1,
            duration_ms=0.0,
            diagnostics=[],
            cached=False,
            profile=engine_options.profile,
            config_file=engine_options.config_file,
            plugin_args=list(engine_options.plugin_args),
            include=list(engine_options.include),
            exclude=list(engine_options.exclude),
            overrides=[cast("OverrideEntry", dict(item)) for item in engine_options.overrides],
            category_mapping={k: list(v) for k, v in engine_options.category_mapping.items()},
            tool_summary=None,
            scanned_paths=list(mode_paths),
            engine_error={"message": str(exc), "exitCode": 1},
        )
        return run_result, truncated

    run_extra: StructuredLogExtra = structured_extra(
        component=LogComponent.CLI,
        tool=engine.name,
        mode=mode,
        cached=False,
        duration_ms=result.duration_ms,
        exit_code=result.exit_code,
    )
    logger.info(
        "Running %s:%s (%s)",
        engine.name,
        mode,
        " ".join(result.command),
        extra=run_extra,
    )

    cache.update(
        cache_key,
        file_hashes,
        result.command,
        result.exit_code,
        result.duration_ms,
        result.diagnostics,
        profile=engine_options.profile,
        config_file=engine_options.config_file,
        plugin_args=engine_options.plugin_args,
        include=engine_options.include,
        exclude=engine_options.exclude,
        overrides=engine_options.overrides,
        category_mapping=engine_options.category_mapping,
        tool_summary=result.tool_summary,
    )

    run_result = _build_run_result(
        engine_options=engine_options,
        result=result,
        mode_paths=mode_paths,
    )
    return run_result, truncated
