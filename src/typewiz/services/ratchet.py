# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Ratchet orchestration services used by CLI and API layers."""

from __future__ import annotations  # noqa: I001

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from typewiz.core.model_types import LogComponent, SeverityLevel, SignaturePolicy
from typewiz.core.type_aliases import RunId
from typewiz.logging import structured_extra
from typewiz.manifest.typed import ManifestData
from typewiz.ratchet import apply_auto_update as _apply_auto_update
from typewiz.ratchet import build_ratchet_from_manifest as _build_ratchet_from_manifest
from typewiz.ratchet import compare_manifest_to_ratchet as _compare_manifest_to_ratchet
from typewiz.ratchet import load_ratchet as _load_ratchet
from typewiz.ratchet import refresh_signatures as _refresh_signatures
from typewiz.ratchet import write_ratchet as _write_ratchet
from typewiz.ratchet.io import current_timestamp as _current_timestamp
from typewiz.ratchet.io import load_manifest as _load_manifest
from typewiz.ratchet.models import RatchetModel
from typewiz.ratchet.summary import RatchetReport

logger: logging.Logger = logging.getLogger("typewiz.services.ratchet")

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
    def __init__(self, path: Path) -> None:
        super().__init__(f"Refusing to overwrite existing ratchet: {path}")
        self.path = path


class RatchetPathRequiredError(RatchetServiceError):
    def __init__(self) -> None:
        super().__init__("Ratchet path is required for this operation.")


@dataclass(slots=True)
class RatchetInitResult:
    model: RatchetModel
    output_path: Path


@dataclass(slots=True)
class RatchetCheckResult:
    report: RatchetReport
    ignore_signature: bool
    warn_signature: bool
    exit_code: int


@dataclass(slots=True)
class RatchetUpdateResult:
    report: RatchetReport
    updated: RatchetModel
    output_path: Path | None
    wrote_file: bool


@dataclass(slots=True)
class RatchetRebaselineResult:
    refreshed: RatchetModel
    output_path: Path


@dataclass(slots=True)
class RatchetInfoSnapshot:
    manifest_path: Path
    ratchet_path: Path | None
    runs: Sequence[RunId] | None
    severities: Sequence[SeverityLevel]
    targets: Mapping[str, int]
    signature_policy: SignaturePolicy
    limit: int | None
    summary_only: bool


def _ensure_can_write(path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise RatchetFileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)


def init_ratchet(  # noqa: PLR0913
    *,
    manifest: ManifestData,
    runs: Sequence[RunId] | None,
    manifest_path: Path,
    severities: Sequence[SeverityLevel] | None,
    targets: Mapping[str, int] | None,
    output_path: Path,
    force: bool,
) -> RatchetInitResult:
    """Build and persist a ratchet baseline."""

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
    """Compare a manifest against a ratchet model and compute exit metadata."""

    if ratchet_path is None:
        raise RatchetPathRequiredError()
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
    """Apply auto-update logic and optionally persist the refreshed ratchet."""

    if ratchet_path is None:
        raise RatchetPathRequiredError()
    logger.info(
        "Updating ratchet %s",
        ratchet_path,
        extra=structured_extra(component=LogComponent.RATCHET, path=ratchet_path),
    )
    ratchet_model = _load_ratchet(ratchet_path)
    if target_overrides:
        apply_target_overrides(ratchet_model, target_overrides)
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


def rebaseline_ratchet(  # noqa: PLR0913
    *,
    manifest: ManifestData,
    ratchet_path: Path | None,
    runs: Sequence[RunId] | None,
    generated_at: str,
    output_path: Path,
    force: bool,
) -> RatchetRebaselineResult:
    """Refresh ratchet signatures and persist the result."""

    if ratchet_path is None:
        raise RatchetPathRequiredError()
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
    """Return a structured snapshot of ratchet configuration inputs."""

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
    """Apply CLI target overrides to a ratchet model in-place."""

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
