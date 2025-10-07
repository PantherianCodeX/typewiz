from __future__ import annotations

from pathlib import Path

from typewiz.api import run_audit
from typewiz.cli import main
from typewiz.config import AuditConfig, Config
from typewiz.engines.base import EngineContext, EngineResult


class RecordingEngine:
    name = "stub"

    def run(self, context: EngineContext, paths):
        return EngineResult(
            engine=self.name,
            mode=context.mode,
            command=["stub", context.mode],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[],
        )

    def category_mapping(self):
        return {}

    def fingerprint_targets(self, context: EngineContext, paths):
        return []


def test_manifest_validates_against_schema(monkeypatch, tmp_path: Path):
    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "mod.py").write_text("x=1\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"

    override = AuditConfig(full_paths=["src"], runners=["stub"])
    run_audit(project_root=tmp_path, override=override, write_manifest_to=manifest_path)

    # Use the CLI validator to exercise both the jsonschema and fallback paths
    code = main(["manifest", "validate", str(manifest_path)])
    assert code == 0

