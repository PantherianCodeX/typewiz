from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
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
