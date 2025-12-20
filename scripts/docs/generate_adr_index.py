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

"""ADR index generator (Phase 0 prerequisite).

This script updates the generated ADR inventory table in:

  docs/_internal/adr/INDEX.md

The generator is intentionally small and deterministic:
- stdlib only
- stable ordering
- safe edits (replaces only the named generated block)

Usage
-----
From repo root:

  python scripts/docs/generate_adr_index.py --write

Validate without writing (CI-friendly):

  python scripts/docs/generate_adr_index.py --check

Print the generated markdown to stdout:

  python scripts/docs/generate_adr_index.py --print

Exit codes
----------
- 0: success
- 1: --check detected that INDEX.md is out of date
- 2: failure (parse error, missing expected directories/files)
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.docs._generated_blocks import GeneratedBlock, GeneratedBlockError, replace_generated_block

if TYPE_CHECKING:
    from collections.abc import Iterable


_ADR_ID_RE = re.compile(r"\bADR[- ]?(?P<id>\d{4})\b", re.IGNORECASE)
_ADR_ID_WIDTH: int = 4
_STATUS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:[*-]\s*)?\*\*Status:\*\*\s*(?P<value>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:[*-]\s*)?Status:\s*(?P<value>.+?)\s*$", re.IGNORECASE),
)
_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:[*-]\s*)?\*\*Date:\*\*\s*(?P<value>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:[*-]\s*)?Date:\s*(?P<value>.+?)\s*$", re.IGNORECASE),
)
_H1_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")


@dataclasses.dataclass(frozen=True)
class AdrDoc:
    rel_path: Path
    title: str
    status: str
    date: str
    adr_id: int | None
    kind: str


def _iter_md_files(adr_dir: Path) -> list[Path]:
    """Return sorted ADR markdown files under the ADR directory.

    Args:
        adr_dir: Root ADR directory to scan.

    Returns:
        Sorted list of ADR markdown file paths.
    """
    ignore = {
        adr_dir / "INDEX.md",
        adr_dir / "COHERENCE_CHECKLIST.md",
    }

    out: list[Path] = []
    for p in adr_dir.rglob("*.md"):
        if p in ignore:
            continue
        if adr_dir / "archive" in p.parents:
            continue
        out.append(p)

    return sorted(out, key=lambda x: x.as_posix().lower())


def _extract_title(lines: list[str], fallback: str) -> str:
    """Extract the first H1 title from lines or return the fallback.

    Args:
        lines: Markdown file lines to scan.
        fallback: Title to use when no H1 is present.

    Returns:
        Extracted title string.
    """
    for ln in lines[:50]:
        m = _H1_RE.match(ln)
        if m:
            return m.group("title").strip()
    return fallback


def _extract_field(lines: Iterable[str], patterns: Iterable[re.Pattern[str]]) -> str:
    """Extract a field value from lines using a list of regex patterns.

    Args:
        lines: Lines to inspect for a matching field.
        patterns: Regex patterns that capture a "value" group.

    Returns:
        The first matching field value, or an empty string.
    """
    for ln in lines:
        for pat in patterns:
            m = pat.match(ln)
            if m:
                return m.group("value").strip()
    return ""


def _extract_adr_id(path: Path, title: str) -> int | None:
    """Extract a numeric ADR id from the title or path.

    Args:
        path: ADR file path (relative to ADR root).
        title: Extracted ADR title.

    Returns:
        Parsed ADR id, or None if not found.
    """
    # Prefer explicit ADR number.
    for s in (title, path.name, str(path)):
        m = _ADR_ID_RE.search(s)
        if m:
            try:
                return int(m.group("id"))
            except ValueError:
                return None

    # Fallback: directory name like docs/_internal/adr/0001/... (working drafts).
    parts = [p for p in path.parts if p.isdigit() and len(p) == _ADR_ID_WIDTH]
    if parts:
        try:
            return int(parts[0])
        except ValueError:
            return None

    return None


def _classify_kind(path: Path, title: str) -> str:
    """Classify the ADR document kind based on its path and title.

    Args:
        path: ADR file path (relative to ADR root).
        title: Extracted ADR title.

    Returns:
        Human-readable ADR kind label.
    """
    lower_name = path.name.lower()
    if "draft-2" in lower_name or lower_name.startswith("adr-"):
        return "Legacy draft-2"
    if _ADR_ID_RE.search(title):
        return "ADR draft"
    if any(part.isdigit() and len(part) == _ADR_ID_WIDTH for part in path.parts):
        return "Working draft"
    return "Working note"


def load_adr_docs(*, repo_root: Path) -> tuple[AdrDoc, ...]:
    """Load ADR documents from the repository root.

    Args:
        repo_root: Repository root directory.

    Returns:
        Sorted tuple of ADR document metadata.

    Raises:
        FileNotFoundError: If the ADR directory does not exist.
    """
    adr_dir = repo_root / "docs" / "_internal" / "adr"
    if not adr_dir.is_dir():
        msg = f"ADR directory not found: {adr_dir}"
        raise FileNotFoundError(msg)

    docs: list[AdrDoc] = []
    for p in _iter_md_files(adr_dir):
        rel = p.relative_to(adr_dir)
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        title = _extract_title(lines, fallback=rel.as_posix())
        status = _extract_field(lines, _STATUS_PATTERNS)
        date = _extract_field(lines, _DATE_PATTERNS)
        adr_id = _extract_adr_id(rel, title)
        kind = _classify_kind(rel, title)
        docs.append(
            AdrDoc(
                rel_path=rel,
                title=title,
                status=status,
                date=date,
                adr_id=adr_id,
                kind=kind,
            )
        )

    docs_sorted = sorted(
        docs,
        key=lambda d: (-(d.adr_id if d.adr_id is not None else -1), d.rel_path.as_posix().lower()),
    )
    return tuple(docs_sorted)


def render_index_table(docs: Iterable[AdrDoc]) -> str:
    """Render the ADR inventory table as markdown.

    Args:
        docs: ADR document metadata entries.

    Returns:
        Markdown table string for the ADR inventory.
    """
    lines: list[str] = []
    lines.extend([
        "## ADR inventory (generated)",
        "",
        "| ADR | Type | Title | Status | Date | File |",
        "| ---: | --- | --- | --- | --- | --- |",
    ])

    any_rows = False
    for d in docs:
        any_rows = True
        adr = f"{d.adr_id:0{_ADR_ID_WIDTH}d}" if d.adr_id is not None else "—"
        status = d.status or ""
        date = d.date or ""
        link = f"[{d.rel_path.as_posix()}]({d.rel_path.as_posix()})"
        title = d.title.replace("|", "\\|")
        lines.append(f"| {adr} | {d.kind} | {title} | {status} | {date} | {link} |")

    if not any_rows:
        lines.append("| — | (none) | (no ADR files found) |  |  |  |")

    return "\n".join(lines).rstrip() + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the ADR index generator.

    Args:
        argv: CLI arguments (excluding the executable).

    Returns:
        Parsed argparse namespace.
    """
    p = argparse.ArgumentParser(description="Generate docs/_internal/adr/INDEX.md ADR inventory block")
    p.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current working directory)",
    )
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--write", action="store_true", help="Write updated INDEX.md in place")
    g.add_argument("--check", action="store_true", help="Exit non-zero if INDEX.md would change")
    g.add_argument("--print", dest="do_print", action="store_true", help="Print generated markdown")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    """CLI entrypoint for ADR index generation.

    Args:
        argv: CLI arguments (excluding the executable).

    Returns:
        Exit code (0 for success).

    Raises:
        RuntimeError: If generated-block markers are malformed.
    """
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    try:
        docs = load_adr_docs(repo_root=repo_root)
        table_md = render_index_table(docs)

        if args.do_print:
            sys.stdout.write(table_md)
            return 0

        index_path = repo_root / "docs" / "_internal" / "adr" / "INDEX.md"
        block = GeneratedBlock(label="adr-index")
        prior = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

        try:
            expected = replace_generated_block(content=prior, block=block, replacement=table_md)
        except GeneratedBlockError as e:
            raise RuntimeError(str(e)) from e

        if args.check:
            return 0 if expected == prior else 1

        # Default behavior (and --write): apply the update.
        if expected != prior:
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(expected, encoding="utf-8")

    # ignore JUSTIFIED: CLI entrypoint should catch unexpected errors and report them.
    except Exception as e:  # pylint: disable=broad-exception-caught
        sys.stderr.write(f"error: {e}\n")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
