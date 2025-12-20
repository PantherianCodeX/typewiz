"""Filesystem path discovery for s11r2 progress generation.

This module discovers the s11r2 governance register layout by reading the
`registers/registry_index.md` file and extracting the canonical link targets.

Goals:
- Avoid hardcoding output filenames/paths.
- Enforce that generated outputs are written under `docs/_internal/policy/s11r2/progress/`.
- Provide clear, actionable validation issues when discovery fails.

Conventions
-----------
`registry_index.md` SHOULD annotate at least the following links with tags:

- `<!-- s11r2-input:status_legend -->`
- `<!-- s11r2-output:progress_board -->`
- `<!-- s11r2-output:dashboard -->`

These tags make discovery resilient to future link-text edits.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from scripts.docs.s11r2_progress.md import extract_links
from scripts.docs.s11r2_progress.models import Issue, IssueReport, Severity


@dataclass(frozen=True, slots=True)
class S11R2Paths:
    repo_root: Path
    s11r2_dir: Path
    registers_dir: Path
    registry_index: Path

    status_legend: Path

    generated_progress_board: Path
    generated_dashboard: Path


_TAG_RE = re.compile(
    r"\[[^\]]+\]\((?P<target>[^)]+)\)\s*<!--\s*s11r2-(?P<kind>input|output):(?P<key>[\w-]+)\s*-->"
)

_REQUIRED_INPUT_TAGS: tuple[tuple[str, str], ...] = (("input", "status_legend"),)
_REQUIRED_OUTPUT_TAGS: tuple[tuple[str, str], ...] = (("output", "progress_board"), ("output", "dashboard"))


def _find_registry_index(repo_root: Path) -> Path:
    canonical = repo_root / "docs/_internal/policy/s11r2/registers/registry_index.md"
    if canonical.exists():
        return canonical

    matches = [p for p in repo_root.rglob("registry_index.md") if p.name == "registry_index.md"]
    matches = [m for m in matches if m.as_posix().endswith("/policy/s11r2/registers/registry_index.md")]

    if not matches:
        raise FileNotFoundError("Could not locate docs/_internal/policy/s11r2/registers/registry_index.md")
    if len(matches) > 1:
        raise FileNotFoundError(f"Ambiguous registry_index.md matches: {[m.as_posix() for m in matches]}")
    return matches[0]


def _extract_tagged_targets(index_md: str) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for m in _TAG_RE.finditer(index_md):
        key = (m.group("kind"), m.group("key"))
        out[key] = m.group("target").strip()
    return out


def discover_paths(repo_root: Path) -> tuple[S11R2Paths, IssueReport]:
    issues: list[Issue] = []

    root = repo_root.resolve()
    idx = _find_registry_index(root)
    registers_dir = idx.parent
    s11r2_dir = registers_dir.parent

    idx_text = idx.read_text(encoding="utf-8")

    tagged = _extract_tagged_targets(idx_text)
    links = dict(extract_links(idx_text))

    def _target_from_tag(*, kind: str, key: str, fallback_link_text: str, fallback_target: str) -> str:
        t = tagged.get((kind, key))
        if t is not None:
            return t
        return links.get(fallback_link_text, fallback_target)

    missing_tags = [t for t in (*_REQUIRED_INPUT_TAGS, *_REQUIRED_OUTPUT_TAGS) if t not in tagged]
    for kind, key in missing_tags:
        # Missing tags are warnings (fallback may still succeed), but we want the index to be machine-friendly.
        issues.append(Issue(Severity.WARN, f"registry_index.md: missing recommended tag: <!-- s11r2-{kind}:{key} -->"))

    def _resolve(target: str) -> Path:
        # All link targets are treated as paths relative to registers_dir.
        return (registers_dir / Path(target)).resolve()

    status_legend = _resolve(
        _target_from_tag(kind="input", key="status_legend", fallback_link_text="Status legend", fallback_target="STATUS_LEGEND.md")
    )
    generated_pb = _resolve(
        _target_from_tag(
            kind="output",
            key="progress_board",
            fallback_link_text="Progress board (generated)",
            fallback_target="../progress/progress_board.md",
        )
    )
    generated_dash = _resolve(
        _target_from_tag(
            kind="output",
            key="dashboard",
            fallback_link_text="Dashboard (generated)",
            fallback_target="../progress/dashboard/index.html",
        )
    )

    # Validate required *inputs* exist.
    if not status_legend.exists():
        issues.append(Issue(Severity.ERROR, f"registry_index.md: status legend missing: {status_legend.as_posix()}"))

    # Validate required *outputs* are under the progress directory.
    progress_dir = (s11r2_dir / "progress").resolve()

    for out_path, label in (
        (generated_pb, "Progress board"),
        (generated_dash, "Dashboard"),
    ):
        try:
            out_path.relative_to(progress_dir)
        except ValueError:
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"registry_index.md: output for {label} must be under `{progress_dir.as_posix()}` (got `{out_path.as_posix()}`)",
                )
            )

    paths = S11R2Paths(
        repo_root=root,
        s11r2_dir=s11r2_dir,
        registers_dir=registers_dir,
        registry_index=idx,
        status_legend=status_legend,
        generated_progress_board=generated_pb,
        generated_dashboard=generated_dash,
    )
    return paths, IssueReport(tuple(issues))


__all__ = ["S11R2Paths", "discover_paths"]
