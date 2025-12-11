#!/usr/bin/env python3
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

"""Validate ignore justifications for linting, typing, and coverage.

This checker enforces the `# ignore JUSTIFIED: <reason>` convention described
in `CONTRIBUTING.md`. It scans Python source and stub files for:

- Ruff ignores (`# noqa`, `# ruff: noqa`)
- Pylint ignores (`# pylint: disable=...`, `# pylint: skip-file`)
- Type-checker ignores (`# type: ignore[...]`, `# pyright: ignore[...]`)
- Coverage ignores (`# pragma: no cover`)

For every such line, the *immediately preceding* line must be a justification
comment that begins with `# ignore JUSTIFIED:` and contains a short,
human-readable reason. Blank lines or other comments between the justification
and the ignore are not allowed and will be reported as violations.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import io
import json
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def _load_header_block() -> str:
    """Load the shared license header block from the sibling script module.

    This uses the file path directly so the checker can be executed either as
    a module (`python -m scripts.check_ignoress`) or as a
    standalone script (`./scripts/check_ignoress.py`) without
    relying on `sys.path` layout.

    Returns:
        The `HEADER_BLOCK` string defined in `check_license_headers.py`.

    Raises:
        RuntimeError: If the helper module cannot be loaded.
        TypeError: If the helper module does not define a string
            `HEADER_BLOCK` constant.
    """
    module_path = Path(__file__).resolve().parent / "check_license_headers.py"
    spec = importlib.util.spec_from_file_location(
        "ratchetr_scripts_check_license_headers",
        module_path,
    )
    if spec is None or spec.loader is None:
        msg = f"unable to load license header helper from {module_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    header_block = getattr(module, "HEADER_BLOCK", None)
    if not isinstance(header_block, str):
        msg = f"HEADER_BLOCK missing or not a string in {module_path}"
        raise TypeError(msg)
    return header_block


HEADER_BLOCK: str = _load_header_block()

# Maximum allowed length for a single justification line, excluding indentation.
MAX_JUSTIFICATION_LINE_LENGTH: int = 88

# Base markers that identify ignore pragmas in comments.
# These are root forms; specific spellings (e.g. `noqa: F401`)
# are derived from these.
BASE_IGNORE_MARKERS: tuple[str, ...] = (
    "noqa:",
    "ruff:",
    "pylint:",
    "mypy:",
    "pyright:",
    "type:",
    "pragma:",
)

JUSTIFICATION_PREFIX = "# ignore JUSTIFIED:"

# Rule codes for ignore justification policy violations.
RULE_MISSING_JUSTIFICATION = "IGN001"
RULE_EMPTY_JUSTIFICATION = "IGN002"
RULE_INLINE_SPACING = "IGN010"
RULE_COMMENT_PREFIX = "IGN011"
RULE_MULTIPRAGMA_SPACING = "IGN012"
RULE_PRAGMA_POSITION = "IGN013"
RULE_DUPLICATE_JUSTIFICATION_PREFIX = "IGN014"
RULE_FILE_BLOCK_SINGLE_PRAGMA = "IGN021"
RULE_JUSTIFICATION_TOO_LONG = "IGN030"
RULE_DUPLICATE_SOURCE = "IGN050"
RULE_FILE_PLACEMENT = "IGN020"


@dataclass(slots=True)
class IgnoreViolation:
    """Represents a single ignore that violates the justification convention."""

    file: Path
    line: int
    column: int
    code: str
    message: str
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation of the violation.

        Returns:
            Mapping with file path, location, code, message, and sources.
        """
        return {
            "file": str(self.file),
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "message": self.message,
            "sources": list(self.sources),
        }

    def format_cli(self, root: Path) -> str:
        """Format the violation in a standard linter style.

        Args:
            root: Repository root used to compute relative paths.

        Returns:
            A string of the form `path:line:column: CODE [sources] message`.
        """
        try:
            rel = self.file.relative_to(root)
        except ValueError:
            rel = self.file
        sources_label = ""
        if self.sources:
            joined = ",".join(self.sources)
            sources_label = f" [{joined}]"
        return f"{rel}:{self.line}:{self.column}: {self.code}{sources_label} {self.message}"


def _detect_sources(comment: str) -> tuple[str, ...]:
    """Infer the logical sources (tools) for an ignore comment.

    Returns:
        Tuple of logical source labels (e.g. `("ruff", "mypy")`).
    """
    lowered = comment.lower()
    sources: list[str] = []
    if "# noqa" in lowered or "#noqa" in lowered or "noqa:" in lowered or "ruff:" in lowered:
        sources.append("ruff")
    if "pylint:" in lowered:
        sources.append("pylint")
    if "mypy:" in lowered or "type: ignore" in lowered:
        sources.append("mypy")
    if "pyright:" in lowered:
        sources.append("pyright")
    if "pragma:" in lowered:
        sources.append("coverage")
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_sources: list[str] = []
    for src in sources:
        if src not in seen:
            seen.add(src)
            unique_sources.append(src)
    return tuple(unique_sources)


def _is_python_file(path: Path) -> bool:
    """Return True if the path looks like a Python source or stub."""
    suffix = path.suffix.lower()
    return suffix in {".py", ".pyi"}


def _iter_python_files(root: Path, paths: Sequence[Path] | None) -> Iterable[Path]:
    """Yield Python files under `root` or the given paths.

    When `paths` is provided, each entry may be a file or directory. Directories
    are walked recursively for `.py`/`.pyi` files.
    """
    if paths:
        for path in paths:
            resolved = (root / path).resolve() if not path.is_absolute() else path
            if resolved.is_dir():
                yield from (p for p in resolved.rglob("*.py") if p.is_file())
                yield from (p for p in resolved.rglob("*.pyi") if p.is_file())
            elif resolved.is_file() and _is_python_file(resolved):
                yield resolved
        return

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if not _is_python_file(path):
            continue
        # Skip common virtualenv / cache / build directories
        parts = path.parts
        if any(
            part in {".venv", ".git", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".pyrightcache", "build", "dist"}
            for part in parts
        ):
            continue
        yield path


def _comment_contains_ignore(comment: str) -> bool:
    """Return True if a comment line contains an ignore pragma.

    This uses root markers (e.g. `noqa:`, `pylint:`, `type:`) and only
    considers text that appears after the initial `#` in the comment. This
    avoids treating explanatory comments that merely *mention* these words as
    pragmas.
    """
    stripped = comment.lstrip()
    if not stripped.startswith("#"):
        return False
    body = stripped[1:].lstrip().lower()
    if not body:
        return False
    # Skip documentation-style comments that show pragmas as code samples.
    if "`" in body:
        return False
    return any(body.startswith(marker) or f" {marker}" in body for marker in BASE_IGNORE_MARKERS)


def _find_justification_block(lines: list[str], index: int) -> tuple[int, int] | None:
    """Locate the justification comment block above an ignore line, if present.

    The block is defined as a contiguous run of comment-only lines immediately
    above the ignore, with no intervening non-comment lines. The first line of
    the block must start with `# ignore JUSTIFIED:`.

    Args:
        lines: All lines in the file.
        index: Zero-based index of the ignore line.

    Returns:
        A tuple `(start, end)` giving the zero-based inclusive bounds of the
        justification block, or `None` if no valid block is found.
    """
    if not index:
        return None

    end = index - 1
    start = end
    while start >= 0:
        stripped = lines[start].lstrip()
        if not stripped.startswith("#"):
            break
        start -= 1
    start += 1

    if start > end:
        return None

    header = lines[start].strip()
    if not header.startswith(JUSTIFICATION_PREFIX):
        return None
    return start, end


def _adjacent_justification(lines: list[str], index: int) -> str | None:
    """Return the justification header text for an ignore, if present."""
    block = _find_justification_block(lines, index)
    if block is None:
        return None
    start, _ = block
    return lines[start].strip()


def _detect_ignore_kind(text: str) -> str:
    """Classify the type of ignore present in a comment.

    Returns:
        A short kind label such as `ruff-line` or `coverage-ignore`.
    """
    lowered = text.lower()
    markers = [
        ("ruff: noqa", "ruff-file"),
        ("pylint: skip-file", "pylint-file"),
        ("mypy: ignore-errors", "mypy-file"),
        ("pyright: ignore", "pyright-ignore"),
        ("pyright:", "pyright-file"),
        ("noqa", "ruff-line"),
        ("pylint: disable", "pylint-line"),
        ("type: ignore", "type-ignore"),
        ("pragma: no cover", "coverage-ignore"),
        ("coverage:", "coverage-ignore"),
    ]
    for marker, kind in markers:
        if marker in lowered:
            return kind
    return "unknown"


# ignore JUSTIFIED: central scan collects multiple validations; keeping it together
# avoids repeated IO and maintains coherence
def _check_file(path: Path) -> tuple[list[IgnoreViolation], int]:  # noqa: C901, PLR0914, FIX002, TD003  # TODO@PantherianCodeX: Split into smaller helpers once performance benchmarks are in place
    """Return ignore-justification violations and ignore count for a file.

    Returns:
        A tuple of (violations, ignore_count).
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    anchor_line = _compute_anchor_line(text)

    violations: list[IgnoreViolation] = []
    ignore_count = 0

    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type != tokenize.COMMENT:
            continue
        comment = token.string
        # Justification lines are metadata, not ignores, even if they mention markers.
        if comment.lstrip().startswith(JUSTIFICATION_PREFIX):
            continue
        if not _comment_contains_ignore(comment):
            continue

        lineno = token.start[0]
        col_offset = token.start[1] + 1
        idx = lineno - 1

        ignore_count += 1
        sources = _detect_sources(comment)

        # General formatting rules for all ignore comments.
        violations.extend(
            _validate_pragma_format(
                file=path,
                line=idx + 1,
                column=col_offset,
                comment=comment,
                line_text=lines[idx] if 0 <= idx < len(lines) else "",
                sources=sources,
            ),
        )

        block = _find_justification_block(lines, idx)
        prev_text = _adjacent_justification(lines, idx) if block is not None else None
        if prev_text is None:
            violations.append(
                IgnoreViolation(
                    file=path,
                    line=idx + 1,
                    column=col_offset,
                    code=RULE_MISSING_JUSTIFICATION,
                    message="missing adjacent '# ignore JUSTIFIED:' comment on the line above",
                    sources=sources,
                ),
            )
            continue

        justification = prev_text[len(JUSTIFICATION_PREFIX) :].strip()
        if not justification:
            violations.append(
                IgnoreViolation(
                    file=path,
                    line=idx + 1,
                    column=col_offset,
                    code=RULE_EMPTY_JUSTIFICATION,
                    message="justification after '# ignore JUSTIFIED:' must not be empty",
                    sources=sources,
                ),
            )
        elif block is not None:
            start, end = block
            for j in range(start + 1, end + 1):
                if lines[j].lstrip().startswith(JUSTIFICATION_PREFIX):
                    violations.append(
                        IgnoreViolation(
                            file=path,
                            line=j + 1,
                            column=len(lines[j]) - len(lines[j].lstrip()) + 1,
                            code=RULE_DUPLICATE_JUSTIFICATION_PREFIX,
                            message="justification prefix must appear only on the first line of the block",
                            sources=sources,
                        ),
                    )
                    break
            for j in range(start, end + 1):
                line_text = lines[j]
                stripped = line_text.lstrip()
                indent_len = len(line_text) - len(stripped)
                effective = stripped
                if len(effective) > MAX_JUSTIFICATION_LINE_LENGTH:
                    # First violating character is the (MAX_JUSTIFICATION_LINE_LENGTH+1)-th
                    # non-indentation character on the line.
                    column = indent_len + MAX_JUSTIFICATION_LINE_LENGTH + 1
                    violations.append(
                        IgnoreViolation(
                            file=path,
                            line=j + 1,
                            column=column,
                            code=RULE_JUSTIFICATION_TOO_LONG,
                            message=(
                                f"justification line must be at most {MAX_JUSTIFICATION_LINE_LENGTH} "
                                "characters (excluding indentation)"
                            ),
                            sources=sources,
                        ),
                    )
                    break

        # File-level placement rules: apply when the comment looks like a file-level pragma.
        kind = _detect_ignore_kind(comment)
        if kind in {"ruff-file", "pylint-file", "mypy-file", "pyright-file"}:
            violations.extend(
                _validate_file_level_placement(
                    file=path,
                    lines=lines,
                    idx=idx,
                    anchor_line=anchor_line,
                    sources=sources,
                ),
            )

    return violations, ignore_count


def _compute_anchor_line(text: str) -> int | None:
    """Compute the anchor line for file-level ignores.

    The anchor is the module-level docstring line if present, otherwise the
    first line of executable code.

    Args:
        text: File contents to inspect.

    Returns:
        The 1-based line number to anchor file-level ignores above, or None if
        it cannot be determined (e.g., due to syntax errors).
    """
    try:
        module: Any = ast.parse(text)
    # ignore JUSTIFIED: invalid syntax in a scanned file should not fail the checker
    # treat as having no anchor and let other tools report syntax errors
    except Exception:  # pragma: no cover  # pylint: disable=broad-exception-caught
        return None

    if not getattr(module, "body", None):
        return None

    docstring = ast.get_docstring(module)
    if docstring is not None and isinstance(module.body[0], ast.Expr):
        doc_node = module.body[0]
        return getattr(doc_node, "lineno", None)

    first_stmt = module.body[0]
    return getattr(first_stmt, "lineno", None)


# ignore JUSTIFIED: pragma formatting rules share state/branches; keeping them together
# avoids duplicate parsing and scattered validation logic
def _validate_pragma_format(  # noqa: C901, PLR0912
    *,
    file: Path,
    line: int,
    column: int,
    comment: str,
    line_text: str,
    sources: tuple[str, ...],
) -> list[IgnoreViolation]:
    """Validate general formatting rules for ignore pragma comments.

    Rules:
    - Inline ignore comments (with code before `#`) must be preceded by
      exactly two spaces.
    - Comment-only ignore lines must start with `# ` once indentation is
      stripped.
    - Additional pragmas within the same comment should be written as
      `  # ...` (two spaces, then `#`).
    - Multiple pragmas for the same logical source in a single comment are
      flagged.

    Returns:
        A list of formatting-related violations for this ignore comment.
    """
    stripped_comment = comment.lstrip()
    if not stripped_comment.startswith("#"):
        # We only enforce prefix rules when we see a leading hash; other shapes
        # are ignored to avoid false positives on unusual comments.
        return []

    violations: list[IgnoreViolation] = []

    # Determine if this is an inline comment (code before '#').
    try:
        hash_index = line_text.index("#")
    except ValueError:
        hash_index = 0
    prefix = line_text[:hash_index]
    is_inline = bool(prefix.strip())

    if is_inline and not prefix.endswith("  "):
        # Inline ignore must be preceded by exactly two spaces.
        violations.append(
            IgnoreViolation(
                file=file,
                line=line,
                column=column,
                code=RULE_INLINE_SPACING,
                message="inline ignore comment must be preceded by exactly two spaces",
                sources=sources,
            ),
        )
    # Comment-only ignore must start with '# ' after indentation.
    elif not is_inline and not stripped_comment.startswith("# "):
        violations.append(
            IgnoreViolation(
                file=file,
                line=line,
                column=column,
                code=RULE_COMMENT_PREFIX,
                message="ignore comment must start with '# '",
                sources=sources,
            ),
        )

    # First pragma must begin at the start of the comment body (after '#') or
    # immediately after a previous pragma fragment.
    body = stripped_comment[1:].lstrip()
    body_lower = body.lower()
    marker_positions: list[int] = []
    for marker in BASE_IGNORE_MARKERS:
        for needle in (marker, f" {marker}", f"#{marker}"):
            position = body_lower.find(needle)
            if position >= 0:
                marker_positions.append(position)
    earliest_marker = min(marker_positions) if marker_positions else None
    if earliest_marker is not None and body[:earliest_marker].strip():
        violations.append(
            IgnoreViolation(
                file=file,
                line=line,
                column=column,
                code=RULE_PRAGMA_POSITION,
                message="ignore pragma must start the comment (or follow another pragma)",
                sources=sources,
            ),
        )

    # Validate separation for additional pragmas in the same comment.
    # We examine the stripped comment (starting at the first '#').
    for idx, char in enumerate(stripped_comment):
        if not idx or char != "#":
            continue
        # Additional pragmas must be introduced by '  #'.
        if stripped_comment[idx - 2 : idx] != "  ":
            violations.append(
                IgnoreViolation(
                    file=file,
                    line=line,
                    column=column,
                    code=RULE_MULTIPRAGMA_SPACING,
                    message="additional ignore pragmas must be formatted as '  # ...'",
                    sources=sources,
                ),
            )
            break

    # Detect duplicate sources on a single comment line by scanning each '#'
    # and attributing it to a logical source.
    lower = stripped_comment.lower()
    source_counts: dict[str, int] = {}
    hash_positions = [idx for idx, ch in enumerate(lower) if ch == "#"]
    for pos in hash_positions:
        segment = lower[pos:]
        src_for_hash: str | None = None
        if segment.startswith(("# noqa", "#noqa", "# ruff:", "#ruff:")):
            src_for_hash = "ruff"
        elif segment.startswith(("# pylint:", "#pylint:")):
            src_for_hash = "pylint"
        elif segment.startswith(("# mypy:", "#mypy:", "# type: ignore", "#type: ignore")):
            src_for_hash = "mypy"
        elif segment.startswith(("# pyright:", "#pyright:")):
            src_for_hash = "pyright"
        elif segment.startswith(("# pragma: no cover", "#pragma: no cover", "# coverage:", "#coverage:")):
            src_for_hash = "coverage"

        if src_for_hash is None:
            continue
        source_counts[src_for_hash] = source_counts.get(src_for_hash, 0) + 1

    for src, count in source_counts.items():
        if count > 1:
            violations.append(
                IgnoreViolation(
                    file=file,
                    line=line,
                    column=column,
                    code=RULE_DUPLICATE_SOURCE,
                    message=f"ignore comment contains multiple pragmas for source '{src}'",
                    sources=sources,
                ),
            )
            break

    return violations


def _validate_file_level_placement(
    *,
    file: Path,
    lines: list[str],
    idx: int,
    anchor_line: int | None,
    sources: tuple[str, ...],
) -> list[IgnoreViolation]:
    """Validate placement rules for file-level ignores.

    File-level ignore blocks must appear above the module-level docstring if
    present, otherwise above the first line of executable code. The block is
    defined as contiguous `# ignore JUSTIFIED:` lines followed by a single
    pragma comment line, with exactly one blank line before and after.

    Returns:
        A list of placement-related violations for this file-level ignore.
    """
    placements: list[IgnoreViolation] = []
    if anchor_line is None:
        return placements

    block = _find_justification_block(lines, idx)
    if block is None:
        return placements
    block_start, _block_end = block
    block_end = idx
    pragma_line = idx + 1
    # Must be strictly above the anchor (docstring or first code).
    if pragma_line >= anchor_line:
        placements.append(
            IgnoreViolation(
                file=file,
                line=pragma_line,
                column=1,
                code=RULE_FILE_PLACEMENT,
                message=(
                    "file-level ignore block must appear immediately above the "
                    "module docstring or the first line of code"
                ),
                sources=sources,
            ),
        )
        return placements

    # Only one pragma line is allowed in a file-level block.
    next_line_idx = idx + 1
    if next_line_idx < len(lines):
        next_stripped = lines[next_line_idx].strip()
        if next_stripped.startswith("#"):
            placements.append(
                IgnoreViolation(
                    file=file,
                    line=pragma_line,
                    column=1,
                    code=RULE_FILE_BLOCK_SINGLE_PRAGMA,
                    message="file-level ignore block must contain exactly one pragma line",
                    sources=sources,
                ),
            )

    # Require a single blank line before the block if there is any content above.
    if block_start > 0:
        before = lines[block_start - 1]
        if before.strip():
            placements.append(
                IgnoreViolation(
                    file=file,
                    line=pragma_line,
                    column=1,
                    code=RULE_FILE_PLACEMENT,
                    message="file-level ignore block must be preceded by a single blank line",
                    sources=sources,
                ),
            )

    # Require a single blank line after the pragma line if more content follows.
    if block_end + 1 < len(lines):
        after = lines[block_end + 1]
        if after.strip():
            placements.append(
                IgnoreViolation(
                    file=file,
                    line=pragma_line,
                    column=1,
                    code=RULE_FILE_PLACEMENT,
                    message="file-level ignore block must be followed by a single blank line",
                    sources=sources,
                ),
            )

    return placements


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that ignore comments (noqa, pylint, type: ignore, pyright, coverage) are justified.",
    )
    parser.add_argument(
        "--json",
        dest="json",
        action="store_true",
        help="Output violations as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional subset of files or directories to scan (defaults to entire repository).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ignore-justification checker.

    Args:
        argv: Optional CLI arguments (used to filter scanned paths).

    Returns:
        0 when all ignores are properly justified, 1 when any violation is found.
    """
    args = _parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    explicit_paths = [Path(p) for p in args.paths]

    all_violations: list[IgnoreViolation] = []
    total_violations = 0
    total_ignores = 0
    files_scanned = 0
    io_errors = 0
    for file_path in _iter_python_files(repo_root, explicit_paths or None):
        files_scanned += 1
        try:
            file_violations, file_ignores = _check_file(file_path)
        except OSError as exc:
            try:
                rel_path = file_path.relative_to(repo_root)
            except ValueError:
                rel_path = file_path
            print(
                f"[ratchetr] IO error reading {rel_path}: {exc}",
                file=sys.stderr,
            )
            io_errors += 1
            continue
        all_violations.extend(file_violations)
        total_violations += len(file_violations)
        total_ignores += file_ignores

    if args.json:
        payload = [violation.to_dict() for violation in all_violations]
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    elif not all_violations:
        print("[ratchetr] all ignores are properly justified")
    else:
        print("[ratchetr] found ignore justification issues:")
        for violation in all_violations:
            print(f"  - {violation.format_cli(repo_root)}")

    if not args.json:
        print(
            "\n[ratchetr] ignore justification summary: \n"
            f"Scanned: {files_scanned}, Found: {total_ignores}, "
            f"Errors: {total_violations}{(', IO Errors: ' + str(io_errors)) if io_errors else ''}\n",
        )

    return 0 if not all_violations and not io_errors else 1


# ignore JUSTIFIED: CLI entrypoint is exercised indirectly via unit tests
# __main__ guard is a trivial wrapper around main()
if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
