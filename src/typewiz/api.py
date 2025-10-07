from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence, Callable, cast

from .cache import EngineCache, collect_file_hashes
from .config import (
    AuditConfig,
    Config,
    EngineProfile,
    EngineSettings,
    PathOverride,
    load_config,
)
from .dashboard import build_summary, render_markdown
from .engines import EngineContext, EngineOptions, resolve_engines
from .engines.base import BaseEngine
from .html_report import render_html
from .manifest import ManifestBuilder
from .typed_manifest import ManifestData
from .types import RunResult
from .utils import default_full_paths, resolve_project_root

logger = logging.getLogger("typewiz")


@dataclass(slots=True)
class AuditResult:
    manifest: ManifestData
    runs: list[RunResult]
    summary: dict[str, object] | None = None
    error_count: int = 0
    warning_count: int = 0


def _clone_profile(profile: EngineProfile) -> EngineProfile:
    return EngineProfile(
        inherit=profile.inherit,
        plugin_args=list(profile.plugin_args),
        config_file=profile.config_file,
        include=list(profile.include),
        exclude=list(profile.exclude),
    )


def _clone_engine_settings_map(settings: dict[str, EngineSettings]) -> dict[str, EngineSettings]:
    cloned: dict[str, EngineSettings] = {}
    for name, value in settings.items():
        cloned[name] = EngineSettings(
            plugin_args=list(value.plugin_args),
            config_file=value.config_file,
            include=list(value.include),
            exclude=list(value.exclude),
            default_profile=value.default_profile,
            profiles={key: _clone_profile(profile) for key, profile in value.profiles.items()},
        )
    return cloned


def _merge_list(base: list[str], addition: Sequence[str]) -> list[str]:
    result = list(base)
    seen = set(result)
    for value in addition:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _normalise_category_mapping(mapping: Mapping[str, Sequence[str]] | None) -> dict[str, list[str]]:
    if not mapping:
        return {}
    normalised: dict[str, list[str]] = {}
    for key, raw_values in mapping.items():
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


def _merge_engine_settings_map(
    base: dict[str, EngineSettings], override: dict[str, EngineSettings]
) -> dict[str, EngineSettings]:
    result = _clone_engine_settings_map(base)
    for name, override_settings in override.items():
        if name not in result:
            result[name] = _clone_engine_settings_map({name: override_settings})[name]
            continue
        target = result[name]
        target.plugin_args = _merge_list(target.plugin_args, override_settings.plugin_args)
        target.include = _merge_list(target.include, override_settings.include)
        target.exclude = _merge_list(target.exclude, override_settings.exclude)
        if override_settings.config_file is not None:
            target.config_file = override_settings.config_file
        if override_settings.default_profile is not None:
            target.default_profile = override_settings.default_profile
        for profile_name, override_profile in override_settings.profiles.items():
            if profile_name not in target.profiles:
                target.profiles[profile_name] = _clone_profile(override_profile)
                continue
            profile_target = target.profiles[profile_name]
            if override_profile.inherit is not None:
                profile_target.inherit = override_profile.inherit
            if override_profile.config_file is not None:
                profile_target.config_file = override_profile.config_file
            profile_target.plugin_args = _merge_list(
                profile_target.plugin_args, override_profile.plugin_args
            )
            profile_target.include = _merge_list(profile_target.include, override_profile.include)
            profile_target.exclude = _merge_list(profile_target.exclude, override_profile.exclude)
    return result


def _clone_path_overrides(overrides: Sequence[PathOverride]) -> list[PathOverride]:
    cloned: list[PathOverride] = []
    for override in overrides:
        cloned.append(
            PathOverride(
                path=override.path,
                engine_settings=_clone_engine_settings_map(override.engine_settings),
                active_profiles=dict(override.active_profiles),
            )
        )
    return cloned


def _clone_config(source: AuditConfig) -> AuditConfig:
    return AuditConfig(
        manifest_path=source.manifest_path,
        full_paths=list(source.full_paths) if source.full_paths is not None else None,
        max_depth=source.max_depth,
        skip_current=source.skip_current,
        skip_full=source.skip_full,
        fail_on=source.fail_on,
        dashboard_json=source.dashboard_json,
        dashboard_markdown=source.dashboard_markdown,
        dashboard_html=source.dashboard_html,
        runners=list(source.runners) if source.runners is not None else None,
        plugin_args={k: list(v) for k, v in source.plugin_args.items()},
        engine_settings=_clone_engine_settings_map(source.engine_settings),
        active_profiles=dict(source.active_profiles),
        path_overrides=_clone_path_overrides(source.path_overrides),
    )


def _merge_configs(base: AuditConfig, override: AuditConfig | None) -> AuditConfig:
    base_copy = _clone_config(base)
    if override is None:
        return base_copy

    merged = AuditConfig(
        manifest_path=override.manifest_path or base_copy.manifest_path,
        full_paths=override.full_paths or base_copy.full_paths,
        max_depth=override.max_depth or base_copy.max_depth,
        skip_current=override.skip_current if override.skip_current is not None else base_copy.skip_current,
        skip_full=override.skip_full if override.skip_full is not None else base_copy.skip_full,
        fail_on=override.fail_on or base_copy.fail_on,
        dashboard_json=override.dashboard_json or base_copy.dashboard_json,
        dashboard_markdown=override.dashboard_markdown or base_copy.dashboard_markdown,
        dashboard_html=override.dashboard_html or base_copy.dashboard_html,
        runners=override.runners or base_copy.runners,
    )
    merged.plugin_args = {k: list(v) for k, v in base_copy.plugin_args.items()}
    for name, values in override.plugin_args.items():
        merged.plugin_args.setdefault(name, []).extend(values)
    for name, values in merged.plugin_args.items():
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                deduped.append(value)
        merged.plugin_args[name] = deduped
    merged.plugin_args = dict(sorted(merged.plugin_args.items()))
    merged.engine_settings = _merge_engine_settings_map(
        base_copy.engine_settings, override.engine_settings
    )
    merged.active_profiles = dict(base_copy.active_profiles)
    merged.active_profiles.update({k: v for k, v in override.active_profiles.items() if v})
    merged.path_overrides = _clone_path_overrides(base_copy.path_overrides)
    if override.path_overrides:
        merged.path_overrides.extend(_clone_path_overrides(override.path_overrides))
    return merged


def _normalise_paths(project_root: Path, raw_paths: Sequence[str]) -> list[str]:
    normalised: list[str] = []
    seen: set[str] = set()
    root = project_root.resolve()
    for raw in raw_paths:
        if not raw:
            continue
        candidate = Path(raw)
        absolute = candidate if candidate.is_absolute() else (root / candidate)
        absolute = absolute.resolve()
        try:
            relative = absolute.relative_to(root)
            key = relative.as_posix()
        except ValueError:
            key = absolute.as_posix()
        if key not in seen:
            seen.add(key)
            normalised.append(key)
    return normalised


def _global_fingerprint_paths(project_root: Path) -> list[str]:
    extras: list[str] = []
    for filename in ("typewiz.toml", ".typewiz.toml", "pyproject.toml"):
        candidate = project_root / filename
        if candidate.exists():
            extras.append(filename)
    return _normalise_paths(project_root, extras)


def _fingerprint_targets(
    project_root: Path,
    mode_paths: Sequence[str],
    default_paths: Sequence[str],
    extra: Sequence[str] | None = None,
) -> list[str]:
    candidates = list(mode_paths) if mode_paths else list(default_paths)
    candidates.extend(_global_fingerprint_paths(project_root))
    if extra:
        candidates.extend(extra)
    if not candidates:
        candidates = ["."]
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in candidates:
        if entry not in seen:
            seen.add(entry)
            ordered.append(entry)
    return ordered


def _normalise_override_entries(
    project_root: Path, override_path: Path, entries: Sequence[str]
) -> list[str]:
    if not entries:
        entries = ["."]
    normalised: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = (override_path / candidate).resolve()
        try:
            relative = candidate.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError:
            relative = candidate.resolve().as_posix()
        if relative not in seen:
            seen.add(relative)
            normalised.append(relative)
    return normalised


def _relative_override_path(project_root: Path, override_path: Path) -> str:
    try:
        return override_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return override_path.resolve().as_posix()


def _resolve_engine_options(
    project_root: Path, audit_config: AuditConfig, engine: BaseEngine
) -> EngineOptions:
    engine_name = engine.name
    settings = audit_config.engine_settings.get(engine_name)
    profile_name = audit_config.active_profiles.get(engine_name)
    if not profile_name and settings:
        profile_name = settings.default_profile
    profile = settings.profiles.get(profile_name) if settings and profile_name else None

    plugin_args = list(audit_config.plugin_args.get(engine_name, []))
    if settings:
        plugin_args = _merge_list(plugin_args, settings.plugin_args)
    if profile:
        plugin_args = _merge_list(plugin_args, profile.plugin_args)

    include_raw: list[str] = []
    exclude_raw: list[str] = []
    if settings:
        include_raw = _merge_list(include_raw, settings.include)
        exclude_raw = _merge_list(exclude_raw, settings.exclude)
    if profile:
        include_raw = _merge_list(include_raw, profile.include)
        exclude_raw = _merge_list(exclude_raw, profile.exclude)

    include = _normalise_paths(project_root, include_raw)
    exclude = _normalise_paths(project_root, exclude_raw)

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
    applied_details: list[dict[str, object]] = []

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
            plugin_args = _merge_list(plugin_args, path_settings.plugin_args)
            include_override = _normalise_override_entries(project_root, override.path, path_settings.include)
            exclude_override = _normalise_override_entries(project_root, override.path, path_settings.exclude)
            include = _merge_list(include, include_override)
            exclude = _merge_list(exclude, exclude_override)
            if path_settings.config_file:
                config_file = path_settings.config_file
            if path_settings.default_profile:
                profile_name = path_settings.default_profile
        profile_override = None
        if path_settings and profile_name and path_settings.profiles:
            profile_override = path_settings.profiles.get(profile_name)
        if profile_override:
            plugin_args = _merge_list(plugin_args, profile_override.plugin_args)
            include_profile_override = _normalise_override_entries(
                project_root, override.path, profile_override.include
            )
            exclude_profile_override = _normalise_override_entries(
                project_root, override.path, profile_override.exclude
            )
            include = _merge_list(include, include_profile_override)
            exclude = _merge_list(exclude, exclude_profile_override)
            include_override = _merge_list(include_override, include_profile_override)
            exclude_override = _merge_list(exclude_override, exclude_profile_override)
            if profile_override.config_file:
                config_file = profile_override.config_file

        after_args = [arg for arg in plugin_args if arg not in before_args]
        after_include = [item for item in include if item not in before_include]
        after_exclude = [item for item in exclude if item not in before_exclude]
        profile_changed = profile_name != before_profile and profile_name is not None

        if profile_changed or after_args or after_include or after_exclude:
            entry: dict[str, object] = {
                "path": _relative_override_path(project_root, override.path),
            }
            if profile_changed:
                entry["profile"] = profile_name
            if after_args:
                entry["pluginArgs"] = after_args
            if after_include:
                entry["include"] = after_include
            if after_exclude:
                entry["exclude"] = after_exclude
            applied_details.append(entry)

    return EngineOptions(
        plugin_args=plugin_args,
        config_file=config_file,
        include=include,
        exclude=exclude,
        profile=profile_name,
        overrides=applied_details,
        category_mapping=_normalise_category_mapping(engine.category_mapping()),
    )


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


def _apply_engine_paths(
    default_paths: Sequence[str], include: Sequence[str], exclude: Sequence[str]
) -> list[str]:
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


def run_audit(
    *,
    project_root: Path | None = None,
    config: Config | None = None,
    override: AuditConfig | None = None,
    full_paths: Sequence[str] | None = None,
    write_manifest_to: Path | None = None,
    build_summary_output: bool = False,
) -> AuditResult:
    cfg = config or load_config(None)
    audit_config = _merge_configs(cfg.audit, override)

    root = resolve_project_root(project_root)
    raw_full_paths = list(full_paths) if full_paths else (audit_config.full_paths or default_full_paths(root))
    if not raw_full_paths:
        raise ValueError("No directories to scan; configure 'full_paths' or pass 'full_paths' argument")

    full_paths_normalised = _normalise_paths(root, raw_full_paths)
    engines = resolve_engines(audit_config.runners)
    cache = EngineCache(root)

    runs: list[RunResult] = []
    for engine in engines:
        engine_options = _resolve_engine_options(root, audit_config, engine)
        for mode in ("current", "full"):
            if mode == "current" and audit_config.skip_current:
                continue
            if mode == "full" and audit_config.skip_full:
                continue

            context = EngineContext(
                project_root=root,
                audit_config=audit_config,
                mode=mode,
                engine_options=engine_options,
            )
            base_paths = full_paths_normalised if mode == "full" else []
            mode_paths = (
                _apply_engine_paths(base_paths, engine_options.include, engine_options.exclude)
                if mode == "full"
                else []
            )
            cache_flags = list(engine_options.plugin_args)
            if engine_options.profile:
                cache_flags.append(f"profile={engine_options.profile}")
            if engine_options.config_file:
                cache_flags.append(f"config={engine_options.config_file.as_posix()}")
            cache_flags.extend(f"include={path}" for path in engine_options.include)
            cache_flags.extend(f"exclude={path}" for path in engine_options.exclude)
            cache_key = cache.key_for(engine.name, mode, mode_paths, cache_flags)
            fingerprint_provider: Callable[[EngineContext, Sequence[str]], Sequence[str]]
            if hasattr(engine, "fingerprint_targets"):
                fingerprint_provider = cast(
                    Callable[[EngineContext, Sequence[str]], Sequence[str]],
                    getattr(engine, "fingerprint_targets"),
                )
            else:
                def _fp(_c: EngineContext, _p: Sequence[str]) -> Sequence[str]:
                    return []
            fingerprint_provider = _fp
            engine_fingerprints = _normalise_paths(
                root,
                fingerprint_provider(context, mode_paths),
            )
            fingerprint_targets = _fingerprint_targets(
                root,
                mode_paths,
                full_paths_normalised,
                extra=engine_fingerprints,
            )
            file_hashes = collect_file_hashes(root, fingerprint_targets)

            cached_run = cache.get(cache_key, file_hashes)
            if cached_run:
                logger.info("Using cached diagnostics for %s:%s", engine.name, mode)
                runs.append(
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
                        overrides=[dict(item) for item in cached_run.overrides],
                        category_mapping={k: list(v) for k, v in cached_run.category_mapping.items()},
                    )
                )
                continue

            result = engine.run(context, mode_paths)
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
            )

            runs.append(
                RunResult(
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
                    overrides=[dict(item) for item in engine_options.overrides],
                    category_mapping={k: list(v) for k, v in engine_options.category_mapping.items()},
                )
            )

    cache.save()

    builder = ManifestBuilder(root)
    depth = audit_config.max_depth or 3
    for run in runs:
        builder.add_run(run, max_depth=depth)
    manifest = builder.data

    manifest_target = write_manifest_to or audit_config.manifest_path
    if manifest_target is not None:
        out = manifest_target if manifest_target.is_absolute() else (root / manifest_target)
        builder.write(out)

    should_build_summary = build_summary_output or audit_config.dashboard_json or audit_config.dashboard_markdown or audit_config.dashboard_html
    summary = build_summary(manifest) if should_build_summary else None

    if summary is not None:
        if audit_config.dashboard_json:
            target = audit_config.dashboard_json if audit_config.dashboard_json.is_absolute() else (root / audit_config.dashboard_json)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if audit_config.dashboard_markdown:
            target = audit_config.dashboard_markdown if audit_config.dashboard_markdown.is_absolute() else (root / audit_config.dashboard_markdown)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_markdown(summary), encoding="utf-8")
        if audit_config.dashboard_html:
            target = audit_config.dashboard_html if audit_config.dashboard_html.is_absolute() else (root / audit_config.dashboard_html)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_html(summary), encoding="utf-8")

    error_count = sum(run.severity_counts().get("error", 0) for run in runs)
    warning_count = sum(run.severity_counts().get("warning", 0) for run in runs)

    return AuditResult(
        manifest=manifest,
        runs=runs,
        summary=summary if build_summary_output else None,
        error_count=error_count,
        warning_count=warning_count,
    )
