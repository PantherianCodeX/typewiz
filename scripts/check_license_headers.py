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

"""Pre-commit hook to enforce Apache 2.0 license headers on source files.

This script is designed to be used as a pre-commit hook. It ensures that all
targeted files start with a standardized Apache 2.0 license header. If the
header is missing, it is inserted automatically.

The script is intentionally simple and does not rely on third-party
dependencies so that it can be executed in any environment where Python 3
is available.

Usage:
    check_license_headers.py FILE [FILE ...]

The script exits with code 0 if all files already contain the header or were
successfully updated. Pre-commit will report files as modified when changes
are applied and fail the hook on the first run, which is expected behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

HEADER_LINES: list[str] = [
    "Copyright 2025 CrownOps Engineering",
    "",
    'Licensed under the Apache License, Version 2.0 (the "License");',
    "you may not use this file except in compliance with the License.",
    "You may obtain a copy of the License at",
    "",
    "    http://www.apache.org/licenses/LICENSE-2.0",
    "",
    "Unless required by applicable law or agreed to in writing, software",
    'distributed under the License is distributed on an "AS IS" BASIS,',
    "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
    "See the License for the specific language governing permissions and",
    "limitations under the License.",
]

COMMENT_PREFIX = "# "


def build_header_block() -> str:
    """Build the full commented header block for a Python source file.

    Returns:
        The license header block, including trailing blank line.
    """
    commented_lines = [f"{COMMENT_PREFIX}{line}".rstrip() for line in HEADER_LINES]
    return "\n".join(commented_lines) + "\n\n"


HEADER_BLOCK = build_header_block()


def file_needs_header(content: str) -> bool:
    """Determine whether the given file content is missing the license header.

    Args:
        content: Current file contents.

    Returns:
        True if the header block is not present at the top of the file.
    """
    # Normalize leading whitespace and compare prefix.
    stripped = content.lstrip("\n")
    return not stripped.startswith(HEADER_BLOCK)


def insert_header(content: str) -> str:
    """Insert the license header at the top of the file content.

    The header is inserted after a shebang line if present.

    Args:
        content: Current file contents.

    Returns:
        Updated file contents with the license header inserted.
    """
    if not content:
        return HEADER_BLOCK

    lines = content.splitlines(keepends=True)

    if lines and lines[0].startswith("#!"):
        # Preserve shebang as the first line.
        shebang = lines[0]
        rest = "".join(lines[1:])
        rest_stripped = rest.lstrip("\n")
        return f"{shebang}{HEADER_BLOCK}{rest_stripped}"

    stripped = "".join(lines).lstrip("\n")
    return f"{HEADER_BLOCK}{stripped}"


def process_file(path: Path) -> bool:
    """Ensure the license header is present in the given file.

    Args:
        path: Path to the file to process.

    Returns:
        True if the file was modified, False otherwise.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        # If the file cannot be read, treat it as unchanged and let pre-commit
        # surface the underlying issue via other hooks or during execution.
        return False

    if not file_needs_header(text):
        return False

    updated = insert_header(text)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True

    return False


def iter_target_files(paths: Sequence[str]) -> Iterable[Path]:
    """Yield target file paths from the provided argument list.

    This function is intentionally minimal and relies on pre-commit's file
    filtering. It only returns existing regular files.

    Args:
        paths: Sequence of file paths passed by pre-commit.

    Yields:
        Paths to files that should be processed.
    """
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            yield path


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the license header enforcement script.

    Args:
        argv: Command-line arguments (excluding the program name). When
            None, `sys.argv[1:]`is used.

    Returns:
        Exit code suitable for use as a pre-commit hook. Zero indicates
        success; non-zero indicates failure.
    """
    if argv is None:
        argv = sys.argv[1:]

    # Pre-commit will fail the hook automatically if files were modified,
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
