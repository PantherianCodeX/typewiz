# Copyright (c) 2024 PantherianCodeX

"""Helpers for cloning and merging audit configuration structures.

These routines provide strongly typed utilities that keep `AuditConfig`
manipulation deterministic and side-effect free.  They are shared between
the API orchestration layer and any tooling that needs to reason about audit
settings.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from .collection_utils import dedupe_preserve, merge_preserve
from .config import AuditConfig, EngineProfile, EngineSettings, PathOverride
from .data_validation import coerce_object_list
from .type_aliases import EngineName


def clone_profile(profile: EngineProfile) -> EngineProfile:
    """Return a deep copy of an ``EngineProfile`` instance."""
    return EngineProfile(
        inherit=profile.inherit,
        plugin_args=list(profile.plugin_args),
        config_file=profile.config_file,
        include=list(profile.include),
        exclude=list(profile.exclude),
    )


def clone_engine_settings_map(
    settings: Mapping[EngineName, EngineSettings],
) -> dict[EngineName, EngineSettings]:
    """Return a mutable copy of an engine-settings mapping."""
    cloned: dict[EngineName, EngineSettings] = {}
    for name, value in settings.items():
        cloned[name] = EngineSettings(
            plugin_args=list(value.plugin_args),
            config_file=value.config_file,
            include=list(value.include),
            exclude=list(value.exclude),
            default_profile=value.default_profile,
            profiles={key: clone_profile(profile) for key, profile in value.profiles.items()},
        )
    return cloned


def merge_engine_settings_map(
    base: Mapping[EngineName, EngineSettings],
    override: Mapping[EngineName, EngineSettings],
) -> dict[EngineName, EngineSettings]:
    """Merge engine settings, cloning results to avoid mutating inputs."""
    result = clone_engine_settings_map(base)
    for name, override_settings in override.items():
        if name not in result:
            result[name] = clone_engine_settings_map({name: override_settings})[name]
            continue
        target = result[name]
        target.plugin_args = merge_preserve(target.plugin_args, override_settings.plugin_args)
        target.include = merge_preserve(target.include, override_settings.include)
        target.exclude = merge_preserve(target.exclude, override_settings.exclude)
        if override_settings.config_file is not None:
            target.config_file = override_settings.config_file
        if override_settings.default_profile is not None:
            target.default_profile = override_settings.default_profile
        for profile_name, override_profile in override_settings.profiles.items():
            if profile_name not in target.profiles:
                target.profiles[profile_name] = clone_profile(override_profile)
                continue
            profile_target = target.profiles[profile_name]
            if override_profile.inherit is not None:
                profile_target.inherit = override_profile.inherit
            if override_profile.config_file is not None:
                profile_target.config_file = override_profile.config_file
            profile_target.plugin_args = merge_preserve(
                profile_target.plugin_args,
                override_profile.plugin_args,
            )
            profile_target.include = merge_preserve(
                profile_target.include,
                override_profile.include,
            )
            profile_target.exclude = merge_preserve(
                profile_target.exclude,
                override_profile.exclude,
            )
    return result


def clone_path_overrides(overrides: Sequence[PathOverride]) -> list[PathOverride]:
    """Clone path override records so that callers can mutate safely."""
    return [
        PathOverride(
            path=override.path,
            engine_settings=clone_engine_settings_map(override.engine_settings),
            active_profiles=dict(override.active_profiles),
        )
        for override in overrides
    ]


def clone_audit_config(source: AuditConfig) -> AuditConfig:
    """Produce a deep copy of an ``AuditConfig`` instance."""
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
        engine_settings=clone_engine_settings_map(source.engine_settings),
        active_profiles=dict(source.active_profiles),
        path_overrides=clone_path_overrides(source.path_overrides),
    )


def merge_audit_configs(base: AuditConfig, override: AuditConfig | None) -> AuditConfig:
    """Merge ``override`` into ``base`` (if supplied) and return a fresh config."""
    base_copy = clone_audit_config(base)
    if override is None:
        return base_copy

    merged = AuditConfig(
        manifest_path=override.manifest_path or base_copy.manifest_path,
        full_paths=override.full_paths or base_copy.full_paths,
        max_depth=override.max_depth or base_copy.max_depth,
        skip_current=(
            override.skip_current if override.skip_current is not None else base_copy.skip_current
        ),
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
        merged.plugin_args[name] = dedupe_preserve(values)
    merged.plugin_args = dict(sorted(merged.plugin_args.items()))

    merged.engine_settings = merge_engine_settings_map(
        base_copy.engine_settings,
        override.engine_settings,
    )
    merged.active_profiles = dict(base_copy.active_profiles)
    merged.active_profiles.update({k: v for k, v in override.active_profiles.items() if v})
    merged.path_overrides = clone_path_overrides(base_copy.path_overrides)
    if override.path_overrides:
        merged.path_overrides.extend(clone_path_overrides(override.path_overrides))
    return merged


def prepare_category_mapping(value: object) -> Mapping[str, Sequence[str]] | None:
    """Normalise raw engine category mappings into a predictable structure."""
    if value is None or not isinstance(value, Mapping):
        return None
    prepared: dict[str, list[str]] = {}
    mapping_value = cast("Mapping[object, object]", value)
    for key_obj, raw_values in mapping_value.items():
        key = str(key_obj)
        raw_list = coerce_object_list(raw_values)
        values = [item.strip() for item in raw_list if isinstance(item, str) and item.strip()]
        if values:
            prepared[key] = values
    return prepared


def normalise_category_mapping(mapping: Mapping[str, Sequence[str]] | None) -> dict[str, list[str]]:
    """Provide a deterministic ordering for category mappings."""
    if mapping is None:
        return {}
    normalised: dict[str, list[str]] = {}
    for key_obj, raw_values in mapping.items():
        key_str = str(key_obj).strip()
        if not key_str:
            continue
        deduped: list[str] = []
        seen: set[str] = set()
        for item in raw_values:
            candidate = item.strip()
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(candidate)
        normalised[key_str] = deduped
    return normalised
