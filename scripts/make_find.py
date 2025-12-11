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

r"""Search utility for Makefile help groups and commands.

This tool is designed for Makefiles that follow the common
"documented help" pattern:

    ##@ Tests
    test.unit: ## Run the unit test suite

It is intended to be called via **dot-notation** Make targets, for example:

    make find.lint
    make find."lint coverage"
    make find."python+3.11"
    make find.label.tests
    make find.label."lint+ruff"

Two search modes are supported:

* Full-text mode (``find.<query>``)
* Label-oriented mode (``find.label.<query>``)

Query semantics
---------------

Queries are composed of tokens with two kinds of separators:

* **Spaces** (and dots when wired via `$(subst ., ,$*)`in Make) act as
  OR separators.
* A plus sign (``+``) inside a token acts as an AND separator.

Examples:
* ``make find.lint.cov``
  Equivalent to `make find."lint cov"`→ OR search on `lint`or ``cov``.

* ``make find."python+3.11"``
  AND search → both `python`and `3.11`must be present.

The parser splits query tokens into:

* OR terms: tokens without ``+``.
* AND terms: each side of a `+`inside a token.

Full-text mode (find.*)
-----------------------

Full-text mode is intended for `find.<query>`targets wired from Make, for
example:

    find.%:
        $(UV) python scripts/make_find.py $(subst ., ,$*)

Matching is performed as follows:

* Each **section heading** is represented by ``"<slug> <label>"``.
* Each **command** is represented by ``"<name> <description>"``.

A section is included in the output if either:

* Its heading satisfies the OR/AND query semantics, in which case
  **all commands** in the section are shown, or
* One or more commands satisfy the OR/AND query semantics, in which
  case only the **matching commands** are shown under that heading.

Label-oriented mode (find.label.*)
----------------------------------

Label-oriented mode is intended for `find.label.<query>`targets wired from
Make, for example:

    find.label.%:
        $(UV) python scripts/make_find.py --labels-only $(subst ., ,$*)

In this mode, matching is performed **per command** against the aggregate of:

* the section slug,
* the section label, and
* the command **name**.

Command descriptions are **not** considered in this mode.

For each command, the search text is::

    "<slug> <label> <name>"

Semantics:

* OR terms: at least one must appear in the aggregate text.
* AND terms: **all** must appear in the aggregate text.
* If both OR and AND terms are present, a command matches when:
    - at least one OR term is present, and
    - all AND terms are present.

Only commands whose aggregate text satisfies these rules are shown, grouped
under their section headings.

Examples:
* ``make find.label.test``
  Matches any command whose heading+name contains ``test``. This will include:
    - the entire `Tests`group (many names contain ``test``),
    - specific commands like ``all.test``, ``package.install-test``,
      ``clean.test``, etc.

* ``make find.label."test+clean"``
  Matches only commands whose heading+name contains **both** `test`and
  ``clean``. For a Makefile like this repository, that includes commands
  such as:
    - ``test.clean.*``,
    - ``clean.test``,
    - `clean.pytest`(via heading + name combination).

Display rules
-------------

For both modes:

* Matching sections are printed using the Makefile-defined formatting
  variables (when present):

    HELP_GROUP_FORMAT := "\n\033[1m%s\033[0m\n"
    HELP_CMD_FORMAT   := "  \033[36m%-32s\033[0m %s\n"

  and fall back to plain equivalents if not defined.

* If no matches are found, a short
  "No matching sections or commands." message is printed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

# ignore JUSTIFIED: TYPE_CHECKING guard prevents runtime execution; branch is only for
# static typing support
if TYPE_CHECKING:  # pragma: no cover
    # ignore JUSTIFIED: imported collections.abc names are only needed for static typing
    # and are not exercised at runtime
    from collections.abc import Iterable, Sequence

Section = tuple[str, str]  # (slug, label)
Command = tuple[str, str]  # (name, description)
SectionMap = dict[str, list[Command]]

_DEFAULT_GROUP_FORMAT: Final[str] = "\n%s\n"
_DEFAULT_CMD_FORMAT: Final[str] = "  %-32s %s\n"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _slugify_label(label: str, separator: str = ".") -> str:
    """Convert a section label into a predictable slug.

    The transformation is minimal and dependency-free: lowercasing,
    replacing non-alphanumeric runs with the separator, and trimming
    leading and trailing separators.

    Args:
        label: Human-readable section label from a `##@`line.
        separator: Character used to join normalized tokens.

    Returns:
        A slug such as ``"lint.format"``.
    """
    normalized = label.lower()
    slug = re.sub(r"[^a-z0-9]+", separator, normalized)
    return slug.strip(separator)


def decode_from_make(lines: Sequence[str], name: str, default: str | None = None) -> str:
    r"""Decode a Makefile variable containing an escaped string literal.

    Makefiles often encode ANSI sequences as escaped strings, for example::

        HELP_GROUP_FORMAT := "\\n\\033[1m%s\\033[0m\\n"

    This helper finds the given variable and decodes its escape sequences
    so it can be used directly with printf-style formatting.

    Args:
        lines: Raw Makefile lines.
        name: Name of the Makefile variable to search for.
        default: Fallback value if the variable is not defined.

    Returns:
        The decoded string value, or `default`if the variable is not
        defined and a default was provided.

    Raises:
        SystemExit: If the variable is missing and no default is provided.
    """
    pattern = re.compile(rf"^{re.escape(name)}\s*:=\s*\"(.*)\"$")
    for line in lines:
        match = pattern.match(line)
        if match:
            raw = match.group(1)
            return bytes(raw, "utf-8").decode("unicode_escape")

    if default is not None:
        return default

    msg = f"Missing definition for {name}"
    raise SystemExit(msg)


def collect_sections(lines: Sequence[str]) -> tuple[list[Section], SectionMap]:
    """Collect help sections and their commands from a Makefile.

    A section is introduced by a line starting with ``"##@ "``. Any
    subsequent targets with `##`comments are associated with the most
    recent section.

    Args:
        lines: Makefile contents as an iterable of lines.

    Returns:
        A pair `(sections, commands)`where:

        * `sections`is an ordered list of `(slug, label)`descriptors.
        * `commands`maps each section slug to a list of
          `(name, description)`command entries.
    """
    sections: list[Section] = []
    commands: SectionMap = {}
    current_slug: str | None = None

    cmd_pat = re.compile(r"^([A-Za-z0-9_.-]+):.*##\s*(.+)$")

    for raw in lines:
        if raw.startswith("##@ "):
            label = raw[4:].strip()
            slug = _slugify_label(label)
            current_slug = slug
            sections.append((slug, label))
            commands.setdefault(slug, [])
            continue

        if current_slug is None:
            continue

        match = cmd_pat.match(raw)
        if match:
            name, desc = match.group(1), match.group(2).strip()
            commands[current_slug].append((name, desc))

    return sections, commands


# ---------------------------------------------------------------------------
# Matching primitives
# ---------------------------------------------------------------------------


def _contains_all(text: str, terms: Sequence[str]) -> bool:
    """Return True if all terms appear in the text (case-insensitive).

    Args:
        text: The candidate text to search.
        terms: Lowercased search terms.

    Returns:
        True if each term is present in `text`(case-insensitive),
        otherwise False.
    """
    lower = text.lower()
    return all(term in lower for term in terms)


def _any_term(text: str, terms: Sequence[str]) -> bool:
    """Return True if any term appears in the text (case-insensitive).

    Args:
        text: The candidate text to search.
        terms: Lowercased OR-search terms.

    Returns:
        True if at least one term is present in `text`(case-insensitive),
        otherwise False.
    """
    lower = text.lower()
    return any(term in lower for term in terms)


def _parse_terms(raw_terms: Sequence[str]) -> tuple[list[str], list[str]]:
    """Split raw query terms into OR and AND sets.

    OR terms:
        Tokens without `+`(e.g. `"lint"`in ``"lint coverage"``).

    AND terms:
        Tokens obtained by splitting on `+`(e.g. `"python+3.11"`becomes
        ``["python", "3.11"]``).

    Args:
        raw_terms: Original search terms from the CLI.

    Returns:
        A tuple `(or_terms, and_terms)`where each element is a list of
        lowercased search strings.
    """
    or_terms: list[str] = []
    and_terms: list[str] = []

    for raw in raw_terms:
        if "+" in raw:
            and_terms.extend(t.lower() for t in raw.split("+") if t)
        else:
            or_terms.append(raw.lower())

    return or_terms, and_terms


# ---------------------------------------------------------------------------
# Search implementations
# ---------------------------------------------------------------------------


def _labels_only_matches(
    sections: Sequence[Section],
    commands: SectionMap,
    or_terms: Sequence[str],
    and_terms: Sequence[str],
) -> dict[str, list[Command]]:
    """Search section headings plus command names (label-oriented mode).

    This mode is used for `find.label.*`targets. Matching is performed
    **per command** against the aggregate of:

    * section slug,
    * section label, and
    * the command name.

    Command descriptions are not considered in this mode.

    For each command, the search text is::

        "<slug> <label> <name>"

    Semantics:

    * OR terms: at least one must appear in the aggregate text.
    * AND terms: all must appear in the aggregate text.
    * If both OR and AND terms are present, a command matches when:
        - at least one OR term is present, and
        - all AND terms are present.

    Args:
        sections: Parsed sections.
        commands: Mapping of section slug to command entries.
        or_terms: OR-search terms.
        and_terms: AND-search terms.

    Returns:
        Mapping of section label to lists of matching commands. Only
        commands whose aggregate heading+name text satisfies the search
        criteria are included under each label.
    """
    results: dict[str, list[Command]] = {}

    for slug, label in sections:
        section_commands = commands.get(slug, [])
        matching_cmds: list[Command] = []

        for name, desc in section_commands:
            record_text = f"{slug} {label} {name}"
            or_ok = not or_terms or _any_term(record_text, or_terms)
            and_ok = not and_terms or _contains_all(record_text, and_terms)

            if or_ok and and_ok:
                matching_cmds.append((name, desc))

        if matching_cmds:
            results[label] = matching_cmds

    return results


def _fulltext_matches(
    sections: Sequence[Section],
    commands: SectionMap,
    or_terms: Sequence[str],
    and_terms: Sequence[str],
) -> dict[str, list[Command]]:
    """Search across labels, slugs, command names, and descriptions.

    This mode is used for `find.*`targets.

    A section is included in the output if either:

    * Its heading `"<slug> <label>"`satisfies the OR/AND semantics, in
      which case **all commands** in the section are returned, or
    * One or more command texts `"<name> <description>"`satisfy the
      OR/AND semantics, in which case only the matching commands are
      returned under that heading.

    Args:
        sections: Parsed sections.
        commands: Mapping of section slugs to commands.
        or_terms: OR-search terms.
        and_terms: AND-search terms.

    Returns:
        Mapping of section label to lists of matching commands.
    """
    results: dict[str, list[Command]] = {}

    for slug, label in sections:
        heading_text = f"{slug} {label}"
        heading_matches = (not or_terms or _any_term(heading_text, or_terms)) and (
            not and_terms or _contains_all(heading_text, and_terms)
        )

        section_cmds = commands.get(slug, [])
        if heading_matches:
            # Heading matches -> include entire group.
            results[label] = section_cmds.copy()
            continue

        matching_cmds: list[Command] = []
        for name, desc in section_cmds:
            text = f"{name} {desc}"
            or_ok = not or_terms or _any_term(text, or_terms)
            and_ok = not and_terms or _contains_all(text, and_terms)
            if or_ok and and_ok:
                matching_cmds.append((name, desc))

        if matching_cmds:
            results[label] = matching_cmds

    return results


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _print_results(
    matches: dict[str, list[Command]],
    group_fmt: str,
    cmd_fmt: str,
) -> int:
    """Render section and command matches using provided formats.

    Args:
        matches: Mapping of section label to matching commands.
        group_fmt: printf-style format string for group headings.
        cmd_fmt: printf-style format string for commands.

    Returns:
        `0`if any matches were printed, `1`if no matches were found.
    """
    if not matches:
        print("No matching sections or commands.")
        return 1

    for label, entries in matches.items():
        sys.stdout.write(group_fmt % label)
        for name, desc in entries:
            sys.stdout.write(cmd_fmt % (name, desc))

    return 0


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def render_help(
    makefile_path: Path,
    *,
    labels_only: bool,
    terms: Sequence[str],
) -> int:
    """Execute the configured search and render the results.

    Args:
        makefile_path: Path to the Makefile to inspect.
        labels_only: If True, use label-oriented mode; otherwise full-text.
        terms: Raw search terms from the CLI (already split on whitespace).

    Returns:
        Exit code `0`on success, `1`if no matches are found.
    """
    lines = makefile_path.read_text(encoding="utf-8").splitlines()

    group_fmt = decode_from_make(lines, "HELP_GROUP_FORMAT", _DEFAULT_GROUP_FORMAT)
    cmd_fmt = decode_from_make(lines, "HELP_CMD_FORMAT", _DEFAULT_CMD_FORMAT)

    sections, commands = collect_sections(lines)
    or_terms, and_terms = _parse_terms(terms)

    if labels_only:
        matches = _labels_only_matches(sections, commands, or_terms, and_terms)
    else:
        matches = _fulltext_matches(sections, commands, or_terms, and_terms)

    return _print_results(matches, group_fmt, cmd_fmt)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Iterable[str] | None = None) -> int:
    """CLI entrypoint for the Makefile search tool.

    Args:
        argv: Optional override for command-line arguments. If omitted,
            arguments are read from :data:`sys.argv`.

    Returns:
        Shell exit code (`0`on success, non-zero on error).

    Raises:
        SystemExit: If the specified Makefile cannot be found.
    """
    parser = argparse.ArgumentParser(
        description="Search Makefile help in full-text or label-oriented mode.",
    )
    parser.add_argument(
        "--labels-only",
        action="store_true",
        help=(
            "Use label-oriented mode: search section slugs, labels, and "
            "command names (but not descriptions). Intended for "
            "`make find.label.<query>` targets."
        ),
    )
    parser.add_argument(
        "--makefile",
        "-f",
        default="Makefile",
        help="Path to the Makefile (default: ./Makefile).",
    )
    parser.add_argument(
        "terms",
        nargs="*",
        help=(
            "Search terms. Space-separated terms use OR semantics; terms "
            "joined with '+' use AND semantics (e.g., 'python+3.11')."
        ),
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    path = Path(args.makefile).resolve()
    if not path.exists():
        msg = f"Makefile not found: {path}"
        raise SystemExit(msg)

    return render_help(makefile_path=path, labels_only=args.labels_only, terms=args.terms)


if __name__ == "__main__":
    sys.exit(main())
