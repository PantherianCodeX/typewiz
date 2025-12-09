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

r"""Helper to render filtered Makefile help groups.

This script parses a Makefile that uses the common pattern:

- Group markers: lines starting with `##@ ` (e.g. `##@ Lint & Format`).
- Target descriptions: targets with `##` comments
  (e.g. `lint.ruff: ## Run ruff lint`).
- Formatting variables defined in the Makefile:

    HELP_GROUP_FORMAT := "\\n\\033[1m%s\\033[0m\\n"
    HELP_CMD_FORMAT   := "  \\033[36m%-32s\\033[0m %s\\n"

Given a "slug" such as `lint`, `lint.ruff`, or `test`, this script
prints the subset of help output relevant to that group or target,
mirroring the behavior of scoped `make <group>.help` commands.

The implementation is deliberately self-contained and uses only the
Python standard library so it can be vendored into any project.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:  # pragma: no cover - import-only for type checkers
    from collections.abc import Iterable, Sequence

Section = tuple[str, str]
Command = tuple[str, str]
SectionMap = dict[str, list[Command]]
SectionWithCommands = tuple[str, str, list[Command]]

_DEFAULT_GROUP_FORMAT: Final[str] = "\n%s\n"
_DEFAULT_CMD_FORMAT: Final[str] = "  %-32s %s\n"


def _slugify_label(label: str, separator: str = ".") -> str:
    """Convert a human-readable group label into a slug.

    The transformation is deliberately conservative and dependency-free:

    - Lowercases the label.
    - Replaces any run of non-alphanumeric characters with `separator`.
    - Strips leading and trailing separators.

    Examples:
        - `"Lint & Format" -> "lint.format"` (separator=".")
        - `"CI / Packaging" -> "ci_packaging"` (separator="_")

    Args:
        label: Raw label text from a `##@` Makefile line.
        separator: Character used to join tokens (defaults to `"."`).

    Returns:
        A slug suitable for grouping, such as `"lint.format"`.
    """
    normalized = label.lower()
    # Collapse runs of non-alphanumeric characters into the separator.
    slug = re.sub(r"[^a-z0-9]+", separator, normalized)
    return slug.strip(separator)


def decode_from_make(
    lines: Sequence[str],
    name: str,
    default: str | None = None,
) -> str:
    r"""Decode a Makefile string variable, honoring escape sequences.

    This helper looks for a line of the form::

        NAME := "value-with-escapes"

    It then decodes common escape sequences (e.g. `"\\033"`) so the
    resulting string can be used directly with `printf`-style formatting.

    Args:
        lines: All lines from the Makefile.
        name: The Makefile variable name to search for (e.g. `"HELP_GROUP_FORMAT"`).
        default: Optional fallback if the variable is not found. If omitted
            or `None`, a missing variable results in `SystemExit`.

    Returns:
        The decoded string value of the Makefile variable.

    Raises:
        SystemExit: If the variable is missing and no default is provided.
    """
    pattern = re.compile(rf"^{re.escape(name)}\s*:=\s*\"(.*)\"$")
    for line in lines:
        match = pattern.match(line)
        if match:
            raw_value = match.group(1)
            # Decode escape sequences like \033 from the Makefile string.
            return bytes(raw_value, "utf-8").decode("unicode_escape")

    if default is not None:
        return default

    msg = f"Missing definition for {name}"
    raise SystemExit(msg)


def collect_sections(lines: Sequence[str]) -> tuple[list[Section], SectionMap]:
    """Collect help sections and commands from a Makefile.

    A "section" is introduced by a line starting with `"##@ "`,
    and subsequent targets with `##` descriptions are associated
    with the most recent section.

    Args:
        lines: All lines from the Makefile.

    Returns:
        A tuple of:

        * sections: A list of `(slug, label)` pairs where `slug` is the
          internal group key (e.g. `"lint.format"`) and `label` is the
          human-readable section title from the Makefile.
        * commands: A mapping from section slug to a list of `(name, desc)`
          target/description pairs.
    """
    sections: list[Section] = []
    commands: SectionMap = {}
    current_slug: str | None = None

    command_pattern = re.compile(r"^([A-Za-z0-9_.-]+):.*##(.*)$")

    for raw in lines:
        if raw.startswith("##@ "):
            label = raw[4:].strip()
            slug = _slugify_label(label, separator=".")
            current_slug = slug
            sections.append((slug, label))
            commands.setdefault(slug, [])
            continue

        if current_slug is None:
            # Ignore commands before the first section marker.
            continue

        match = command_pattern.match(raw)
        if not match:
            continue

        name = match.group(1)
        desc = match.group(2).strip()
        # current_slug is guaranteed to be non-None here due to the early-continue above.
        commands[current_slug].append((name, desc))

    return sections, commands


def select_sections(sections: Sequence[Section], slug: str) -> list[Section]:
    """Determine which sections match a requested slug.

    Matching is performed in three passes:

    1. Exact match on section slug.
    2. Section slugs that start with the requested slug and a separator
       (`"."` or `"-"`) or where the section slug extends the slug
       (e.g. `"lint"` matches `"lint.format"`).
    3. Ancestor search: any section where the requested slug is a descendant
       (e.g. `"lint.format.extra"` matches ancestor `"lint"`).

    Args:
        sections: All known sections as `(slug, label)` pairs.
        slug: The requested help slug (e.g. `"lint"` or `"lint.format"`).

    Returns:
        A list of matching sections, possibly empty if nothing matches.
    """
    exact = [entry for entry in sections if entry[0] == slug]
    if exact:
        return exact

    prefix = [
        entry
        for entry in sections
        if entry[0].startswith(f"{slug}.")
        or entry[0].startswith(f"{slug}-")
        or (entry[0].startswith(slug) and entry[0] != slug)
    ]
    if prefix:
        return prefix

    ancestor = [entry for entry in sections if slug.startswith(f"{entry[0]}.")]
    if ancestor:
        return ancestor

    return []


def select_commands(
    sections: Sequence[Section],
    commands: SectionMap,
    slug: str,
) -> list[SectionWithCommands]:
    """Fallback: select commands by matching the slug against target names.

    When no section can be resolved for a requested slug, this function
    searches across all sections for commands whose names either match
    the slug exactly or begin with `"{slug}."`.

    Args:
        sections: All known sections as `(slug, label)` pairs.
        commands: Mapping from section slug to lists of `(name, desc)`.
        slug: The requested help slug (e.g. `"lint"` or `"lint.format"`).

    Returns:
        A list of tuples of the form `(section_slug, label, entries)` where
        `entries` is the list of matching `(name, desc)` pairs.
    """
    matched: list[SectionWithCommands] = []
    for section_slug, label in sections:
        entries = [
            (name, desc) for name, desc in commands.get(section_slug, []) if name == slug or name.startswith(f"{slug}.")
        ]
        if entries:
            matched.append((section_slug, label, entries))
    return matched


def render_help(slug: str, makefile_path: Path) -> int:
    """Render filtered help output for a given slug.

    This function reads the Makefile, discovers help sections and commands,
    and prints only those that are relevant to the requested `slug`. It
    respects the format strings defined in the Makefile (if present) and
    falls back to simple defaults otherwise.

    Args:
        slug: Help group or target prefix to render (e.g. `"test"`,
            `"lint"`, or `"lint.ruff"`).
        makefile_path: Path to the Makefile to parse.

    Returns:
        Zero on success, non-zero if the slug could not be resolved.
    """
    lines = makefile_path.read_text(encoding="utf-8").splitlines()

    group_fmt = decode_from_make(
        lines,
        "HELP_GROUP_FORMAT",
        default=_DEFAULT_GROUP_FORMAT,
    )
    cmd_fmt = decode_from_make(
        lines,
        "HELP_CMD_FORMAT",
        default=_DEFAULT_CMD_FORMAT,
    )

    sections, commands = collect_sections(lines)
    targets = select_sections(sections, slug)

    printed = False

    # First, try to print all commands in matching sections.
    for section_slug, label in targets:
        entries = commands.get(section_slug, [])
        if not entries:
            continue

        sys.stdout.write(group_fmt % label)
        for name, desc in entries:
            sys.stdout.write(cmd_fmt % (name, desc))
        printed = True

    # If no section-level output, fall back to matching individual commands.
    if not printed:
        matches = select_commands(sections, commands, slug)
        if matches:
            for _, label, entries in matches:
                sys.stdout.write(group_fmt % label)
                for name, desc in entries:
                    sys.stdout.write(cmd_fmt % (name, desc))
            return 0

    # If we matched sections but they had no documented commands.
    if not printed and targets:
        label = targets[0][1]
        sys.stdout.write(group_fmt % label)
        sys.stdout.write("  (no commands with help descriptions)\n")
        return 0

    if printed:
        return 0

    print(f"Unknown help group: {slug}")
    return 1


def main(argv: Iterable[str] | None = None) -> int:
    """CLI entrypoint for rendering scoped Makefile help.

    Args:
        argv: Optional iterable of argument strings. If omitted, arguments
            are taken from `sys.argv`.

    Returns:
        Process exit code: `0` on success, non-zero on failure.

    Raises:
        SystemExit: If the Makefile cannot be found.
    """
    parser = argparse.ArgumentParser(
        description="Render scoped Makefile help output.",
    )
    parser.add_argument(
        "slug",
        help="Help group to render (e.g., 'docker', 'docker.images', 'dev')",
    )
    parser.add_argument(
        "makefile",
        nargs="?",
        default="Makefile",
        help="Path to the Makefile (defaults to ./Makefile)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    makefile_path = Path(args.makefile).resolve()
    if not makefile_path.exists():
        msg = f"Makefile not found: {makefile_path}"
        raise SystemExit(msg)

    return render_help(slug=args.slug, makefile_path=makefile_path)


if __name__ == "__main__":
    sys.exit(main())
