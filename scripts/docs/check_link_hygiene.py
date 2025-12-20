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

"""Check link hygiene for docs markdown files.

This script scans docs markdown files for local link targets and reports
missing targets. It is intentionally conservative (no network checks).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_LINK_OPEN = "]("


@dataclass(frozen=True, slots=True)
class LinkIssue:
    source: Path
    target: str


def _iter_markdown_files(root: Path) -> Iterable[Path]:
    return root.rglob("*.md")


def _normalize_target(target: str) -> str | None:
    target = target.strip()
    if not target:
        return None
    if target.startswith("#"):
        return None
    if target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0].split("?", 1)[0]
    return target or None


def _resolve_target(source: Path, repo_root: Path, target: str) -> Path:
    if target.startswith("/"):
        return repo_root / target.lstrip("/")
    return (source.parent / target).resolve()


def _iter_link_targets(text: str) -> Iterable[str]:
    idx = 0
    while True:
        start = text.find(_LINK_OPEN, idx)
        if start == -1:
            return
        pos = start + len(_LINK_OPEN)
        depth = 1
        while pos < len(text):
            char = text[pos]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if not depth:
                    yield text[start + len(_LINK_OPEN) : pos]
                    idx = pos + 1
                    break
            pos += 1
        else:
            return


def _collect_link_issues(root: Path, *, repo_root: Path) -> list[LinkIssue]:
    issues: list[LinkIssue] = []
    for path in _iter_markdown_files(root):
        text = path.read_text(encoding="utf-8")
        for raw_target in _iter_link_targets(text):
            normalized = _normalize_target(raw_target)
            if normalized is None:
                continue
            resolved = _resolve_target(path, repo_root, normalized)
            if not resolved.exists():
                issues.append(LinkIssue(source=path, target=normalized))
    return issues


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root (default: inferred)",
    )
    parser.add_argument(
        "--docs",
        type=Path,
        action="append",
        default=None,
        help="Docs directory to scan (repeatable).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each missing link target.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run link hygiene checks for docs.

    Args:
        argv: CLI arguments (excluding the executable).

    Returns:
        Exit code (0 for success, 1 for missing link targets).
    """
    args = _parse_args(argv or [])
    repo_root = args.root.resolve()
    if args.docs is None:
        docs_roots = [
            repo_root / "docs/_internal/adr",
            repo_root / "docs/_internal/policy/s11r2",
            repo_root / "docs/cli",
            repo_root / "docs/reference",
        ]
    else:
        docs_roots = list(args.docs)

    issues: list[LinkIssue] = []
    for docs_root in docs_roots:
        issues.extend(_collect_link_issues(docs_root.resolve(), repo_root=repo_root))

    if issues and args.verbose:
        for issue in issues:
            rel_source = issue.source.relative_to(repo_root)
            print(f"{rel_source}: missing link target: {issue.target}")

    if issues:
        print(f"[link-hygiene] missing targets: {len(issues)}")
        return 1

    print("[link-hygiene] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
