# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper utilities for ratchet CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from ratchetr.core.model_types import DEFAULT_SEVERITIES, SeverityLevel, SignaturePolicy
from ratchetr.core.type_aliases import RunId
from ratchetr.services.ratchet import apply_target_overrides, split_target_mapping

from .args import parse_comma_separated, parse_key_value_entries

if TYPE_CHECKING:
    from collections.abc import Sequence

MANIFEST_CANDIDATE_NAMES: Final[tuple[str, ...]] = (
    "typing_audit.json",
    "typing_audit_manifest.json",
    "reports/typing/typing_audit.json",
    "reports/typing/manifest.json",
)
DEFAULT_RATCHET_FILENAME: Final[Path] = Path(".ratchetr/ratchet.json")


def _coerce_severity_value(value: str | SeverityLevel) -> SeverityLevel:
    """Coerce a severity value to SeverityLevel enum.

    Args:
        value: Either a SeverityLevel enum or a string to convert.

    Returns:
        SeverityLevel: The severity level as an enum value.
    """
    return value if isinstance(value, SeverityLevel) else SeverityLevel.from_str(value)


def parse_target_entries(entries: Sequence[str]) -> dict[str, int]:
    """Parse target budget entries from command-line arguments.

    Converts KEY=VALUE strings into a mapping of severity keys to integer budgets.
    Ensures all budget values are non-negative.

    Args:
        entries: Sequence of strings in KEY=VALUE format (e.g., "errors=0", "warnings=5").

    Returns:
        dict[str, int]: Mapping from severity key to non-negative integer budget.

    Raises:
        SystemExit: If a value cannot be parsed as an integer.
    """
    mapping: dict[str, int] = {}
    if not entries:
        return mapping
    for key, raw_value in parse_key_value_entries(entries, argument="--target"):
        try:
            budget = max(0, int(raw_value))
        # ignore JUSTIFIED: parsing is validated via CLI tests;
        # runtime error path kept for safety
        except ValueError as exc:  # pragma: no cover
            msg = f"Invalid target value '{raw_value}' for key '{key}'"
            raise SystemExit(msg) from exc
        mapping[key] = budget
    return mapping


def normalise_runs(runs: Sequence[str | RunId] | None) -> list[RunId]:
    """Normalize run identifiers to a canonical list of RunId values.

    Strips whitespace from each run identifier and filters out empty entries.

    Args:
        runs: Sequence of run identifiers (strings or RunId), or None.

    Returns:
        list[RunId]: List of normalized RunId values, empty if input is None or empty.
    """
    if not runs:
        return []
    normalised: list[RunId] = []
    for value in runs:
        token = str(value).strip()
        if not token:
            continue
        normalised.append(RunId(token))
    return normalised


def resolve_runs(cli_runs: Sequence[str | RunId] | None, config_runs: Sequence[RunId]) -> list[RunId] | None:
    """Resolve the final list of runs from CLI and config sources.

    Prioritizes CLI-provided runs over config runs. Returns None if neither source
    provides any runs.

    Args:
        cli_runs: Run identifiers from command-line arguments, or None.
        config_runs: Run identifiers from configuration file.

    Returns:
        list[RunId] | None: Resolved list of runs, or None if no runs specified.
    """
    runs = normalise_runs(cli_runs) or normalise_runs(config_runs)
    return runs or None


def resolve_severities(cli_value: str | None, config_values: Sequence[SeverityLevel]) -> list[SeverityLevel]:
    """Resolve the final list of severity levels from CLI and config sources.

    Prioritizes CLI-provided severities over config. Falls back to DEFAULT_SEVERITIES
    if neither source provides values. Removes duplicates while preserving order.

    Args:
        cli_value: Comma-separated severity string from CLI, or None.
        config_values: Sequence of severity levels from configuration.

    Returns:
        list[SeverityLevel]: Deduplicated, ordered list of severity levels.
    """
    raw_values: Sequence[str | SeverityLevel]
    raw_values = parse_comma_separated(cli_value) if cli_value else list(config_values)
    normalised: list[SeverityLevel] = [_coerce_severity_value(value) for value in raw_values if value]
    if not normalised:
        config_normalised: list[SeverityLevel] = [_coerce_severity_value(value) for value in config_values if value]
        default_severities: list[SeverityLevel] = list(DEFAULT_SEVERITIES)
        normalised = config_normalised or default_severities
    seen: set[SeverityLevel] = set()
    ordered: list[SeverityLevel] = []
    for severity in normalised:
        if severity not in seen:
            seen.add(severity)
            ordered.append(severity)
    return ordered


def resolve_signature_policy(cli_value: str | None, config_value: SignaturePolicy) -> SignaturePolicy:
    """Resolve the signature policy from CLI and config sources.

    Prioritizes CLI-provided policy over config. Validates that the CLI value is
    a valid SignaturePolicy.

    Args:
        cli_value: Signature policy string from CLI, or None.
        config_value: Signature policy from configuration.

    Returns:
        SignaturePolicy: The resolved signature policy.

    Raises:
        SystemExit: If the CLI value is not a valid signature policy.
    """
    if cli_value is None:
        return config_value
    try:
        return SignaturePolicy.from_str(cli_value)
    except ValueError as exc:
        readable = ", ".join(policy.value for policy in SignaturePolicy)
        msg = f"Unknown signature policy '{cli_value}'. Valid values: {readable}"
        raise SystemExit(msg) from exc


def resolve_limit(cli_limit: int | None, config_limit: int | None) -> int | None:
    """Resolve the display limit from CLI and config sources.

    Prioritizes CLI-provided limit over config limit.

    Args:
        cli_limit: Display limit from CLI arguments, or None.
        config_limit: Display limit from configuration, or None.

    Returns:
        int | None: The resolved display limit, or None for unlimited.
    """
    return cli_limit if cli_limit is not None else config_limit


def resolve_summary_only(*, cli_summary: bool, config_summary: bool) -> bool:
    """Resolve the summary-only flag from CLI and config sources.

    Returns True if either CLI or config specifies summary-only mode.

    Args:
        cli_summary: Summary-only flag from CLI arguments.
        config_summary: Summary-only flag from configuration.

    Returns:
        bool: True if summary-only mode should be enabled, False otherwise.
    """
    return bool(cli_summary) or config_summary


def resolve_path(project_root: Path, candidate: Path) -> Path:
    """Resolve a path relative to the project root.

    If the candidate path is already absolute, returns it unchanged. Otherwise,
    resolves it relative to the project root.

    Args:
        project_root: The project root directory.
        candidate: The path to resolve (absolute or relative).

    Returns:
        Path: The resolved absolute path.
    """
    return candidate if candidate.is_absolute() else (project_root / candidate).resolve()


def discover_manifest_path(
    project_root: Path,
    *,
    explicit: Path | None,
    configured: Path | None,
) -> Path:
    """Discover the manifest file path using multiple strategies.

    Attempts to find the manifest in the following order:
    1. Explicit path from CLI (must exist)
    2. Configured path from config file (if exists)
    3. Standard candidate locations (typing_audit.json, etc.)

    Args:
        project_root: The project root directory.
        explicit: Explicitly provided manifest path from CLI, or None.
        configured: Configured manifest path from config file, or None.

    Returns:
        Path: The resolved manifest file path.

    Raises:
        SystemExit: If the explicit path doesn't exist or no manifest can be discovered.
    """
    if explicit is not None:
        resolved = resolve_path(project_root, explicit)
        if not resolved.exists():
            msg = f"Manifest not found: {resolved}"
            raise SystemExit(msg)
        return resolved
    if configured is not None:
        resolved = resolve_path(project_root, configured)
        if resolved.exists():
            return resolved
    for name in MANIFEST_CANDIDATE_NAMES:
        candidate = (project_root / name).resolve()
        if candidate.exists():
            return candidate
    msg = "No manifest discovered. Provide --manifest or set 'ratchet.manifest_path' in ratchetr.toml."
    raise SystemExit(msg)


def discover_ratchet_path(
    project_root: Path,
    *,
    explicit: Path | None,
    configured: Path | None,
    require_exists: bool,
) -> Path:
    """Discover the ratchet file path using multiple strategies.

    Determines the ratchet file path in the following order:
    1. Explicit path from CLI
    2. Configured path from config file
    3. Default location (.ratchetr/ratchet.json)

    Args:
        project_root: The project root directory.
        explicit: Explicitly provided ratchet path from CLI, or None.
        configured: Configured ratchet path from config file, or None.
        require_exists: If True, raises SystemExit if the resolved path doesn't exist.

    Returns:
        Path: The resolved ratchet file path.

    Raises:
        SystemExit: If require_exists is True and the file doesn't exist.
    """
    if explicit is not None:
        resolved = resolve_path(project_root, explicit)
    elif configured is not None:
        resolved = resolve_path(project_root, configured)
    else:
        resolved = (project_root / DEFAULT_RATCHET_FILENAME).resolve()
    if require_exists and not resolved.exists():
        msg = f"Ratchet file not found at {resolved}"
        raise SystemExit(msg)
    return resolved


def ensure_parent(path: Path) -> None:
    """Ensure the parent directory of a path exists.

    Creates all parent directories as needed, with no error if they already exist.

    Args:
        path: The path whose parent directory should be ensured.
    """
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
