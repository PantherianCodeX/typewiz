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

"""Tool version detection helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from ratchetr.core.model_types import LogComponent
from ratchetr.logging import structured_extra

from .process import python_executable, run_command

logger: logging.Logger = logging.getLogger("ratchetr.internal.versions")

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.core.type_aliases import ToolName

__all__ = ["detect_tool_versions"]


def _safe_version_from_output(output: str) -> str | None:
    text = (output or "").strip()
    if not text:
        return None
    for token in text.replace("(", " ").replace(")", " ").split():
        if any(ch.isdigit() for ch in token) and any(ch == "." for ch in token):
            return token.strip()
    return text.splitlines()[0].strip() if text else None


def detect_tool_versions(tools: Sequence[str | ToolName]) -> dict[str, str]:
    """Return a mapping of tool -> version by invoking their version commands.

    Args:
        tools: Tool identifiers (names or ``ToolName`` instances) to inspect.

    Returns:
        Mapping of tool names to detected version strings.
    """
    versions: dict[str, str] = {}
    seen: set[str] = set()
    for tool in tools:
        name = str(tool).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            if name == "pyright":
                out = run_command(["pyright", "--version"], allowed={"pyright"}).stdout
                ver = _safe_version_from_output(out)
                if ver:
                    versions[name] = ver
            elif name == "mypy":
                py = python_executable()
                out = run_command([py, "-m", "mypy", "--version"], allowed={py}).stdout
                ver = _safe_version_from_output(out)
                if ver:
                    versions[name] = ver
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            logger.debug(
                "Failed to detect version for %s: %s",
                name,
                exc,
                extra=_structured_extra(tool=name),
            )
            continue
    return versions


def _structured_extra(**kwargs: object) -> dict[str, object]:
    payload = structured_extra(LogComponent.SERVICES, **cast("dict[str, Any]", kwargs))
    return cast("dict[str, object]", payload)
