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

"""Ratchet CLI command implementation."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from ratchetr.cli.helpers import (
    DEFAULT_RATCHET_FILENAME,
    StdoutFormat,
    discover_manifest_or_exit,
    discover_ratchet_path,
    echo,
    parse_target_entries,
    register_argument,
    resolve_limit,
    resolve_path,
    resolve_runs,
    resolve_severities,
    resolve_signature_policy,
    resolve_summary_only,
)
from ratchetr.core.model_types import DataFormat, RatchetAction, SignaturePolicy
from ratchetr.json import normalise_enums_for_json
from ratchetr.services.ratchet import (
    RatchetFileExistsError,
    RatchetPathRequiredError,
    RatchetServiceError,
    check_ratchet,
    current_timestamp,
    describe_ratchet,
    init_ratchet,
    rebaseline_ratchet,
    update_ratchet,
)
from ratchetr.services.ratchet import (
    load_manifest as load_ratchet_manifest,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.cli.helpers import CLIContext
    from ratchetr.cli.types import SubparserCollection
    from ratchetr.compat import Never
    from ratchetr.config import RatchetConfig
    from ratchetr.core.type_aliases import RunId
    from ratchetr.manifest.typed import ManifestData


@dataclass(slots=True)
# ignore JUSTIFIED: CLI context aggregates parsed options; attribute count expected
class RatchetContext:  # pylint: disable=too-many-instance-attributes
    """Context object holding all configuration and data for ratchet operations.

    Attributes:
        project_root: Root directory of the project.
        config: Ratchet configuration settings.
        manifest_path: Path to the typing audit manifest file.
        ratchet_path: Path to the ratchet budget file (may be None for init).
        manifest_payload: Loaded manifest data.
        runs: Sequence of run IDs to process, or None for all runs.
        signature_policy: Policy for handling signature mismatches.
        limit: Maximum number of entries to display, or None for unlimited.
        summary_only: Whether to display only summary information.
    """

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
        """Return the generation timestamp for the manifest payload.

        Returns:
            ISO 8601 timestamp string representing when the manifest was generated.
        """
        value = self.manifest_payload.get("generatedAt")
        if isinstance(value, str) and value:
            return value
        return current_timestamp()


def _handle_service_error(exc: RatchetServiceError) -> int:
    """Handle ratchet service errors by printing to stderr and returning error code.

    Args:
        exc: The ratchet service error that occurred.

    Returns:
        int: Exit code 1 indicating failure.
    """
    echo(f"[ratchetr] {exc}", err=True)
    return 1


def _raise_unknown_ratchet_action(action: Never) -> NoReturn:
    msg = f"Unknown ratchet action: {action}"
    raise SystemExit(msg)


def register_ratchet_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None = None,
) -> None:
    """Attach the ratchet command and subcommands to the CLI.

    Args:
        subparsers: Top-level argparse subparser collection to register commands on.
        parents: Shared parent parsers carrying global options.
    """
    ratchet = subparsers.add_parser(
        "ratchet",
        help="Manage per-file ratchet budgets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    ratchet_sub = ratchet.add_subparsers(dest="action", required=True)

    _register_init_parser(ratchet_sub)
    _register_check_parser(ratchet_sub)
    _register_update_parser(ratchet_sub)
    _register_rebaseline_parser(ratchet_sub)
    _register_info_parser(ratchet_sub)


def execute_ratchet(args: argparse.Namespace, cli_context: CLIContext) -> int:
    """Execute the ratchet command based on parsed arguments.

    Args:
        args: Parsed CLI arguments for the ratchet command.
        cli_context: Shared CLI context with resolved paths and configuration.

    Returns:
        Process exit code for the ratchet command.

    Raises:
        SystemExit: If an unknown ratchet action is requested.
    """
    action_value = args.action
    try:
        action = action_value if isinstance(action_value, RatchetAction) else RatchetAction.from_str(action_value)
    # ignore JUSTIFIED: argparse restricts choices;
    # branch guarded by argparse defaults to SystemExit
    except ValueError as exc:  # pragma: no cover
        raise SystemExit(str(exc)) from exc
    config = cli_context.config
    project_root = cli_context.resolved_paths.repo_root
    ratchet_cfg = config.ratchet

    explicit_manifest: Path | None = getattr(args, "manifest", None)
    explicit_ratchet: Path | None = getattr(args, "ratchet", None)

    manifest_path = discover_manifest_or_exit(cli_context, cli_manifest=explicit_manifest)
    ratchet_path = discover_ratchet_path(
        project_root,
        explicit=explicit_ratchet,
        configured=ratchet_cfg.output_path,
        require_exists=action in {RatchetAction.CHECK, RatchetAction.UPDATE, RatchetAction.REBASELINE_SIGNATURE},
    )

    manifest_payload = load_ratchet_manifest(manifest_path)
    runs_choice = resolve_runs(getattr(args, "runs", None), ratchet_cfg.runs)
    signature_policy = resolve_signature_policy(
        getattr(args, "signature_policy", None),
        ratchet_cfg.signature,
    )
    limit_value = resolve_limit(getattr(args, "limit", None), ratchet_cfg.limit)
    summary_only = resolve_summary_only(
        cli_summary=getattr(args, "summary_only", False),
        config_summary=ratchet_cfg.summary_only,
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

    echo(f"[ratchetr] Using manifest: {context.manifest_path}")
    if context.ratchet_path:
        echo(f"[ratchetr] Using ratchet: {context.ratchet_path}")

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
    _raise_unknown_ratchet_action(action)


def _register_init_parser(subparsers: SubparserCollection) -> None:
    """Register the 'ratchet init' subcommand parser.

    Configures the init subcommand with argument groups for inputs, budget settings,
    and output options. This command creates a new ratchet budget file from a manifest.

    Args:
        subparsers: Subparser registry where the init command will be added.
    """
    ratchet_init = subparsers.add_parser(
        RatchetAction.INIT.value,
        help="Create a ratchet budget from a manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    init_inputs = ratchet_init.add_argument_group("Inputs & Discovery")
    init_budget = ratchet_init.add_argument_group("Budget Settings")
    init_output = ratchet_init.add_argument_group("Output")

    register_argument(
        init_output,
        "-s",
        "--save-as",
        "--output",
        dest="output",
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


def _register_check_parser(subparsers: SubparserCollection) -> None:
    """Register the 'ratchet check' subcommand parser.

    Configures the check subcommand with argument groups for inputs, display options,
    and policy settings. This command compares a manifest against ratchet budgets.

    Args:
        subparsers: Subparser registry where the check command will be added.
    """
    ratchet_check = subparsers.add_parser(
        RatchetAction.CHECK.value,
        help="Compare a manifest against a ratchet budget",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    check_inputs = ratchet_check.add_argument_group("Inputs & Discovery")
    check_display = ratchet_check.add_argument_group("Display")

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


def _register_update_parser(subparsers: SubparserCollection) -> None:
    """Register the 'ratchet update' subcommand parser.

    Configures the update subcommand with argument groups for inputs, budget settings,
    output options, and display settings. This command updates ratchet budgets based
    on a new manifest while preserving or modifying target thresholds.

    Args:
        subparsers: Subparser registry where the update command will be added.
    """
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
        "--ratchet",
        type=Path,
        default=None,
        help="Existing ratchet file to update.",
    )
    register_argument(
        update_output,
        "-s",
        "--save-as",
        "--output",
        dest="output",
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


def _register_rebaseline_parser(subparsers: SubparserCollection) -> None:
    """Register the 'ratchet rebaseline-signature' subcommand parser.

    Configures the rebaseline-signature subcommand with argument groups for inputs and
    output options. This command refreshes engine signature data without changing budgets.

    Args:
        subparsers: Subparser registry where the rebaseline-signature command will be added.
    """
    ratchet_rebaseline = subparsers.add_parser(
        RatchetAction.REBASELINE_SIGNATURE.value,
        help="Refresh engine signature data without changing budgets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    rebase_inputs = ratchet_rebaseline.add_argument_group("Inputs & Discovery")
    rebase_output = ratchet_rebaseline.add_argument_group("Output")

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
        "-s",
        "--save-as",
        "--output",
        dest="output",
        type=Path,
        default=None,
        help="Optional destination for the refreshed ratchet (defaults to --ratchet).",
    )
    register_argument(
        rebase_output,
        "--force",
        action="store_true",
        help="Allow overwriting the existing ratchet when not specifying --save-as.",
    )


def _register_info_parser(subparsers: SubparserCollection) -> None:
    """Register the 'ratchet info' subcommand parser.

    Configures the info subcommand with arguments for inputs discovery. This command
    shows the resolved ratchet configuration including manifest path, ratchet path,
    runs, severities, targets, and signature policy.

    Args:
        subparsers: Subparser registry where the info command will be added.
    """
    ratchet_info = subparsers.add_parser(
        RatchetAction.INFO.value,
        help="Show resolved ratchet configuration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    info_inputs = ratchet_info.add_argument_group("Inputs & Discovery")
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
    """Handle the 'ratchet init' command execution.

    Creates a new ratchet budget file from a manifest using the specified severities
    and target budgets. The output path is determined from CLI args, context, or defaults.

    Args:
        context: Ratchet execution context containing configuration and manifest data.
        args: Parsed command-line arguments including output path, severities, targets, and force.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    output: Path | None = getattr(args, "output", None)
    if output is None:
        output = context.ratchet_path or (context.project_root / DEFAULT_RATCHET_FILENAME).resolve()
    else:
        output = resolve_path(context.project_root, output)

    severities = resolve_severities(
        getattr(args, "severities", None),
        context.config.severities,
    )

    targets = dict(context.config.targets)
    targets.update(parse_target_entries(getattr(args, "targets", [])))

    try:
        result = init_ratchet(
            manifest=context.manifest_payload,
            runs=context.runs,
            manifest_path=context.manifest_path,
            severities=severities or None,
            targets=targets or None,
            output_path=output,
            force=getattr(args, "force", False),
        )
    except RatchetServiceError as exc:
        return _handle_service_error(exc)

    echo(f"[ratchetr] Ratchet baseline written to {result.output_path}")
    return 0


def handle_check(context: RatchetContext, args: argparse.Namespace) -> int:
    """Handle the 'ratchet check' command execution.

    Compares the current manifest against ratchet budgets and reports on any violations.
    Output can be formatted as JSON or table format. Returns non-zero exit code if budgets
    are exceeded or signature mismatches fail policy checks.

    Args:
        context: Ratchet execution context containing configuration and manifest data.
        args: Parsed command-line arguments including output format.

    Returns:
        int: Exit code (0 for success, non-zero for budget violations or policy failures).
    """
    try:
        result = check_ratchet(
            manifest=context.manifest_payload,
            ratchet_path=context.ratchet_path,
            runs=context.runs,
            signature_policy=context.signature_policy,
        )
    except RatchetServiceError as exc:
        return _handle_service_error(exc)

    stdout_format = StdoutFormat.from_str(getattr(args, "out", StdoutFormat.TEXT.value))
    output_format = DataFormat.JSON if stdout_format is StdoutFormat.JSON else DataFormat.TABLE

    if output_format is DataFormat.JSON:
        echo(json.dumps(normalise_enums_for_json(result.report.to_payload()), indent=2))
    else:
        for line in result.report.format_lines(
            ignore_signature=result.ignore_signature,
            limit=context.limit,
            summary_only=context.summary_only,
        ):
            echo(line)

    if result.warn_signature:
        echo("[ratchetr] Signature mismatch (policy=warn)", err=True)
    return result.exit_code


def handle_update(context: RatchetContext, args: argparse.Namespace) -> int:
    """Handle the 'ratchet update' command execution.

    Updates ratchet budgets based on a new manifest, optionally applying target overrides.
    Supports dry-run mode for previewing changes without writing to disk. The updated
    ratchet is written to the specified output path or the original ratchet path.

    Args:
        context: Ratchet execution context containing configuration and manifest data.
        args: Parsed command-line arguments including targets, output path, force, and dry-run.

    Returns:
        int: Exit code (always 0 for success).
    """
    cli_targets = parse_target_entries(getattr(args, "targets", []))
    output: Path | None = getattr(args, "output", None)
    output = resolve_path(context.project_root, output) if output else None

    try:
        result = update_ratchet(
            manifest=context.manifest_payload,
            ratchet_path=context.ratchet_path,
            runs=context.runs,
            generated_at=context.generated_at,
            target_overrides=cli_targets,
            output_path=output,
            force=getattr(args, "force", False),
            dry_run=getattr(args, "dry_run", False),
        )
    except RatchetServiceError as exc:
        return _handle_service_error(exc)

    for line in result.report.format_lines(
        ignore_signature=True,
        limit=context.limit,
        summary_only=context.summary_only,
    ):
        echo(line)

    if not result.wrote_file:
        echo("[ratchetr] Dry-run mode; ratchet not written.")
        return 0

    echo(f"[ratchetr] Ratchet updated at {result.output_path}")
    return 0


def handle_rebaseline(context: RatchetContext, args: argparse.Namespace) -> int:
    """Handle the 'ratchet rebaseline-signature' command execution.

    Refreshes engine signature data in the ratchet file without changing budget values.
    This is useful when engine configurations or versions change but budgets should remain
    constant. Writes to the specified output path or updates the original ratchet file.

    Args:
        context: Ratchet execution context containing configuration and manifest data.
        args: Parsed command-line arguments including output path and force flag.

    Returns:
        int: Exit code (0 for success, 1 for failure).

    Raises:
        SystemExit: If the ratchet path cannot be determined.
    """
    target_path: Path | None = getattr(args, "output", None)
    target_path = context.ratchet_path if target_path is None else resolve_path(context.project_root, target_path)
    if target_path is None:
        msg = "Ratchet path is required for ratchet rebaseline."
        raise SystemExit(msg)

    try:
        result = rebaseline_ratchet(
            manifest=context.manifest_payload,
            ratchet_path=context.ratchet_path,
            runs=context.runs,
            generated_at=context.generated_at,
            output_path=target_path,
            force=getattr(args, "force", False),
        )
    except RatchetServiceError as exc:
        return _handle_service_error(exc)

    echo(f"[ratchetr] Ratchet signatures refreshed at {result.output_path}")
    return 0


def handle_info(context: RatchetContext) -> int:
    """Handle the 'ratchet info' command execution.

    Displays the resolved ratchet configuration including manifest path, ratchet path,
    runs, severities, target budgets, signature policy, display limit, and summary mode.
    This helps users understand the effective configuration being used.

    Args:
        context: Ratchet execution context containing configuration and manifest data.

    Returns:
        int: Exit code (always 0 for success).
    """
    severities = resolve_severities(None, context.config.severities)
    snapshot = describe_ratchet(
        manifest_path=context.manifest_path,
        ratchet_path=context.ratchet_path,
        runs=context.runs,
        severities=severities,
        targets=context.config.targets,
        signature_policy=context.config.signature,
        limit=context.limit,
        summary_only=context.summary_only,
    )

    echo("[ratchetr] Ratchet configuration summary")
    echo(f"  manifest: {snapshot.manifest_path}")
    echo(f"  ratchet: {snapshot.ratchet_path or '<computed>'}")
    echo(f"  runs: {', '.join(snapshot.runs) if snapshot.runs else '<all>'}")
    echo(f"  severities: {', '.join(severity.value for severity in snapshot.severities)}")

    if snapshot.targets:
        for key, value in sorted(snapshot.targets.items()):
            echo(f"  target[{key}] = {value}")
    else:
        echo("  targets: <none>")

    echo(f"  signature policy: {snapshot.signature_policy}")
    limit_display = str(snapshot.limit) if snapshot.limit is not None else "<none>"
    echo(f"  display limit: {limit_display}")
    echo(f"  summary-only: {'yes' if snapshot.summary_only else 'no'}")
    return 0


__all__ = [
    "RatchetContext",
    "RatchetFileExistsError",
    "RatchetPathRequiredError",
    "RatchetServiceError",
    "execute_ratchet",
    "handle_check",
    "handle_info",
    "handle_init",
    "handle_rebaseline",
    "handle_update",
    "register_ratchet_command",
]
