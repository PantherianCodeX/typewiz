"""Execution helpers for running engines during an audit."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, cast

from .audit_config_utils import normalise_category_mapping, prepare_category_mapping
from .audit_paths import fingerprint_targets as build_fingerprint_targets
from .audit_paths import normalise_override_entries, normalise_paths, relative_override_path
from .cache import EngineCache, collect_file_hashes, fingerprint_path
from .collection_utils import merge_preserve
from .engines import EngineContext, EngineOptions
from .model_types import OverrideEntry
from .typed_manifest import ToolSummary
from .types import RunResult

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from .config import AuditConfig, PathOverride
    from .engines.base import BaseEngine

logger = logging.getLogger("typewiz")


def _path_matches(candidate: str, pattern: str) -> bool:
    if not pattern:
        return False
    candidate_norm = candidate.rstrip("/")
    pattern_norm = pattern.rstrip("/")
    if candidate_norm == pattern_norm:
        return True
    if pattern_norm and candidate_norm.startswith(f"{pattern_norm}/"):
        return True
    return False


def apply_engine_paths(
    default_paths: Sequence[str], include: Sequence[str], exclude: Sequence[str]
) -> list[str]:
    """Merge include/exclude directives with default paths for a run."""

    ordered: list[str] = []
    seen: set[str] = set()

    def _add(path: str) -> None:
        if path and path not in seen:
            seen.add(path)
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
    project_root: Path, audit_config: AuditConfig, engine: BaseEngine
) -> EngineOptions:
    """Compute engine options including overrides and category mappings."""

    engine_name = engine.name
    settings = audit_config.engine_settings.get(engine_name)
    profile_name = audit_config.active_profiles.get(engine_name)
    if not profile_name and settings:
        profile_name = settings.default_profile
    profile = settings.profiles.get(profile_name) if settings and profile_name else None

    plugin_args = list(audit_config.plugin_args.get(engine_name, []))
    if settings:
        plugin_args = merge_preserve(plugin_args, settings.plugin_args)
    if profile:
        plugin_args = merge_preserve(plugin_args, profile.plugin_args)

    include_raw: list[str] = []
    exclude_raw: list[str] = []
    if settings:
        include_raw = merge_preserve(include_raw, settings.include)
        exclude_raw = merge_preserve(exclude_raw, settings.exclude)
    if profile:
        include_raw = merge_preserve(include_raw, profile.include)
        exclude_raw = merge_preserve(exclude_raw, profile.exclude)

    include = normalise_paths(project_root, include_raw)
    exclude = normalise_paths(project_root, exclude_raw)

    config_file = None
    if profile and profile.config_file:
        config_file = profile.config_file
    elif settings and settings.config_file:
        config_file = settings.config_file

    def _override_sort_key(item: PathOverride) -> tuple[int, str]:
        try:
            rel = item.path.resolve().relative_to(project_root.resolve())
            depth = len(rel.parts)
        except ValueError:
            depth = len(item.path.resolve().parts)
        return (depth, item.path.as_posix())

    overrides = sorted(audit_config.path_overrides, key=_override_sort_key)
    applied_details: list[OverrideEntry] = []

    for override in overrides:
        before_profile = profile_name
        before_args = list(plugin_args)
        before_include = list(include)
        before_exclude = list(exclude)

        override_profile = override.active_profiles.get(engine_name)
        if override_profile:
            profile_name = override_profile
        path_settings = override.engine_settings.get(engine_name)
        include_override: list[str] = []
        exclude_override: list[str] = []
        if path_settings:
            plugin_args = merge_preserve(plugin_args, path_settings.plugin_args)
            include_override = normalise_override_entries(
                project_root, override.path, path_settings.include
            )
            exclude_override = normalise_override_entries(
                project_root, override.path, path_settings.exclude
            )
            include = merge_preserve(include, include_override)
            exclude = merge_preserve(exclude, exclude_override)
            if path_settings.config_file:
                config_file = path_settings.config_file
            if path_settings.default_profile:
                profile_name = path_settings.default_profile
        profile_override = None
        if path_settings and profile_name and path_settings.profiles:
            profile_override = path_settings.profiles.get(profile_name)
        if profile_override:
            plugin_args = merge_preserve(plugin_args, profile_override.plugin_args)
            include_profile_override = normalise_override_entries(
                project_root, override.path, profile_override.include
            )
            exclude_profile_override = normalise_override_entries(
                project_root, override.path, profile_override.exclude
            )
            include = merge_preserve(include, include_profile_override)
            exclude = merge_preserve(exclude, exclude_profile_override)
            include_override = merge_preserve(include_override, include_profile_override)
            exclude_override = merge_preserve(exclude_override, exclude_profile_override)
            if profile_override.config_file:
                config_file = profile_override.config_file

        after_args = [arg for arg in plugin_args if arg not in before_args]
        after_include = [item for item in include if item not in before_include]
        after_exclude = [item for item in exclude if item not in before_exclude]
        profile_changed = profile_name != before_profile and profile_name is not None

        if profile_changed or after_args or after_include or after_exclude:
            entry: OverrideEntry = {
                "path": relative_override_path(project_root, override.path),
            }
            if profile_changed:
                assert profile_name is not None
                entry["profile"] = profile_name
            if after_args:
                entry["pluginArgs"] = after_args
            if after_include:
                entry["include"] = after_include
            if after_exclude:
                entry["exclude"] = after_exclude
            applied_details.append(entry)

    cat_map_input = prepare_category_mapping(engine.category_mapping())

    return EngineOptions(
        plugin_args=plugin_args,
        config_file=config_file,
        include=include,
        exclude=exclude,
        profile=profile_name,
        overrides=applied_details,
        category_mapping=normalise_category_mapping(cat_map_input),
    )


def execute_engine_mode(
    *,
    engine: BaseEngine,
    mode: Literal["current", "full"],
    context: EngineContext,
    audit_config: AuditConfig,
    cache: EngineCache,
    tool_versions: Mapping[str, str],
    root: Path,
    full_paths_normalised: Sequence[str],
) -> tuple[RunResult, bool]:
    """Execute or fetch a cached engine run and return the result."""

    engine_options = context.engine_options
    mode_paths: list[str]
    if mode == "full":
        mode_paths = apply_engine_paths(
            full_paths_normalised, engine_options.include, engine_options.exclude
        )
    else:
        mode_paths = []

    cache_flags = list(engine_options.plugin_args)
    if engine_options.profile:
        cache_flags.append(f"profile={engine_options.profile}")
    if engine_options.config_file:
        cfg_path = engine_options.config_file
        cache_flags.append(f"config={cfg_path.as_posix()}")
        try:
            fingerprint = fingerprint_path(cfg_path)
            if "hash" in fingerprint:
                cache_flags.append(f"config_hash={fingerprint['hash']}")
            if "mtime" in fingerprint:
                cache_flags.append(f"config_mtime={fingerprint['mtime']}")
        except Exception:
            pass
    cache_flags.extend(f"include={path}" for path in engine_options.include)
    cache_flags.extend(f"exclude={path}" for path in engine_options.exclude)
    version = tool_versions.get(engine.name)
    if version:
        cache_flags.append(f"version={version}")

    cache_key = cache.key_for(engine.name, mode, mode_paths, cache_flags)
    prev_hashes = cache.peek_file_hashes(cache_key)

    fingerprint_result = list(engine.fingerprint_targets(context, mode_paths))
    engine_fingerprints = normalise_paths(root, fingerprint_result)
    fingerprint_targets = build_fingerprint_targets(
        root,
        mode_paths,
        full_paths_normalised,
        extra=engine_fingerprints,
    )
    file_hashes, truncated = collect_file_hashes(
        root,
        fingerprint_targets,
        respect_gitignore=bool(audit_config.respect_gitignore),
        max_files=audit_config.max_files,
        baseline=prev_hashes,
        max_bytes=getattr(audit_config, "max_bytes", None),
    )

    cached_run = cache.get(cache_key, file_hashes)
    if cached_run:
        return (
            RunResult(
                tool=engine.name,
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
                    cast(ToolSummary, dict(cached_run.tool_summary))
                    if cached_run.tool_summary is not None
                    else None
                ),
                scanned_paths=list(mode_paths),
            ),
            truncated,
        )

    try:
        result = engine.run(context, mode_paths)
    except Exception as exc:
        run_result = RunResult(
            tool=engine.name,
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

    logger.info("Running %s:%s (%s)", engine.name, mode, " ".join(result.command))

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

    run_result = RunResult(
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
    return run_result, truncated
