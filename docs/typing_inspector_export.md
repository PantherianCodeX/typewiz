## Exporting Typing Inspector to a standalone repository

Use the following checklist to promote `typing_inspector` into its own reusable package.

### 1. Create the new repository

1. `mkdir typing-inspector && cd typing-inspector`
2. `git init`
3. `gh repo create org/typing-inspector --source=. --public` (or create manually).

### 2. Copy the package

From the current project root:

```bash
rsync -av --progress src/typing_inspector/ ../typing-inspector/src/typing_inspector/
rsync -av docs/typing_inspector.md ../typing-inspector/docs/
```

Include example manifests to exercise the dashboard (optional):

```bash
cp docs/typing/typing_audit_manifest.json ../typing-inspector/examples/typing_audit_manifest.json
```

### 3. Add packaging metadata

Within the new repo:

```bash
cat > pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "typing-inspector"
version = "0.1.0"
description = "Typing diagnostics aggregator for pyright and mypy"
readme = "README.md"
requires-python = ">=3.10"
dependencies = ["pyright>=1.1.392", "mypy>=1.8.0"]
EOF
```

Add `README.md` summarising usage and commands. Copy `docs/typing/typing_inspector.md` as a starting point.

### 4. Provide CLI entry points

Add to `pyproject.toml`:

```toml
[project.scripts]
typing-inspector = "typing_inspector.cli:main"
```

This maps `typing-inspector` to the existing `main()` function.

### 5. Tests & formatting

- Create `tests/test_smoke.py` with a simple `subprocess.run(["typing-inspector", "audit", "--skip-full"])`.
- Add pre-commit or lint config if desired.

### 6. Publish or vendor

```bash
pip install build
python -m build
twine upload dist/*
```

Or vendor the package by committing the directory into another repo’s `libs/` folder.

### 7. Update downstream repos

- `pip install typing-inspector`
- Run nightly workflows from the new package instead of the in-repo copy.

### 8. Remove the embedded copy (optional)

Once other repos transition, drop `typing_inspector/` from this project and replace CLI usages with the published package.
