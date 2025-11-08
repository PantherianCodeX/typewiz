# Copyright (c) 2024 PantherianCodeX
"""Ratchet CLI command implementation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from typewiz._internal.utils import normalise_enums_for_json, resolve_project_root
from typewiz.cli.helpers import (
    DEFAULT_RATCHET_FILENAME,
    apply_target_overrides,
    discover_manifest_path,
    discover_ratchet_path,
    echo,
    ensure_parent,
    parse_target_entries,
    register_argument,
    resolve_limit,
    resolve_path,
    resolve_runs,
    resolve_severities,
    resolve_signature_policy,
    resolve_summary_only,
)
from typewiz.config import RatchetConfig, load_config
from typewiz.core.model_types import DataFormat, RatchetAction, SignaturePolicy
from typewiz.core.type_aliases import RunId
from typewiz.manifest.typed import ManifestData
from typewiz.ratchet import (
    apply_auto_update as ratchet_apply_auto_update,
)
from typewiz.ratchet import (
    build_ratchet_from_manifest as ratchet_build_from_manifest,
)
from typewiz.ratchet import (
    compare_manifest_to_ratchet as ratchet_compare_manifest,
)
from typewiz.ratchet import (
    load_ratchet,
    write_ratchet,
)
from typewiz.ratchet import (
    refresh_signatures as ratchet_refresh_signatures,
)
from typewiz.ratchet.io import current_timestamp
from typewiz.ratchet.io import load_manifest as load_ratchet_manifest


@dataclass(slots=True)
class RatchetContext:
    project_root: Path
    config: RatchetConfig
    manifest_path: Path
    ratchet_path: Path | None
    manifest_payload: ManifestData
    runs: Sequence[RunId] | None
    signature_policy: SignaturePolicy
    limit: int | None
    summary_only: bool

    @property
    def generated_at(self) -> str:
        """Return the generation timestamp for the manifest payload."""
        value = self.manifest_payload.get("generatedAt")
        if isinstance(value, str) and value:
            return value
        return current_timestamp()


class SubparserRegistry(Protocol):
    def add_parser(
        self, *args: Any, **kwargs: Any
    ) -> argparse.ArgumentParser: ...  # pragma: no cover - stub


def register_ratchet_command(subparsers: SubparserRegistry) -> None:
    """Attach the ratchet command and subcommands to the CLI."""
    ratchet = subparsers.add_parser(
        "ratchet",
        help="Manage per-file ratchet budgets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ratchet_sub = ratchet.add_subparsers(dest="action", required=True)

    _register_init_parser(ratchet_sub)
    _register_check_parser(ratchet_sub)
    _register_update_parser(ratchet_sub)
    _register_rebaseline_parser(ratchet_sub)
    _register_info_parser(ratchet_sub)


def execute_ratchet(args: argparse.Namespace) -> int:
    """Execute the ratchet command based on parsed arguments.

    Returns:
        int: Process exit code for the ratchet command.

    Raises:
        SystemExit: If an unknown ratchet action is requested.

    """
    config = load_config(None)
    project_root = resolve_project_root(None)
    ratchet_cfg = config.ratchet

    action_value = args.action
    try:
        action = (
            action_value
            if isinstance(action_value, RatchetAction)
            else RatchetAction.from_str(action_value)
        )
    except ValueError as exc:  # pragma: no cover - argparse prevents invalid choices
        raise SystemExit(str(exc)) from exc
    explicit_manifest: Path | None = getattr(args, "manifest", None)
    explicit_ratchet: Path | None = getattr(args, "ratchet", None)

    manifest_path = discover_manifest_path(
        project_root,
        explicit=explicit_manifest,
        configured=ratchet_cfg.manifest_path,
    )
    ratchet_path = discover_ratchet_path(
        project_root,
        explicit=explicit_ratchet,
        configured=ratchet_cfg.output_path,
        require_exists=action
        in {RatchetAction.CHECK, RatchetAction.UPDATE, RatchetAction.REBASELINE_SIGNATURE},
    )

    manifest_payload = load_ratchet_manifest(manifest_path)
    runs_choice = resolve_runs(getattr(args, "runs", None), ratchet_cfg.runs)
    signature_policy = resolve_signature_policy(
        getattr(args, "signature_policy", None),
        ratchet_cfg.signature,
    )
    limit_value = resolve_limit(getattr(args, "limit", None), ratchet_cfg.limit)
    summary_only = resolve_summary_only(
        getattr(args, "summary_only", False),
        ratchet_cfg.summary_only,
    )

    context = RatchetContext(
        project_root=project_root,
        config=ratchet_cfg,
        manifest_path=manifest_path,
        ratchet_path=ratchet_path,
        manifest_payload=manifest_payload,
        runs=runs_choice,
        signature_policy=signature_policy,
        limit=limit_value,
        summary_only=summary_only,
    )

    echo(f"[typewiz] Using manifest: {context.manifest_path}")
    if context.ratchet_path:
        echo(f"[typewiz] Using ratchet: {context.ratchet_path}")

    if action is RatchetAction.INIT:
        return handle_init(context, args)
    if action is RatchetAction.CHECK:
        return handle_check(context, args)
    if action is RatchetAction.UPDATE:
        return handle_update(context, args)
    if action is RatchetAction.REBASELINE_SIGNATURE:
        return handle_rebaseline(context, args)
    if action is RatchetAction.INFO:
        return handle_info(context)
    raise SystemExit(f"Unknown ratchet action: {action}")


def _register_init_parser(subparsers: SubparserRegistry) -> None:
    ratchet_init = subparsers.add_parser(
        RatchetAction.INIT.value,
        help="Create a ratchet budget from a manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    init_inputs = ratchet_init.add_argument_group("Inputs & Discovery")
    init_budget = ratchet_init.add_argument_group("Budget Settings")
    init_output = ratchet_init.add_argument_group("Output")

    register_argument(
        init_inputs,
        "--manifest",
        type=Path,
        default=None,
        help="Manifest to use as the baseline.",
    )
    register_argument(
        init_output,
        "--output",
        type=Path,
        default=None,
        help="Destination for the generated ratchet file.",
    )
    register_argument(
        init_inputs,
        "--run",
        dest="runs",
        action="append",
        default=None,
        help="Limit to runs (tool:mode). Repeatable.",
    )
    register_argument(
        init_budget,
        "--severities",
        default=None,
        help="Comma-separated severities to track (default: errors,warnings).",
    )
    register_argument(
        init_budget,
        "--target",
        dest="targets",
        action="append",
        default=[],
        help="Target budgets per severity (e.g. --target errors=0). Repeatable.",
    )
    register_argument(
        init_output,
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )


def _register_check_parser(subparsers: SubparserRegistry) -> None:
    ratchet_check = subparsers.add_parser(
        RatchetAction.CHECK.value,
        help="Compare a manifest against a ratchet budget",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    check_inputs = ratchet_check.add_argument_group("Inputs & Discovery")
    check_display = ratchet_check.add_argument_group("Display")
    check_policy = ratchet_check.add_argument_group("Policy")

    register_argument(
        check_inputs,
        "--manifest",
        type=Path,
        default=None,
        help="Manifest produced by the latest audit.",
    )
    register_argument(
        check_inputs,
        "--ratchet",
        type=Path,
        default=None,
        help="Ratchet budget file.",
    )
    register_argument(
        check_inputs,
        "--run",
        dest="runs",
        action="append",
        default=None,
        help="Limit to runs (tool:mode). Repeatable.",
    )
    register_argument(
        check_display,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.TABLE.value,
        help="Output format.",
    )
    register_argument(
        check_policy,
        "--signature-policy",
        choices=[policy.value for policy in SignaturePolicy],
        default=None,
        help="How to handle signature mismatches (fail, warn, ignore).",
    )
    register_argument(
        check_display,
        "--limit",
        type=int,
        default=None,
        help="Maximum entries to display per section (default: unlimited).",
    )
    register_argument(
        check_display,
        "--summary-only",
        action="store_true",
        help="Collapse output to summary lines only.",
    )


def _register_update_parser(subparsers: SubparserRegistry) -> None:
    ratchet_update = subparsers.add_parser(
        RatchetAction.UPDATE.value,
        help="Update ratchet budgets using a manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    update_inputs = ratchet_update.add_argument_group("Inputs & Discovery")
    update_budget = ratchet_update.add_argument_group("Budget Settings")
    update_output = ratchet_update.add_argument_group("Output")
    update_display = ratchet_update.add_argument_group("Display")

    register_argument(
        update_inputs,
        "--manifest",
        type=Path,
        default=None,
        help="Manifest produced by the latest audit.",
    )
    register_argument(
        update_inputs,
        "--ratchet",
        type=Path,
        default=None,
        help="Existing ratchet file to update.",
    )
    register_argument(
        update_output,
        "--output",
        type=Path,
        default=None,
        help="Optional destination for the updated ratchet (defaults to --ratchet).",
    )
    register_argument(
        update_inputs,
        "--run",
        dest="runs",
        action="append",
        default=None,
        help="Limit to runs (tool:mode). Repeatable.",
    )
    register_argument(
        update_budget,
        "--target",
        dest="targets",
        action="append",
        default=[],
        help="Override targets per severity (e.g. --target warnings=5). Repeatable.",
    )
    register_argument(
        update_output,
        "--dry-run",
        action="store_true",
        help="Preview the updated budgets without writing them.",
    )
    register_argument(
        update_output,
        "--force",
        action="store_true",
        help="Allow overwriting the existing ratchet when not using --dry-run.",
    )
    register_argument(
        update_display,
        "--limit",
        type=int,
        default=None,
        help="Maximum entries to display per section (default: unlimited).",
    )
    register_argument(
        update_display,
        "--summary-only",
        action="store_true",
        help="Collapse output to summary lines only.",
    )


def _register_rebaseline_parser(subparsers: SubparserRegistry) -> None:
    ratchet_rebaseline = subparsers.add_parser(
        RatchetAction.REBASELINE_SIGNATURE.value,
        help="Refresh engine signature data without changing budgets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    rebase_inputs = ratchet_rebaseline.add_argument_group("Inputs & Discovery")
    rebase_output = ratchet_rebaseline.add_argument_group("Output")

    register_argument(
        rebase_inputs,
        "--manifest",
        type=Path,
        default=None,
        help="Manifest reflecting the desired engine configuration.",
    )
    register_argument(
        rebase_inputs,
        "--ratchet",
        type=Path,
        default=None,
        help="Existing ratchet file to update.",
    )
    register_argument(
        rebase_inputs,
        "--run",
        dest="runs",
        action="append",
        default=None,
        help="Limit signature refresh to runs (tool:mode). Repeatable.",
    )
    register_argument(
        rebase_output,
        "--output",
        type=Path,
        default=None,
        help="Optional destination for the refreshed ratchet (defaults to --ratchet).",
    )
    register_argument(
        rebase_output,
        "--force",
        action="store_true",
        help="Allow overwriting the existing ratchet when not specifying --output.",
    )


def _register_info_parser(subparsers: SubparserRegistry) -> None:
    ratchet_info = subparsers.add_parser(
        RatchetAction.INFO.value,
        help="Show resolved ratchet configuration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    info_inputs = ratchet_info.add_argument_group("Inputs & Discovery")
    register_argument(
        info_inputs,
        "--manifest",
        type=Path,
        default=None,
        help="Manifest path to use when resolving defaults.",
    )
    register_argument(
        info_inputs,
        "--ratchet",
        type=Path,
        default=None,
        help="Ratchet path to use when resolving defaults.",
    )
    register_argument(
        info_inputs,
        "--run",
        dest="runs",
        action="append",
        default=None,
        help="Runs that would be affected (tool:mode). Repeatable.",
    )


def handle_init(context: RatchetContext, args: argparse.Namespace) -> int:
    output: Path | None = getattr(args, "output", None)
    if output is None:
        output = context.ratchet_path or (context.project_root / DEFAULT_RATCHET_FILENAME).resolve()
    else:
        output = resolve_path(context.project_root, output)

    if output.exists() and not getattr(args, "force", False):
        echo(f"[typewiz] Refusing to overwrite existing ratchet: {output}", err=True)
        return 1

    severities = resolve_severities(
        getattr(args, "severities", None),
        context.config.severities,
    )

    targets = dict(context.config.targets)
    targets.update(parse_target_entries(getattr(args, "targets", [])))

    ratchet_model = ratchet_build_from_manifest(
        manifest=context.manifest_payload,
        runs=context.runs,
        severities=severities or None,
        targets=targets or None,
        manifest_path=str(context.manifest_path),
    )
    ensure_parent(output)
    write_ratchet(output, ratchet_model)
    echo(f"[typewiz] Ratchet baseline written to {output}")
    return 0


def handle_check(context: RatchetContext, args: argparse.Namespace) -> int:
    if context.ratchet_path is None:
        raise SystemExit("Ratchet path is required for ratchet check.")
    ratchet_model = load_ratchet(context.ratchet_path)
    report = ratchet_compare_manifest(
        manifest=context.manifest_payload,
        ratchet=ratchet_model,
        runs=context.runs,
    )
    ignore_signature = context.signature_policy in {
        SignaturePolicy.WARN,
        SignaturePolicy.IGNORE,
    }
    warn_signature = (
        context.signature_policy is SignaturePolicy.WARN and report.has_signature_mismatch()
    )
    output_format = DataFormat.from_str(getattr(args, "format", DataFormat.TABLE.value))

    if output_format is DataFormat.JSON:
        echo(json.dumps(normalise_enums_for_json(report.to_payload()), indent=2))
    else:
        for line in report.format_lines(
            ignore_signature=ignore_signature,
            limit=context.limit,
            summary_only=context.summary_only,
        ):
            echo(line)

    exit_code = report.exit_code(ignore_signature=ignore_signature)
    if warn_signature:
        echo("[typewiz] Signature mismatch (policy=warn)", err=True)
    return exit_code


def handle_update(context: RatchetContext, args: argparse.Namespace) -> int:
    if context.ratchet_path is None:
        raise SystemExit("Ratchet path is required for ratchet update.")
    ratchet_model = load_ratchet(context.ratchet_path)
    cli_targets = parse_target_entries(getattr(args, "targets", []))
    if cli_targets:
        apply_target_overrides(ratchet_model, cli_targets)

    report = ratchet_compare_manifest(
        manifest=context.manifest_payload,
        ratchet=ratchet_model,
        runs=context.runs,
    )
    for line in report.format_lines(
        ignore_signature=True,
        limit=context.limit,
        summary_only=context.summary_only,
    ):
        echo(line)

    updated = ratchet_apply_auto_update(
        manifest=context.manifest_payload,
        ratchet=ratchet_model,
        runs=context.runs,
        generated_at=context.generated_at,
    )

    if getattr(args, "dry_run", False):
        echo("[typewiz] Dry-run mode; ratchet not written.")
        return 0

    output: Path | None = getattr(args, "output", None)
    if output is None:
        output = context.ratchet_path or (context.project_root / DEFAULT_RATCHET_FILENAME).resolve()
    else:
        output = resolve_path(context.project_root, output)

    if output.exists() and not getattr(args, "force", False):
        echo(f"[typewiz] Refusing to overwrite existing ratchet: {output}", err=True)
        return 1

    ensure_parent(output)
    write_ratchet(output, updated)
    echo(f"[typewiz] Ratchet updated at {output}")
    return 0


def handle_rebaseline(context: RatchetContext, args: argparse.Namespace) -> int:
    if context.ratchet_path is None:
        raise SystemExit("Ratchet path is required for ratchet rebaseline.")
    ratchet_model = load_ratchet(context.ratchet_path)

    target_path: Path | None = getattr(args, "output", None)
    target_path = (
        context.ratchet_path
        if target_path is None
        else resolve_path(context.project_root, target_path)
    )

    if target_path.exists() and not getattr(args, "force", False):
        echo(f"[typewiz] Refusing to overwrite existing ratchet: {target_path}", err=True)
        return 1

    refreshed = ratchet_refresh_signatures(
        manifest=context.manifest_payload,
        ratchet=ratchet_model,
        runs=context.runs,
        generated_at=context.generated_at,
    )
    ensure_parent(target_path)
    write_ratchet(target_path, refreshed)
    echo(f"[typewiz] Ratchet signatures refreshed at {target_path}")
    return 0


def handle_info(context: RatchetContext) -> int:
    echo("[typewiz] Ratchet configuration summary")
    echo(f"  manifest: {context.manifest_path}")
    echo(f"  ratchet: {context.ratchet_path or '<computed>'}")
    echo(f"  runs: {', '.join(context.runs) if context.runs else '<all>'}")
    severities = resolve_severities(None, context.config.severities)
    echo(f"  severities: {', '.join(severity.value for severity in severities)}")

    if context.config.targets:
        for key, value in sorted(context.config.targets.items()):
            echo(f"  target[{key}] = {value}")
    else:
        echo("  targets: <none>")

    echo(f"  signature policy: {context.config.signature}")
    limit_display = str(context.limit) if context.limit is not None else "<none>"
    echo(f"  display limit: {limit_display}")
    echo(f"  summary-only: {'yes' if context.summary_only else 'no'}")
    return 0


__all__ = [
    "RatchetContext",
    "execute_ratchet",
    "handle_check",
    "handle_info",
    "handle_init",
    "handle_rebaseline",
    "handle_update",
    "register_ratchet_command",
]
