#!/usr/bin/env python3
"""Bulk rewrite import statements according to a mapping.

Usage:
    python scripts/refactor_imports.py --map old.module=new.module [--root src]

Multiple ``--map`` entries are allowed. By default the script runs in dry-run
mode and prints the files that would change. Pass ``--apply`` to write the
changes in-place.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ImportMap:
    old: str
    new: str


def _parse_map_entries(entries: Iterable[str]) -> list[ImportMap]:
    mapping: list[ImportMap] = []
    for entry in entries:
        if "=" not in entry:
            msg = f"Invalid mapping '{entry}'. Expected format old=new."
            raise argparse.ArgumentTypeError(msg)
        old, new = entry.split("=", 1)
        old = old.strip()
        new = new.strip()
        if not old or not new:
            msg = f"Mapping '{entry}' must define both old and new modules."
            raise argparse.ArgumentTypeError(msg)
        mapping.append(ImportMap(old=old, new=new))
    if not mapping:
        raise argparse.ArgumentTypeError("At least one --map entry is required")
    return mapping


def _rewrite_from_line(line: str, mapping: dict[str, str]) -> tuple[str, bool]:
    stripped = line.lstrip()
    if not stripped.startswith("from "):
        return line, False
    indent_len = len(line) - len(stripped)
    indent = line[:indent_len]
    remainder = stripped[5:]
    if " import " not in remainder:
        return line, False
    module, suffix = remainder.split(" import ", 1)
    module = module.strip()
    replacement = mapping.get(module)
    if replacement is None:
        return line, False
    new_line = f"{indent}from {replacement} import {suffix}"
    return new_line, True


def _rewrite_import_line(line: str, mapping: dict[str, str]) -> tuple[str, bool]:
    stripped = line.lstrip()
    if not stripped.startswith("import "):
        return line, False
    indent_len = len(line) - len(stripped)
    indent = line[:indent_len]
    payload = stripped[7:]
    parts = [part.strip() for part in payload.split(",")]
    changed = False
    new_parts: list[str] = []
    for part in parts:
        if not part:
            continue
        tokens = part.split()
        module = tokens[0]
        alias = " ".join(tokens[1:]) if len(tokens) > 1 else ""
        replacement = mapping.get(module)
        if replacement is not None:
            module = replacement
            changed = True
        new_part = module if not alias else f"{module} {alias}"
        new_parts.append(new_part)
    if not changed:
        return line, False
    new_line = indent + "import " + ", ".join(new_parts)
    return new_line, True


def _rewrite_content(content: str, mapping: dict[str, str]) -> tuple[str, bool]:
    lines = content.splitlines()
    changed_any = False
    for idx, line in enumerate(lines):
        new_line, changed = _rewrite_from_line(line, mapping)
        if changed:
            lines[idx] = new_line
            changed_any = True
            continue
        new_line, changed = _rewrite_import_line(line, mapping)
        if changed:
            lines[idx] = new_line
            changed_any = True
    if not changed_any:
        return content, False
    return "\n".join(lines) + ("\n" if content.endswith("\n") else ""), True


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite import statements")
    parser.add_argument(
        "--root",
        default="src",
        help="Root directory to scan for Python files (default: src)",
    )
    parser.add_argument(
        "--map",
        dest="mappings",
        action="append",
        default=[],
        help="Mapping entry in the form old.module=new.module (repeatable)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes (default: dry-run)",
    )
    args = parser.parse_args()

    mappings = _parse_map_entries(args.mappings)
    mapping_dict = {entry.old: entry.new for entry in mappings}
    root = Path(args.root).resolve()
    if not root.exists():
        parser.error(f"Root directory {root} does not exist")

    changed_files: list[Path] = []
    for path in root.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        new_content, changed = _rewrite_content(content, mapping_dict)
        if not changed:
            continue
        changed_files.append(path)
        if args.apply:
            path.write_text(new_content, encoding="utf-8")

    if not changed_files:
        print("No imports needed rewriting.")
        return 0

    action = "Updated" if args.apply else "Would update"
    for file_path in changed_files:
        rel = file_path.relative_to(Path.cwd())
        print(f"{action}: {rel}")
    if not args.apply:
        print("Dry-run complete; re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
