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

"""Utilities for updating "generated blocks" in markdown files.

A *generated block* is an automatically-produced region inside an otherwise
hand-edited file. The region is delimited by marker comments:

  <!-- GENERATED:BEGIN <label> -->
  ... generated content ...
  <!-- GENERATED:END <label> -->

Design goals
------------
- Deterministic output and stable formatting.
- Safe edits: preserve manual content outside the block.
- Clear failures: refuse to operate if markers are malformed or ambiguous.

This module is intentionally small (stdlib-only) and strongly typed.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


@dataclasses.dataclass(frozen=True)
class GeneratedBlock:
    """Definition of a generated block inside a text file."""

    label: str

    def begin_marker(self) -> str:
        """Return the BEGIN marker string for this block.

        Returns:
            BEGIN marker string.
        """
        return f"<!-- GENERATED:BEGIN {self.label} -->"

    def end_marker(self) -> str:
        """Return the END marker string for this block.

        Returns:
            END marker string.
        """
        return f"<!-- GENERATED:END {self.label} -->"


class GeneratedBlockError(RuntimeError):
    """Raised when generated-block markers are missing or malformed."""


def replace_generated_block(*, content: str, block: GeneratedBlock, replacement: str) -> str:
    """Replace the generated block in *content* with *replacement*.

    If markers are not present, the block is appended to the end of the file.

    Args:
        content: Full file text.
        block: Block definition (label determines markers).
        replacement: New block body. Must not include begin/end markers.

    Returns:
        Updated full file content.

    Raises:
        GeneratedBlockError: if markers are malformed or ambiguous.
    """
    begin = block.begin_marker()
    end = block.end_marker()

    begin_idx = content.find(begin)
    end_idx = content.find(end)

    if begin_idx == -1 and end_idx == -1:
        # Append a new block.
        prefix = content
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix and not prefix.endswith("\n\n"):
            prefix += "\n"
        body = replacement.rstrip("\n") + "\n"
        return f"{prefix}{begin}\n\n{body}{end}\n"

    if begin_idx == -1 or end_idx == -1:
        msg = "Generated-block markers are incomplete: both BEGIN and END markers are required."
        raise GeneratedBlockError(msg)

    if end_idx < begin_idx:
        msg = "Generated-block END marker occurs before BEGIN marker."
        raise GeneratedBlockError(msg)

    # Ensure uniqueness.
    if content.find(begin, begin_idx + len(begin)) != -1:
        msg = "Multiple BEGIN markers found for the same block label."
        raise GeneratedBlockError(msg)
    if content.find(end, end_idx + len(end)) != -1:
        msg = "Multiple END markers found for the same block label."
        raise GeneratedBlockError(msg)

    pre = content[:begin_idx].rstrip("\n") + "\n"
    post = content[end_idx + len(end) :]
    if post and not post.startswith("\n"):
        post = "\n" + post

    body = replacement.rstrip("\n")
    body = "\n\n" + body + "\n\n" if body else "\n\n"

    return f"{pre}{begin}{body}{end}{post}".rstrip("\n") + "\n"


def update_file_generated_block(*, path: Path, block: GeneratedBlock, replacement: str) -> bool:
    """Update a generated block in *path*.

    Returns:
        True if the file changed, else False.

    Args:
        path: File to update.
        block: Generated block definition.
        replacement: Replacement content (no markers).
    """
    prior = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = replace_generated_block(content=prior, block=block, replacement=replacement)
    if updated == prior:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return True


def require_paths_exist(paths: Iterable[Path]) -> None:
    """Fail fast if any path does not exist.

    Args:
        paths: Paths that must exist.

    Raises:
        FileNotFoundError: if any required path does not exist.
    """
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        joined = "\n".join(f"- {m}" for m in missing)
        msg = f"Required paths are missing:\n{joined}"
        raise FileNotFoundError(msg)
