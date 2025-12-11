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

"""Ratchet orchestration services used by CLI and API layers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ratchetr.core.model_types import LogComponent, SeverityLevel, SignaturePolicy
from ratchetr.logging import structured_extra
from ratchetr.ratchet import apply_auto_update as _apply_auto_update
from ratchetr.ratchet import build_ratchet_from_manifest as _build_ratchet_from_manifest
from ratchetr.ratchet import compare_manifest_to_ratchet as _compare_manifest_to_ratchet
from ratchetr.ratchet import load_ratchet as _load_ratchet
from ratchetr.ratchet import refresh_signatures as _refresh_signatures
from ratchetr.ratchet import write_ratchet as _write_ratchet
from ratchetr.ratchet.io import current_timestamp as _current_timestamp
from ratchetr.ratchet.io import load_manifest as _load_manifest

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from ratchetr.core.type_aliases import RunId
    from ratchetr.manifest.typed import ManifestData
    from ratchetr.ratchet.models import RatchetModel
    from ratchetr.ratchet.summary import RatchetReport

logger: logging.Logger = logging.getLogger("ratchetr.services.ratchet")

__all__ = [
    "RatchetCheckResult",
    "RatchetInfoSnapshot",
    "RatchetInitResult",
    "RatchetRebaselineResult",
    "RatchetServiceError",
    "RatchetUpdateResult",
    "apply_target_overrides",
    "check_ratchet",
    "current_timestamp",
    "describe_ratchet",
    "init_ratchet",
    "load_manifest",
    "load_ratchet",
    "rebaseline_ratchet",
    "refresh_signatures",
    "update_ratchet",
]


class RatchetServiceError(RuntimeError):
    """Base exception type for ratchet service failures."""


class RatchetFileExistsError(RatchetServiceError):
    """Raised when attempting to write a ratchet file that already exists without force flag.

    Attributes:
        path: Path to the existing ratchet file.
    """

    def __init__(self, path: Path) -> None:
        """Initialize error with the conflicting path.

        Args:
            path: Path to the existing ratchet file.
        """
        super().__init__(f"Refusing to overwrite existing ratchet: {path}")
        self.path = path


class RatchetPathRequiredError(RatchetServiceError):
    """Raised when a ratchet operation requires a path but none was provided."""

    def __init__(self) -> None:
        """Initialize the error with a descriptive message."""
        super().__init__("Ratchet path is required for this operation.")


@dataclass(slots=True)
class RatchetInitResult:
    """Result of initializing a new ratchet baseline.

    Attributes:
        model: The newly created ratchet model.
        output_path: Path where the ratchet was written.
    """

    model: RatchetModel
    output_path: Path


@dataclass(slots=True)
class RatchetCheckResult:
    """Result of checking a manifest against a ratchet baseline.

    Attributes:
        report: Detailed comparison report.
        ignore_signature: Whether signature mismatches were ignored.
        warn_signature: Whether signature warnings should be shown.
        exit_code: Computed exit code for the check operation.
    """

    report: RatchetReport
    ignore_signature: bool
    warn_signature: bool
    exit_code: int


@dataclass(slots=True)
class RatchetUpdateResult:
    """Result of updating a ratchet with auto-update logic.

    Attributes:
        report: Comparison report before update.
        updated: The updated ratchet model.
        output_path: Path where the updated ratchet was written, or None if dry-run.
        wrote_file: Whether the file was actually written to disk.
    """

    report: RatchetReport
    updated: RatchetModel
    output_path: Path | None
    wrote_file: bool


@dataclass(slots=True)
class RatchetRebaselineResult:
    """Result of rebaselining a ratchet with refreshed signatures.

    Attributes:
        refreshed: The ratchet model with updated signatures.
        output_path: Path where the refreshed ratchet was written.
    """

    refreshed: RatchetModel
    output_path: Path


@dataclass(slots=True)
class RatchetInfoSnapshot:
    """Structured snapshot of ratchet configuration and display settings.

    Attributes:
        manifest_path: Path to the manifest file.
        ratchet_path: Optional path to the ratchet file.
        runs: Optional filter for specific run IDs.
        severities: Severity levels to include.
        targets: Budget targets for each severity level.
        signature_policy: Policy for handling signature mismatches.
        limit: Maximum number of items to display.
        summary_only: Whether to show only summary information.
    """

    manifest_path: Path
    ratchet_path: Path | None
    runs: Sequence[RunId] | None
    severities: Sequence[SeverityLevel]
    targets: Mapping[str, int]
    signature_policy: SignaturePolicy
    limit: int | None
    summary_only: bool


def _ensure_can_write(path: Path, *, force: bool) -> None:
    """Verify a path can be written and create parent directories.

    Args:
        path: Target file path.
        force: Whether to allow overwriting existing files.

    Raises:
        RatchetFileExistsError: If the file exists and force is False.
    """
    if path.exists() and not force:
        raise RatchetFileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)


def init_ratchet(
    *,
    manifest: ManifestData,
    runs: Sequence[RunId] | None,
    manifest_path: Path,
    severities: Sequence[SeverityLevel] | None,
    targets: Mapping[str, int] | None,
    output_path: Path,
    force: bool,
) -> RatchetInitResult:
    """Build and persist a ratchet baseline from a manifest.

    Args:
        manifest: Manifest data to build the ratchet from.
        runs: Optional filter for specific run IDs to include.
        manifest_path: Path to the manifest file (for logging).
        severities: Optional severity levels to include in baseline.
        targets: Optional custom budget targets per severity.
        output_path: Path where the ratchet file will be written.
        force: Whether to overwrite an existing ratchet file.

    Returns:
        RatchetInitResult containing the created model and output path.
    """
    _ensure_can_write(output_path, force=force)
    logger.info(
        "Initializing ratchet baseline",
        extra=structured_extra(
            component=LogComponent.RATCHET,
            manifest=manifest_path,
            path=output_path,
            details={"runs": len(runs) if runs else "all"},
        ),
    )
    model = _build_ratchet_from_manifest(
        manifest=manifest,
        runs=runs,
        severities=severities or None,
        targets=targets or None,
        manifest_path=str(manifest_path),
    )
    _write_ratchet(output_path, model)
    logger.info(
        "Ratchet baseline written to %s",
        output_path,
        extra=structured_extra(
            component=LogComponent.RATCHET,
            path=output_path,
            details={"runs": len(model.runs)},
        ),
    )
    return RatchetInitResult(model=model, output_path=output_path)


def check_ratchet(
    *,
    manifest: ManifestData,
    ratchet_path: Path | None,
    runs: Sequence[RunId] | None,
    signature_policy: SignaturePolicy,
) -> RatchetCheckResult:
    """Compare a manifest against a ratchet model and compute exit metadata.

    Args:
        manifest: Current manifest data to check.
        ratchet_path: Path to the ratchet baseline file.
        runs: Optional filter for specific run IDs to check.
        signature_policy: How to handle signature mismatches (enforce, warn, ignore).

    Returns:
        RatchetCheckResult with comparison report and exit code.

    Raises:
        RatchetPathRequiredError: If ratchet_path is None.
    """
    if ratchet_path is None:
        raise RatchetPathRequiredError
    ratchet_model = _load_ratchet(ratchet_path)
    report = _compare_manifest_to_ratchet(
        manifest=manifest,
        ratchet=ratchet_model,
        runs=runs,
    )
    ignore_signature = signature_policy in {
        SignaturePolicy.WARN,
        SignaturePolicy.IGNORE,
    }
    warn_signature = signature_policy is SignaturePolicy.WARN and report.has_signature_mismatch()
    exit_code = report.exit_code(ignore_signature=ignore_signature)
    violation_total = sum(len(run.violations) for run in report.runs)
    logger.info(
        "Ratchet check completed: exit=%s violations=%s signature_mismatch=%s",
        exit_code,
        violation_total,
        report.has_signature_mismatch(),
        extra=structured_extra(
            component=LogComponent.RATCHET,
            path=ratchet_path,
            exit_code=exit_code,
            signature_matches=not report.has_signature_mismatch(),
            details={
                "runs": len(report.runs),
                "violations": violation_total,
                "policy": signature_policy.value,
            },
        ),
    )
    if warn_signature and report.has_signature_mismatch():
        logger.warning(
            "Ratchet signature mismatches detected (policy=warn)",
            extra=structured_extra(
                component=LogComponent.RATCHET,
                path=ratchet_path,
                signature_matches=False,
            ),
        )
    return RatchetCheckResult(
        report=report,
        ignore_signature=ignore_signature,
        warn_signature=warn_signature,
        exit_code=exit_code,
    )


# ignore JUSTIFIED: update operation needs explicit configuration parameters;
# collapsing into a config object would obscure the public API
def update_ratchet(  # noqa: PLR0913
    *,
    manifest: ManifestData,
    ratchet_path: Path | None,
    runs: Sequence[RunId] | None,
    generated_at: str,
    target_overrides: Mapping[str, int] | None,
    output_path: Path | None,
    force: bool,
    dry_run: bool,
) -> RatchetUpdateResult:
    """Apply auto-update logic and optionally persist the refreshed ratchet.

    Args:
        manifest: Current manifest data.
        ratchet_path: Path to the existing ratchet file.
        runs: Optional filter for specific run IDs.
        generated_at: Timestamp for the updated ratchet metadata.
        target_overrides: Optional custom budget overrides to apply.
        output_path: Optional custom output path (defaults to ratchet_path).
        force: Whether to overwrite existing files.
        dry_run: If True, skip writing the file.

    Returns:
        RatchetUpdateResult with report, updated model, and write status.

    Raises:
        RatchetPathRequiredError: If ``ratchet_path`` is ``None``.
    """
    if ratchet_path is None:
        raise RatchetPathRequiredError
    logger.info(
        "Updating ratchet %s",
        ratchet_path,
        extra=structured_extra(component=LogComponent.RATCHET, path=ratchet_path),
    )
    ratchet_model = _load_ratchet(ratchet_path)
    report = _compare_manifest_to_ratchet(
        manifest=manifest,
        ratchet=ratchet_model,
        runs=runs,
    )
    updated = _apply_auto_update(
        manifest=manifest,
        ratchet=ratchet_model,
        runs=runs,
        generated_at=generated_at,
    )
    if target_overrides:
        apply_target_overrides(updated, target_overrides)
    write_path = output_path or ratchet_path
    wrote_file = False
    if not dry_run:
        _ensure_can_write(write_path, force=force)
        _write_ratchet(write_path, updated)
        wrote_file = True
        logger.info(
            "Ratchet updated %s",
            write_path,
            extra=structured_extra(
                component=LogComponent.RATCHET,
                path=write_path,
                details={"runs": len(updated.runs)},
            ),
        )
    else:
        logger.debug(
            "Ratchet update dry-run; no file written",
            extra=structured_extra(component=LogComponent.RATCHET, path=ratchet_path),
        )
    return RatchetUpdateResult(
        report=report,
        updated=updated,
        output_path=None if dry_run else write_path,
        wrote_file=wrote_file,
    )


def rebaseline_ratchet(
    *,
    manifest: ManifestData,
    ratchet_path: Path | None,
    runs: Sequence[RunId] | None,
    generated_at: str,
    output_path: Path,
    force: bool,
) -> RatchetRebaselineResult:
    """Refresh ratchet signatures and persist the result.

    Args:
        manifest: Current manifest data.
        ratchet_path: Path to the existing ratchet file.
        runs: Optional filter for specific run IDs.
        generated_at: Timestamp for the refreshed ratchet metadata.
        output_path: Path where the refreshed ratchet will be written.
        force: Whether to overwrite existing files.

    Returns:
        RatchetRebaselineResult with the refreshed model and output path.

    Raises:
        RatchetPathRequiredError: If ``ratchet_path`` is ``None``.
    """
    if ratchet_path is None:
        raise RatchetPathRequiredError
    ratchet_model = _load_ratchet(ratchet_path)
    refreshed = _refresh_signatures(
        manifest=manifest,
        ratchet=ratchet_model,
        runs=runs,
        generated_at=generated_at,
    )
    _ensure_can_write(output_path, force=force)
    _write_ratchet(output_path, refreshed)
    logger.info(
        "Ratchet signatures refreshed to %s",
        output_path,
        extra=structured_extra(
            component=LogComponent.RATCHET,
            path=output_path,
            details={"runs": len(refreshed.runs)},
        ),
    )
    return RatchetRebaselineResult(refreshed=refreshed, output_path=output_path)


# ignore JUSTIFIED: API surface requires a wide parameter list
# for explicit snapshot reporting
def describe_ratchet(  # noqa: PLR0913
    *,
    manifest_path: Path,
    ratchet_path: Path | None,
    runs: Sequence[RunId] | None,
    severities: Sequence[SeverityLevel],
    targets: Mapping[str, int],
    signature_policy: SignaturePolicy,
    limit: int | None,
    summary_only: bool,
) -> RatchetInfoSnapshot:
    """Return a structured snapshot of ratchet configuration inputs.

    Args:
        manifest_path: Path to the manifest file.
        ratchet_path: Optional path to the ratchet file.
        runs: Optional filter for specific run IDs.
        severities: Severity levels to include.
        targets: Budget targets for each severity.
        signature_policy: Policy for signature mismatch handling.
        limit: Maximum items to display.
        summary_only: Whether to show only summary.

    Returns:
        RatchetInfoSnapshot with all configuration details.
    """
    return RatchetInfoSnapshot(
        manifest_path=manifest_path,
        ratchet_path=ratchet_path,
        runs=runs,
        severities=tuple(severities),
        targets=dict(targets),
        signature_policy=signature_policy,
        limit=limit,
        summary_only=summary_only,
    )


def split_target_mapping(
    mapping: Mapping[str, int],
) -> tuple[dict[SeverityLevel, int], dict[str, dict[SeverityLevel, int]]]:
    """Split target mapping into global and per-run budget dictionaries.

    Args:
        mapping: Raw target mapping with keys like "error" or "mypy.warning".

    Returns:
        Tuple of (global_targets, per_run_targets) dictionaries.
    """
    global_targets: dict[SeverityLevel, int] = {}
    per_run: dict[str, dict[SeverityLevel, int]] = {}
    for raw_key, value in mapping.items():
        key = raw_key.strip()
        if not key:
            continue
        budget = max(0, int(value))
        if "." in key:
            run_id, severity_token = key.rsplit(".", 1)
            severity = SeverityLevel.from_str(severity_token)
            run_key = run_id.strip()
            entry = per_run.setdefault(run_key, {})
            entry[severity] = budget
        else:
            severity = SeverityLevel.from_str(key)
            global_targets[severity] = budget
    return global_targets, per_run


def apply_target_overrides(model: RatchetModel, overrides: Mapping[str, int]) -> None:
    """Apply CLI target overrides to a ratchet model in-place.

    Args:
        model: Ratchet model to modify.
        overrides: Target overrides mapping severity levels or run.severity to budgets.
    """
    if not overrides:
        return
    logger.debug(
        "Applying ratchet target overrides",
        extra=structured_extra(
            component=LogComponent.RATCHET,
            details={"overrides": len(overrides)},
        ),
    )
    global_targets, per_run = split_target_mapping(overrides)
    for run_id, run_budget in model.runs.items():
        if global_targets:
            run_budget.targets.update(global_targets)
        if run_id in per_run:
            run_budget.targets.update(per_run[run_id])


# Re-export core ratchet helpers for convenience.
load_manifest = _load_manifest
load_ratchet = _load_ratchet
refresh_signatures = _refresh_signatures
current_timestamp = _current_timestamp
