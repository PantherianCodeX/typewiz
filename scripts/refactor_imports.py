#!/usr/bin/env python3
# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Bulk rewrite import statements according to a mapping.

Usage:
    python scripts/refactor_imports.py --map old.module=new.module [--root src]

Multiple ``--map`` entries are allowed. By default the script runs in dry-run
mode and prints the files that would change. Pass ``--apply`` to write the
changes in-place.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ImportMap:
    old: str
    new: str


@dataclass(slots=True)
class EnsureImport:
    path: Path
    module: str
    symbols: tuple[str, ...]


def _strip_suffix(name: str) -> str:
    for suffix in (".py", ".pyi"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _module_name_from_path(path: Path, root: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    parts = list(relative.parts)
    if not parts:
        return None
    parts[-1] = _strip_suffix(parts[-1])
    if parts[-1] == "__init__":
        parts.pop()
    if not parts:
        return None
    return ".".join(parts)


def _resolve_absolute_module(module: str, current_module: str | None) -> str | None:
    if not module.startswith("."):
        return module
    if not current_module:
        return None
    level = len(module) - len(module.lstrip("."))
    remainder = module[level:]
    parents = current_module.split(".")
    if level > len(parents):
        return None
    target = parents[: len(parents) - level]
    if remainder:
        target.extend(part for part in remainder.split(".") if part)
    if not target:
        return None
    return ".".join(target)


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
    return mapping


def _parse_export_map(entries: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            msg = f"Invalid export mapping '{entry}'. Expected old=new."
            raise argparse.ArgumentTypeError(msg)
        old, new = entry.split("=", 1)
        old = old.strip().strip("'\"")
        new = new.strip().strip("'\"")
        if not old or not new:
            msg = f"Export mapping '{entry}' must define both old and new names."
            raise argparse.ArgumentTypeError(msg)
        result[old] = new
    return result


def _parse_ensure_import_entries(entries: Iterable[str], root: Path) -> list[EnsureImport]:
    ensure_list: list[EnsureImport] = []
    for entry in entries:
        parts = entry.split(":")
        if len(parts) != 3:
            msg = f"Invalid ensure-import '{entry}'. Expected path:module:symbols."
            raise argparse.ArgumentTypeError(msg)
        rel_path, module, symbols_str = parts
        path = Path(rel_path)
        if not path.is_absolute():
            path = (root / path).resolve()
        module = module.strip()
        symbols = tuple(sym.strip() for sym in symbols_str.split(",") if sym.strip())
        if not module or not symbols:
            msg = f"Ensure-import '{entry}' must include module and at least one symbol."
            raise argparse.ArgumentTypeError(msg)
        ensure_list.append(EnsureImport(path=path, module=module, symbols=symbols))
    return ensure_list


def _git_repo_root(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            cwd=start,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    root = result.stdout.strip()
    return Path(root).resolve() if root else None


def _git_tracked_python_files(root: Path) -> list[Path]:
    repo_root = _git_repo_root(root)
    if not repo_root:
        return []
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "*.py"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    root_resolved = root.resolve()
    files: list[Path] = []
    for line in result.stdout.splitlines():
        rel = line.strip()
        if not rel:
            continue
        path = (repo_root / rel).resolve()
        if not path.exists():
            continue
        if root_resolved == repo_root or path == root_resolved or root_resolved in path.parents:
            files.append(path)
    return files


def _iter_python_files(root: Path, use_git: bool) -> Iterator[Path]:
    if use_git:
        git_files = _git_tracked_python_files(root)
        if git_files:
            yield from git_files
            return
    yield from root.rglob("*.py")


def _load_mapping_file(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Mapping file {path} does not exist")
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def _rewrite_from_line(
    line: str,
    mapping: dict[str, str],
    current_module: str | None,
) -> tuple[str, bool]:
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
    absolute_module = _resolve_absolute_module(module, current_module)
    replacement = None
    if absolute_module:
        replacement = mapping.get(absolute_module)
    if replacement is None:
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


def _rewrite_content(
    content: str,
    mapping: dict[str, str],
    current_module: str | None = None,
) -> tuple[str, bool]:
    lines = content.splitlines()
    changed_any = False
    for idx, line in enumerate(lines):
        new_line, changed = _rewrite_from_line(line, mapping, current_module)
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


def _ensure_import_in_content(
    content: str, module: str, symbols: tuple[str, ...]
) -> tuple[str, bool]:
    lines = content.splitlines()
    line_ending = "\n" if content.endswith("\n") else ""
    target_prefix = f"from {module} import "
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(target_prefix):
            existing = stripped[len(target_prefix) :].split("#", 1)[0]
            current_symbols = [sym.strip() for sym in existing.split(",") if sym.strip()]
            missing = [sym for sym in symbols if sym not in current_symbols]
            if not missing:
                return content, False
            updated = current_symbols + missing
            indent = line[: len(line) - len(line.lstrip())]
            lines[idx] = f"{indent}{target_prefix}{', '.join(updated)}"
            return "\n".join(lines) + line_ending, True
    insert_idx = _determine_insertion_index(lines)
    new_line = f"from {module} import {', '.join(symbols)}"
    lines.insert(insert_idx, new_line)
    return "\n".join(lines) + line_ending, True


def _determine_insertion_index(lines: list[str]) -> int:
    if not lines:
        return 0
    joined = "\n".join(lines) + "\n"
    insert_idx = 0
    try:
        parsed = ast.parse(joined)
    except SyntaxError:
        parsed = None
    docstring_offset = 0
    if parsed and parsed.body:
        doc_node = parsed.body[0]
        if (
            isinstance(doc_node, ast.Expr)
            and isinstance(doc_node.value, ast.Constant)
            and isinstance(doc_node.value.value, str)
        ):
            insert_idx = doc_node.end_lineno or doc_node.lineno
            docstring_offset = 1
    insert_idx = max(insert_idx, 0)
    idx = insert_idx
    if parsed:
        for node in parsed.body[docstring_offset:]:
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                idx = max(idx, node.end_lineno or node.lineno)
            else:
                break
    idx = max(idx, 0)
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    return idx


def _rewrite_exports(content: str, export_map: dict[str, str]) -> tuple[str, bool]:
    if not export_map:
        return content, False
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return content, False
    target_node: ast.Assign | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            ):
                target_node = node
                break
    if target_node is None:
        return content, False
    values: list[str] = []
    elts: list[ast.expr] = []
    if isinstance(target_node.value, (ast.List, ast.Tuple)):
        elts = list(target_node.value.elts)
    else:
        return content, False
    for elt in elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            values.append(elt.value)
        else:
            return content, False
    replaced = False
    new_values: list[str] = []
    for name in values:
        new_name = export_map.get(name, name)
        if new_name != name:
            replaced = True
        new_values.append(new_name)
    if not replaced:
        return content, False
    new_block_lines = ["__all__ = ["]
    for name in new_values:
        new_block_lines.append(f'    "{name}",')
    new_block_lines.append("]")
    start = target_node.lineno - 1
    end = target_node.end_lineno
    lines = content.splitlines()
    lines[start:end] = new_block_lines
    result = "\n".join(lines)
    if content.endswith("\n"):
        result += "\n"
    return result, True


def main(argv: Sequence[str] | None = None) -> int:
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
        "--mapping-file",
        dest="mapping_files",
        action="append",
        default=[],
        help="Optional file containing mapping definitions (one 'old=new' per line)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes (default: dry-run)",
    )
    parser.add_argument(
        "--ensure-import",
        dest="ensure_imports",
        action="append",
        default=[],
        help="Ensure an import exists in the given file. Format: path:module:symbol1,symbol2",
    )
    parser.add_argument(
        "--export-map",
        dest="export_mappings",
        action="append",
        default=[],
        help="Rename entries inside __all__ blocks (old=new, repeatable)",
    )
    parser.add_argument(
        "--use-git",
        dest="use_git",
        action="store_true",
        default=True,
        help="Use 'git ls-files' to discover Python files (respects gitignore)",
    )
    parser.add_argument(
        "--no-use-git",
        dest="use_git",
        action="store_false",
        help="Disable git discovery and scan filesystem directly",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists():
        parser.error(f"Root directory {root} does not exist")

    mapping_entries = list(args.mappings)
    for file_entry in args.mapping_files:
        mapping_entries.extend(_load_mapping_file(Path(file_entry)))
    mappings = _parse_map_entries(mapping_entries) if mapping_entries else []
    mapping_dict = {entry.old: entry.new for entry in mappings}
    export_map = _parse_export_map(args.export_mappings)
    ensure_imports = _parse_ensure_import_entries(args.ensure_imports, root)

    if not (mapping_dict or export_map or ensure_imports):
        parser.error(
            "Provide at least one --map/--mapping-file/--ensure-import/--export-map action"
        )

    seen_paths: set[Path] = set()
    changed_files: list[Path] = []

    def _mark(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        changed_files.append(resolved)

    if mapping_dict:
        for path in _iter_python_files(root, args.use_git):
            content = path.read_text(encoding="utf-8")
            module_name = _module_name_from_path(path, root)
            new_content, changed = _rewrite_content(content, mapping_dict, module_name)
            if not changed:
                continue
            _mark(path)
            if args.apply:
                path.write_text(new_content, encoding="utf-8")

    if export_map:
        for path in _iter_python_files(root, args.use_git):
            content = path.read_text(encoding="utf-8")
            new_content, changed = _rewrite_exports(content, export_map)
            if not changed:
                continue
            _mark(path)
            if args.apply:
                path.write_text(new_content, encoding="utf-8")

    for ensure_entry in ensure_imports:
        if not ensure_entry.path.exists():
            print(f"Skipping missing file {ensure_entry.path}")
            continue
        content = ensure_entry.path.read_text(encoding="utf-8")
        new_content, changed = _ensure_import_in_content(
            content, ensure_entry.module, ensure_entry.symbols
        )
        if not changed:
            continue
        _mark(ensure_entry.path)
        if args.apply:
            ensure_entry.path.write_text(new_content, encoding="utf-8")

    if not changed_files:
        print("No imports needed rewriting.")
        return 0

    action = "Updated" if args.apply else "Would update"
    for file_path in changed_files:
        try:
            rel = file_path.relative_to(Path.cwd())
        except ValueError:
            rel = file_path
        print(f"{action}: {rel}")
    if not args.apply:
        print("Dry-run complete; re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
