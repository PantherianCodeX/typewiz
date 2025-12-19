#!/usr/bin/env python3
"""Execution-contract progress board generator.

This is an **automation-only** helper for the documentation rewrite. It is intentionally
small, deterministic, and audit-friendly.

What it does
------------
- Parses the markdown-table registries in
  `docs/_internal/policy/execution-contract/registers/`.
- Computes roll-ups (counts by status, coverage checks, warnings).
- Updates `progress_board.md` by replacing the content between:

  <!-- GENERATED:BEGIN -->
  <!-- GENERATED:END -->

  If the markers do not exist, the generated block is appended.

Design principles
-----------------
- No external dependencies (stdlib only).
- Deterministic output (stable ordering).
- Safe edits: preserves manual content outside the GENERATED markers.

Usage
-----
From repo root:

  python scripts/docs/build_execution_contract_progress_board.py --write

To validate without writing:

  python scripts/docs/build_execution_contract_progress_board.py --print

To run a self-test demo (writes into a temporary copy and prints diffs):

  python scripts/docs/build_execution_contract_progress_board.py --demo

Exit codes
----------
- 0: success
- 2: parse/validation failure (missing required columns, unreadable files, etc.)
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import re
import shutil
import sys
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path

GENERATED_BEGIN = "<!-- GENERATED:BEGIN -->"
GENERATED_END = "<!-- GENERATED:END -->"


# -----------------------------
# Markdown table parsing
# -----------------------------

@dataclasses.dataclass(frozen=True)
class MdTable:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    start_line: int
    end_line: int


_PIPE_LINE = re.compile(r"^\s*\|.*\|\s*$")
_SEP_LINE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _split_row(line: str) -> list[str]:
    s = line.strip()
    s = s.removeprefix("|")
    s = s.removesuffix("|")
    return [p.strip() for p in s.split("|")]


def iter_md_tables(text: str) -> Iterator[MdTable]:
    """Yield markdown tables found in text."""
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if _PIPE_LINE.match(line) and _SEP_LINE.match(nxt):
            header = _split_row(line)
            body: list[list[str]] = []
            j = i + 2
            while j < len(lines) and _PIPE_LINE.match(lines[j]):
                body.append(_split_row(lines[j]))
                j += 1

            hlen = len(header)
            norm_rows: list[tuple[str, ...]] = []
            for r in body:
                if len(r) < hlen:
                    r = r + ([""] * (hlen - len(r)))
                elif len(r) > hlen:
                    r = r[:hlen]
                if all(c.strip() == "" for c in r):
                    continue
                norm_rows.append(tuple(r))

            yield MdTable(header=tuple(header), rows=tuple(norm_rows), start_line=i + 1, end_line=j)
            i = j
        else:
            i += 1


def find_table_by_headers(text: str, required_headers: Sequence[str]) -> MdTable | None:
    """Find first table whose headers match all required header *fragments* (case-insensitive).

    We intentionally match by *containment* rather than exact header equality, because the
    registries use descriptive headers like:

      - `Superseded by plan? (Y/N + ref)`
      - `Posture (`verbatim`/`adapt`)`

    Callers should therefore pass stable fragments such as `Superseded by plan?` or `Posture`.
    """
    req = [h.strip().lower() for h in required_headers]
    for t in iter_md_tables(text):
        hdr = [h.strip().lower() for h in t.header]
        if all(any(r in h for h in hdr) for r in req):
            return t
    return None


def table_rows_as_dicts(t: MdTable) -> list[dict[str, str]]:
    idx = {h: i for i, h in enumerate(t.header)}
    out: list[dict[str, str]] = []
    for row in t.rows:
        out.append({h: row[i].strip() for h, i in idx.items()})
    return out


def _norm_status(s: str) -> str:
    s = s.strip()
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def _classify_owner_path(owner: str) -> str:
    o = owner.strip().strip("`")
    lower = o.lower()
    if "docs/_internal/policy" in lower or lower.startswith("docs/_internal/policy"):
        return "Policy"
    if "docs/_internal/adr" in lower or lower.startswith("adr-") or lower.startswith("adr-000"):
        return "ADR"
    if lower.startswith("docs/reference") or "/reference/" in lower:
        return "Reference spec"
    if lower.startswith("docs/cli") or "/cli/" in lower:
        return "CLI docs"
    if "roadmap" in lower:
        return "Roadmap"
    if "archive" in lower:
        return "Archive"
    return "Other"


# -----------------------------
# Metrics extraction
# -----------------------------

@dataclasses.dataclass(frozen=True)
class MetricBlock:
    title: str
    body_md: str


@dataclasses.dataclass(frozen=True)
class Metrics:
    blocks: tuple[MetricBlock, ...]
    warnings: tuple[str, ...]


def _count_by(rows: Iterable[Mapping[str, str]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        v = _norm_status(r.get(key, ""))
        if not v:
            continue
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0].lower())))


def _md_kv_table(title_left: str, d: Mapping[str, int]) -> str:
    lines = [f"| {title_left} | Count |", "|---|---:|"]
    for k, v in d.items():
        lines.append(f"| {k} | {v} |")
    if len(lines) == 2:
        lines.append("| (none) | 0 |")
    return "\n".join(lines)


def _md_warning_list(warnings: Sequence[str]) -> str:
    if not warnings:
        return "_No warnings._"
    return "\n".join(f"- {w}" for w in warnings)


def compute_metrics(register_dir: Path) -> Metrics:
    warnings: list[str] = []
    blocks: list[MetricBlock] = []

    def read(name: str) -> str:
        p = register_dir / name
        if not p.exists():
            warnings.append(f"Missing register: `{p.as_posix()}`")
            return ""
        return p.read_text(encoding="utf-8")

    # Owner index
    owner_txt = read("owner_index.md")
    owner_table = find_table_by_headers(owner_txt, ["Concept", "Canonical owner"])
    if owner_table:
        owner_rows = table_rows_as_dicts(owner_table)
        blocks.append(MetricBlock("Owner index", f"- Concepts owned (rows): **{len(owner_rows)}**"))
        by_bucket: dict[str, int] = {}
        for r in owner_rows:
            b = _classify_owner_path(r.get("Canonical owner", ""))
            by_bucket[b] = by_bucket.get(b, 0) + 1
        blocks.append(MetricBlock("Ownership distribution (by owner bucket)", _md_kv_table("Bucket", by_bucket)))
    else:
        warnings.append("Could not find Owner index table (expected headers include `Concept` and `Canonical owner`).")

    # Rewrite status
    rs_txt = read("rewrite_status.md")
    rs_table = find_table_by_headers(rs_txt, ["Artifact", "Status"])
    if rs_table:
        rs_rows = table_rows_as_dicts(rs_table)
        blocks.append(MetricBlock("Rewrite status", _md_kv_table("Artifact status", _count_by(rs_rows, "Status"))))
    else:
        warnings.append("Could not find Rewrite status table (expected headers include `Artifact` and `Status`).")

    # Master mapping ledger (mapping table)
    mml_txt = read("master_mapping_ledger.md")
    mml_table = find_table_by_headers(mml_txt, ["Row ID", "Source ID", "Destination doc", "Status"])
    if mml_table:
        mml_rows = table_rows_as_dicts(mml_table)

        ids = [r.get("Row ID", "").strip() for r in mml_rows if r.get("Row ID", "").strip()]
        dup = sorted({x for x in ids if ids.count(x) > 1})
        if dup:
            warnings.append(f"Duplicate mapping Row IDs: {', '.join(dup[:10])}{'…' if len(dup) > 10 else ''}")

        blocks.append(MetricBlock("Master mapping ledger", _md_kv_table("Mapping status", _count_by(mml_rows, "Status"))))

        # Type column may vary slightly
        type_col = None
        for h in mml_table.header:
            if "type" in h.lower():
                type_col = h
                break
        if type_col:
            blocks.append(MetricBlock("Mapping type", _md_kv_table("Type", _count_by(mml_rows, type_col))))
        else:
            warnings.append("Master mapping ledger: could not find a Type column; skipping type roll-up.")

        src_ids = sorted({r.get("Source ID", "").strip() for r in mml_rows if r.get("Source ID", "").strip()})
        blocks.append(MetricBlock("Mapped source IDs (unique)", f"- Unique Source IDs present in mapping rows: **{len(src_ids)}**"))
    else:
        warnings.append("Could not find Master mapping ledger mapping table (expected headers include `Row ID`, `Source ID`, `Destination doc`, `Status`).")

    # Draft-2 preservation map
    d2_txt = read("draft2_preservation_map.md")
    d2_table = find_table_by_headers(d2_txt, ["Item ID", "Preserve posture", "Superseded by plan?"])
    if d2_table:
        d2_rows = table_rows_as_dicts(d2_table)
        blocks.append(MetricBlock("Draft-2 preservation map", f"- Preservation items (rows): **{len(d2_rows)}**"))

        posture_col = next((h for h in d2_table.header if "preserve posture" in h.lower()), None)
        if posture_col:
            blocks.append(MetricBlock("Preserve posture", _md_kv_table("Posture", _count_by(d2_rows, posture_col))))

        sup_col = next((h for h in d2_table.header if "superseded" in h.lower()), None)
        if sup_col:
            counts: dict[str, int] = {}
            for r in d2_rows:
                v = r.get(sup_col, "").strip().upper()
                v2 = "Y" if v.startswith("Y") else ("N" if v.startswith("N") else "")
                if v2:
                    counts[v2] = counts.get(v2, 0) + 1
            blocks.append(MetricBlock("Superseded by plan?", _md_kv_table("Y/N", dict(sorted(counts.items())))))
    else:
        warnings.append("Could not find Draft-2 preservation table (expected headers include `Item ID`, `Preserve posture`, `Superseded by plan?`).")

    # Carry-forward matrix
    cf_txt = read("carry_forward_matrix.md")
    cf_table = find_table_by_headers(cf_txt, ["CF ID", "Posture"])
    if cf_table:
        cf_rows = table_rows_as_dicts(cf_table)
        posture_col = next((h for h in cf_table.header if "posture" in h.lower()), None)
        if posture_col:
            blocks.append(MetricBlock("Carry-forward matrix", _md_kv_table("Carry-forward posture", _count_by(cf_rows, posture_col))))
        else:
            blocks.append(MetricBlock("Carry-forward matrix", f"- Rows: **{len(cf_rows)}**"))
    else:
        warnings.append("Could not find Carry-forward table (expected headers include `CF ID` and `Posture`).")

    # Plan overlay register
    ovl_txt = read("plan_overlay_register.md")
    ovl_table = find_table_by_headers(ovl_txt, ["OVL ID", "Status"])
    if ovl_table:
        ovl_rows = table_rows_as_dicts(ovl_table)
        blocks.append(MetricBlock("Plan overlay register", _md_kv_table("Overlay status", _count_by(ovl_rows, "Status"))))
    else:
        warnings.append("Could not find Plan overlay table (expected headers include `OVL ID` and `Status`).")

    # Supersedence ledger
    sup_txt = read("supersedence_ledger.md")
    sup_table = find_table_by_headers(sup_txt, ["SUP ID", "Status"])
    if sup_table:
        sup_rows = table_rows_as_dicts(sup_table)
        blocks.append(MetricBlock("Supersedence ledger", _md_kv_table("Supersedence status", _count_by(sup_rows, "Status"))))
    else:
        warnings.append("Could not find Supersedence table (expected headers include `SUP ID` and `Status`).")

    # CLI parity deltas
    cli_txt = read("cli_parity_deltas.md")
    cli_table = find_table_by_headers(cli_txt, ["CLI ID", "Status"])
    if cli_table:
        cli_rows = table_rows_as_dicts(cli_table)
        blocks.append(MetricBlock("CLI parity deltas", _md_kv_table("CLI delta status", _count_by(cli_rows, "Status"))))
    else:
        warnings.append("Could not find CLI parity table (expected headers include `CLI ID` and `Status`).")

    # Open questions
    q_txt = read("open_questions.md")
    q_table = find_table_by_headers(q_txt, ["Q ID", "Status"])
    if q_table:
        q_rows = table_rows_as_dicts(q_table)
        blocks.append(MetricBlock("Open questions", _md_kv_table("Question status", _count_by(q_rows, "Status"))))
    else:
        warnings.append("Could not find Open questions table (expected headers include `Q ID` and `Status`).")

    # Change control
    cc_txt = read("change_control.md")
    cc_table = find_table_by_headers(cc_txt, ["CC ID", "Status"])
    if cc_table:
        cc_rows = table_rows_as_dicts(cc_table)
        blocks.append(MetricBlock("Change control", _md_kv_table("Change-control status", _count_by(cc_rows, "Status"))))
    else:
        warnings.append("Could not find Change control table (expected headers include `CC ID` and `Status`).")

    # Roadmap register (optional)
    rr_txt = read("roadmap_register.md")
    if rr_txt:
        rr_table = find_table_by_headers(rr_txt, ["ID", "Status"])
        if rr_table:
            rr_rows = table_rows_as_dicts(rr_table)
            blocks.append(MetricBlock("Roadmap register", _md_kv_table("Roadmap status", _count_by(rr_rows, "Status"))))

    # Anchor changes (optional)
    ac_txt = read("anchor_changes.md")
    if ac_txt:
        ac_table = find_table_by_headers(ac_txt, ["ID", "Doc (path)"])
        if ac_table:
            ac_rows = table_rows_as_dicts(ac_table)
            blocks.append(MetricBlock("Anchor changes", f"- Anchor change rows: **{len(ac_rows)}**"))

    return Metrics(blocks=tuple(blocks), warnings=tuple(warnings))


# -----------------------------
# Progress board update
# -----------------------------

def render_generated_block(metrics: Metrics, *, now: _dt.datetime) -> str:
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    parts: list[str] = []
    parts.append(GENERATED_BEGIN)
    parts.append("")
    parts.append("## Automated roll-up (generated)")
    parts.append("")
    parts.append(f"_Generated: {ts} (local)._\n")

    parts.append("### Warnings")
    parts.append(_md_warning_list(metrics.warnings))
    parts.append("")

    for b in metrics.blocks:
        parts.append(f"### {b.title}")
        parts.append(b.body_md.strip())
        parts.append("")

    parts.append(GENERATED_END)
    return "\n".join(parts).rstrip() + "\n"


def upsert_generated_block(text: str, generated_block: str) -> str:
    if GENERATED_BEGIN in text and GENERATED_END in text:
        pre, rest = text.split(GENERATED_BEGIN, 1)
        _, post = rest.split(GENERATED_END, 1)
        return pre.rstrip() + "\n\n" + generated_block + "\n" + post.lstrip()
    return text.rstrip() + "\n\n" + generated_block


def _write_table(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for r in rows:
        r2 = r + [""] * (len(header) - len(r))
        lines.append("| " + " | ".join(r2[: len(header)]) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_demo(repo_root: Path) -> int:
    """Self-test with synthetic registry data.

    Creates a temporary copy of the repo, injects synthetic rows across multiple registers,
    runs the generator twice (with mutations), and performs basic assertions.

    The demo prints the tail of the generated progress board for human inspection.
    """
    with tempfile.TemporaryDirectory(prefix="exec_contract_demo_") as td:
        dst = Path(td) / "repo"
        shutil.copytree(repo_root, dst, dirs_exist_ok=True)

        regdir = dst / "docs/_internal/policy/execution-contract/registers"
        board = regdir / "progress_board.md"

        _write_table(
            regdir / "rewrite_status.md",
            ["Artifact", "Canonical path (target)", "Owner", "Status", "Last touch (YYYY-MM-DD)", "Next action", "Notes"],
            [
                ["ADR-0003", "`docs/_internal/adr/0003-*.md`", "Alice", "Drafted", "2025-12-18", "Review", ""],
                ["ADR-0004", "`docs/_internal/adr/0004-*.md`", "Bob", "Not started", "", "Map", ""],
                ["CLI docs", "`docs/cli/`", "Chris", "In progress", "2025-12-18", "Draft", ""],
            ],
        )

        _write_table(
            regdir / "master_mapping_ledger.md",
            ["Row ID", "Source ID", "Source anchor (heading / location)", "Destination doc", "Destination anchor", "Type (`preserve`/`overlay`)", "Status", "Evidence (link/commit/PR)", "Notes"],
            [
                ["MAP-0001", "D2-0003", "pipeline", "ADR-0003", "#pipeline", "preserve", "drafted", "c1", ""],
                ["MAP-0002", "PLAN-v18", "overlay A", "ADR-0003", "#overlay", "overlay", "planned", "", ""],
                ["MAP-0003", "D2-0004", "taxonomy", "ADR-0004", "#taxonomy", "preserve", "reviewed", "c2", ""],
                ["MAP-0004", "CLI-H", "help", "docs/cli/flags.md", "#flags", "overlay", "accepted", "c3", ""],
            ],
        )

        _write_table(
            regdir / "plan_overlay_register.md",
            ["OVL ID", "Plan anchor (section/heading)", "Delta summary (one line)", "Affected targets (docs)", "Ownership impact? (Y/N)", "Evidence (link/commit/PR)", "Status", "Notes"],
            [
                ["OVL-0001", "§2.2", "Add overlay", "ADR-0003", "N", "c2", "applied", ""],
                ["OVL-0002", "§3.1", "Rename flag", "docs/cli/flags.md", "N", "", "planned", ""],
            ],
        )

        _write_table(
            regdir / "open_questions.md",
            ["Q ID", "Question / ambiguity", "Affected concepts", "Blocked targets", "Owner", "Proposed resolution", "Status", "Date opened"],
            [
                ["Q-0001", "What is canonical manifest alias?", "manifest", "CLI docs", "Chris", "Decide in ADR-0003", "open", "2025-12-18"],
                ["Q-0002", "Do we allow X?", "X", "ADR-0004", "Bob", "Defer", "resolved", "2025-12-18"],
            ],
        )

        # Ensure markers exist
        txt = board.read_text(encoding="utf-8")
        if GENERATED_BEGIN not in txt or GENERATED_END not in txt:
            txt = txt.rstrip() + "\n\n" + GENERATED_BEGIN + "\n\n" + GENERATED_END + "\n"
            board.write_text(txt, encoding="utf-8")

        # Run once
        m1 = compute_metrics(regdir)
        g1 = render_generated_block(m1, now=_dt.datetime(2025, 12, 18, 12, 0, 0))
        board.write_text(upsert_generated_block(board.read_text(encoding="utf-8"), g1), encoding="utf-8")

        # Mutate and re-run
        mm = (regdir / "master_mapping_ledger.md").read_text(encoding="utf-8")
        mm = mm.replace("| MAP-0002 | PLAN-v18 | overlay A | ADR-0003 | #overlay | overlay | planned |", "| MAP-0002 | PLAN-v18 | overlay A | ADR-0003 | #overlay | overlay | drafted |")
        (regdir / "master_mapping_ledger.md").write_text(mm, encoding="utf-8")

        oq = (regdir / "open_questions.md").read_text(encoding="utf-8").splitlines()
        oq.append("| Q-0003 | Missing schema field? | findings | docs/reference/findings.md | Alice | Define in spec | open | 2025-12-18 |")
        (regdir / "open_questions.md").write_text("\n".join(oq) + "\n", encoding="utf-8")

        m2 = compute_metrics(regdir)
        g2 = render_generated_block(m2, now=_dt.datetime(2025, 12, 18, 13, 0, 0))
        board.write_text(upsert_generated_block(board.read_text(encoding="utf-8"), g2), encoding="utf-8")

        out = board.read_text(encoding="utf-8")
        if "## Automated roll-up (generated)" not in out:
            print("DEMO FAIL: missing generated section", file=sys.stderr)
            return 2
        if "| open |" not in out:
            print("DEMO FAIL: open questions roll-up missing", file=sys.stderr)
            return 2

        print("DEMO PASS. Tail of generated progress_board.md:")
        print("\n".join(out.splitlines()[-80:]))
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Path to repository root (default: .)")
    ap.add_argument(
        "--register-dir",
        default="docs/_internal/policy/execution-contract/registers",
        help="Registry directory relative to repo root.",
    )
    ap.add_argument(
        "--progress-board",
        default="docs/_internal/policy/execution-contract/registers/progress_board.md",
        help="Progress board markdown path relative to repo root.",
    )
    ap.add_argument("--write", action="store_true", help="Write changes to progress_board.md")
    ap.add_argument("--print", dest="do_print", action="store_true", help="Print generated block to stdout")
    ap.add_argument("--demo", action="store_true", help="Run demo self-test with synthetic registry data")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()

    if args.demo:
        return _run_demo(repo_root)

    register_dir = (repo_root / args.register_dir).resolve()
    board_path = (repo_root / args.progress_board).resolve()

    if not register_dir.exists():
        print(f"ERROR: register dir not found: {register_dir}", file=sys.stderr)
        return 2
    if not board_path.exists():
        print(f"ERROR: progress board not found: {board_path}", file=sys.stderr)
        return 2

    metrics = compute_metrics(register_dir)
    generated = render_generated_block(metrics, now=_dt.datetime.now())

    if args.do_print and not args.write:
        print(generated)
        return 0

    if args.write:
        original = board_path.read_text(encoding="utf-8")
        updated = upsert_generated_block(original, generated)
        if updated != original:
            board_path.write_text(updated, encoding="utf-8")
        if args.do_print:
            print(generated)
        return 0

    print("No action specified. Use --write to update progress_board.md or --print to preview.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
