from __future__ import annotations

from pathlib import Path

from typing_inspector.config import AuditConfig, load_config


def test_load_config_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "typing_inspector.toml"
    config_path.write_text(
        """
[audit]
full_paths = ["apps", "packages"]
skip_full = true
max_depth = 5
pyright_args = ["--pythonversion", "3.12"]
dashboard_html = "reports/dashboard.html"
""",
        encoding="utf-8",
    )
    cfg = load_config(config_path)
    assert cfg.audit.full_paths == ["apps", "packages"]
    assert cfg.audit.skip_full is True
    assert cfg.audit.max_depth == 5
    assert cfg.audit.dashboard_html == (config_path.parent / "reports" / "dashboard.html")


def test_audit_config_override() -> None:
    base = AuditConfig(full_paths=["apps"], pyright_args=["--foo"])
    override = AuditConfig(full_paths=["apps", "packages"], pyright_args=["--bar"], skip_full=True)
    # manual merge
    merged = AuditConfig(
        manifest_path=override.manifest_path or base.manifest_path,
        full_paths=override.full_paths or base.full_paths,
        max_depth=override.max_depth or base.max_depth,
        skip_current=override.skip_current if override.skip_current is not None else base.skip_current,
        skip_full=override.skip_full if override.skip_full is not None else base.skip_full,
        pyright_only=override.pyright_only if override.pyright_only is not None else base.pyright_only,
        mypy_only=override.mypy_only if override.mypy_only is not None else base.mypy_only,
        pyright_args=(base.pyright_args or []) + (override.pyright_args or []),
        mypy_args=(base.mypy_args or []) + (override.mypy_args or []),
        fail_on=override.fail_on or base.fail_on,
        dashboard_json=override.dashboard_json or base.dashboard_json,
        dashboard_markdown=override.dashboard_markdown or base.dashboard_markdown,
        dashboard_html=override.dashboard_html or base.dashboard_html,
    )
    assert merged.full_paths == ["apps", "packages"]
    assert merged.pyright_args == ["--foo", "--bar"]
    assert merged.skip_full is True
