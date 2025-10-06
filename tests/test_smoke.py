from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = cwd / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".strip(os.pathsep)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise AssertionError(f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def test_audit_and_dashboard(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = tmp_path / "manifest.json"

    run(
        [
            "python",
            "-m",
            "typing_inspector",
            "audit",
            "--skip-full",
            "--pyright-only",
            "--manifest",
            str(manifest),
        ],
        cwd=repo_root,
    )
    assert manifest.exists()

    dashboard = run(
        [
            "python",
            "-m",
            "typing_inspector",
            "dashboard",
            "--manifest",
            str(manifest),
            "--format",
            "json",
        ],
        cwd=repo_root,
    )
    data = json.loads(dashboard.stdout)
    assert "runSummary" in data

    # Programmatic API usage with overrides and HTML output
    from typing_inspector import AuditConfig, run_audit

    override = AuditConfig(
        skip_full=True,
        mypy_only=True,
        full_paths=["src"],
        manifest_path=tmp_path / "api_manifest.json",
        dashboard_html=tmp_path / "dashboard.html",
    )
    result = run_audit(
        project_root=repo_root,
        override=override,
        build_summary_output=True,
    )
    assert result.summary is not None
    assert (tmp_path / "dashboard.html").exists()
