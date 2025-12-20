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

"""Generated-block helpers for s11r2 progress artifacts.

We standardize on a single generated-block label for all s11r2 progress outputs.
The marker format is shared repo-wide and implemented by `scripts/docs/_generated_blocks.py`.

This module is a thin wrapper that:
- centralizes the label;
- exposes marker strings for renderers;
- provides a safe insert/replace helper.

The progress board output is fully generated, but we still include a delimited
block to make it obvious what content is produced by automation.
"""

from __future__ import annotations

from typing import Final

from scripts.docs._generated_blocks import GeneratedBlock, GeneratedBlockError, replace_generated_block

PROGRESS_BLOCK_LABEL: Final[str] = "s11r2-progress"
PROGRESS_BLOCK: Final[GeneratedBlock] = GeneratedBlock(label=PROGRESS_BLOCK_LABEL)

BEGIN_MARKER: Final[str] = PROGRESS_BLOCK.begin_marker()
END_MARKER: Final[str] = PROGRESS_BLOCK.end_marker()


def replace_progress_block(*, content: str, replacement_body: str) -> str:
    """Insert or replace the s11r2 progress generated block.

    Args:
        content: Full file content.
        replacement_body: Block body text (without begin/end markers).

    Returns:
        Updated file content.

    """
    return replace_generated_block(content=content, block=PROGRESS_BLOCK, replacement=replacement_body)


__all__ = [
    "BEGIN_MARKER",
    "END_MARKER",
    "PROGRESS_BLOCK_LABEL",
    "GeneratedBlockError",
    "replace_progress_block",
]
