# Copyright (c) 2024 PantherianCodeX
"""Helper utilities for ratchet CLI commands."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from typewiz.cli_helpers import (
    parse_comma_separated,
    parse_key_value_entries,
)
from typewiz.model_types import SignaturePolicy
from typewiz.ratchet.models import RatchetModel, normalise_severity

DEFAULT_SEVERITIES = ("error", "warning")
MANIFEST_CANDIDATE_NAMES: tuple[str, ...] = (
    "typing_audit.json",
    "typing_audit_manifest.json",
    "reports/typing/typing_audit.json",
    "reports/typing/manifest.json",
)
DEFAULT_RATCHET_FILENAME = Path(".typewiz/ratchet.json")


def parse_target_entries(entries: Sequence[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    if not entries:
        return mapping
    for key, raw_value in parse_key_value_entries(entries, argument="--target"):
        try:
            budget = max(0, int(raw_value))
        except ValueError as exc:  # pragma: no cover - validated via CLI tests
            raise SystemExit(f"Invalid target value '{raw_value}' for key '{key}'") from exc
        mapping[key] = budget
    return mapping


def split_target_mapping(
    mapping: Mapping[str, int],
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    global_targets: dict[str, int] = {}
    per_run: dict[str, dict[str, int]] = {}
    for raw_key, value in mapping.items():
        key = raw_key.strip()
        if not key:
            continue
        budget = max(0, int(value))
        if "." in key:
            run_id, severity_token = key.rsplit(".", 1)
            severity = normalise_severity(severity_token)
            per_run.setdefault(run_id.strip(), {})[severity] = budget
        else:
            severity = normalise_severity(key)
            global_targets[severity] = budget
    return global_targets, per_run


def apply_target_overrides(model: RatchetModel, overrides: Mapping[str, int]) -> None:
    if not overrides:
        return
    global_targets, per_run = split_target_mapping(overrides)
    for run_id, run_budget in model.runs.items():
        if global_targets:
            run_budget.targets.update(global_targets)
        if run_id in per_run:
            run_budget.targets.update(per_run[run_id])


def normalise_runs(runs: Sequence[str] | None) -> list[str]:
    if not runs:
        return []
    return [item.strip() for item in runs if item and item.strip()]


def resolve_runs(cli_runs: Sequence[str] | None, config_runs: Sequence[str]) -> list[str] | None:
    runs = normalise_runs(cli_runs) or normalise_runs(config_runs)
    return runs or None


def resolve_severities(cli_value: str | None, config_values: Sequence[str]) -> list[str]:
    if cli_value:
        values = parse_comma_separated(cli_value)
    else:
        values = list(config_values)
    normalised = [normalise_severity(value) for value in values if value]
    if not normalised:
        config_normalised = [normalise_severity(value) for value in config_values if value]
        normalised = config_normalised or list(DEFAULT_SEVERITIES)
    seen: set[str] = set()
    ordered: list[str] = []
    for severity in normalised:
        if severity not in seen:
            seen.add(severity)
            ordered.append(severity)
    return ordered


def resolve_signature_policy(
    cli_value: str | None, config_value: SignaturePolicy
) -> SignaturePolicy:
    if cli_value is None:
        return config_value
    try:
        return SignaturePolicy.from_str(cli_value)
    except ValueError as exc:
        readable = ", ".join(policy.value for policy in SignaturePolicy)
        raise SystemExit(
            f"Unknown signature policy '{cli_value}'. Valid values: {readable}"
        ) from exc


def resolve_limit(cli_limit: int | None, config_limit: int | None) -> int | None:
    return cli_limit if cli_limit is not None else config_limit


def resolve_summary_only(cli_summary: bool, config_summary: bool) -> bool:
    return bool(cli_summary) or config_summary


def resolve_path(project_root: Path, candidate: Path) -> Path:
    return candidate if candidate.is_absolute() else (project_root / candidate).resolve()


def discover_manifest_path(
    project_root: Path,
    *,
    explicit: Path | None,
    configured: Path | None,
) -> Path:
    if explicit is not None:
        resolved = resolve_path(project_root, explicit)
        if not resolved.exists():
            raise SystemExit(f"Manifest not found: {resolved}")
        return resolved
    if configured is not None:
        resolved = resolve_path(project_root, configured)
        if resolved.exists():
            return resolved
    for name in MANIFEST_CANDIDATE_NAMES:
        candidate = (project_root / name).resolve()
        if candidate.exists():
            return candidate
    raise SystemExit(
        "No manifest discovered. Provide --manifest or set 'ratchet.manifest_path' in typewiz.toml."
    )


def discover_ratchet_path(
    project_root: Path,
    *,
    explicit: Path | None,
    configured: Path | None,
    require_exists: bool,
) -> Path:
    if explicit is not None:
        resolved = resolve_path(project_root, explicit)
    elif configured is not None:
        resolved = resolve_path(project_root, configured)
    else:
        resolved = (project_root / DEFAULT_RATCHET_FILENAME).resolve()
    if require_exists and not resolved.exists():
        raise SystemExit(f"Ratchet file not found at {resolved}")
    return resolved


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


__all__ = [
    "DEFAULT_RATCHET_FILENAME",
    "DEFAULT_SEVERITIES",
    "MANIFEST_CANDIDATE_NAMES",
    "apply_target_overrides",
    "discover_manifest_path",
    "discover_ratchet_path",
    "ensure_parent",
    "normalise_runs",
    "parse_target_entries",
    "resolve_limit",
    "resolve_path",
    "resolve_runs",
    "resolve_severities",
    "resolve_signature_policy",
    "resolve_summary_only",
    "split_target_mapping",
]
