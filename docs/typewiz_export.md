# Exporting typewiz to a standalone repository

Use the following checklist to promote `typewiz` into its own reusable package.

## 1. Create the new repository

1. `mkdir typewiz && cd typewiz`
2. `git init`
3. `gh repo create org/typewiz --source=. --public` (or create manually).

## 2. Copy the package

From the current project root:

```bash
rsync -av --progress src/typewiz/ ../typewiz/src/typewiz/
rsync -av docs/typewiz.md ../typewiz/docs/
```

Include example manifests to exercise the dashboard (optional):

```bash
cp docs/typing/typing_audit_manifest.json ../typewiz/examples/typing_audit_manifest.json
```

## 3. Add packaging metadata

Within the new repo:

```bash
cat > pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "typewiz"
version = "0.1.0"
description = "Typing diagnostics aggregator for pyright and mypy"
readme = "README.md"
requires-python = ">=3.12"
dependencies = ["pyright>=1.1.392", "mypy>=1.8.0"]
EOF
```

Add `README.md` summarising usage and commands. Copy `docs/typewiz.md` as a starting point.

## 4. Provide CLI entry points

Add to `pyproject.toml`:

```toml
[project.scripts]
typewiz = "typewiz.cli:main"
```

This maps `typewiz` to the existing `main()` function.

## 5. Tests & formatting

- Create `tests/test_smoke.py` with a simple `subprocess.run(["typewiz", "audit", "--skip-full"])`.
- Add pre-commit or lint config if desired.
- Add `.typewiz_cache/` to `.gitignore` to avoid committing local caches.

## 6. Publish or vendor

```bash
pip install build
python -m build
twine upload dist/*
```

Keep the public version in the `0.1.x` line while the API settles; bump to `0.2.x`
when you're ready to promise stronger compatibility guarantees. Or vendor the package by committing the directory into another repo’s
`libs/` folder.

## 7. Update downstream repos

- `pip install typewiz`
- Run nightly workflows from the new package instead of the in-repo copy.

## 8. Remove the embedded copy (optional)

Once other repos transition, drop `typewiz/` from this project and replace CLI usages with the published package.
