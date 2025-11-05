from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import tempfile
import venv


def _find_wheel(dist_dir: pathlib.Path) -> pathlib.Path:
    candidates = sorted(dist_dir.glob("typewiz-*.whl"))
    if not candidates:
        raise SystemExit(MISSING_WHEEL_MSG)
    return candidates[-1]


MISSING_WHEEL_MSG = "No typewiz wheel found in dist/. Run `make package.build` first."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install a built typewiz wheel in an isolated virtualenv"
    )
    parser.add_argument(
        "--wheel",
        type=pathlib.Path,
        default=None,
        help="Optional path to the wheel to install (defaults to latest typewiz-*.whl in dist/)",
    )
    args = parser.parse_args()

    dist_dir = pathlib.Path("dist")
    wheel_path = args.wheel if args.wheel is not None else _find_wheel(dist_dir)

    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix="typewiz-install-"))
    venv_dir = tmp_dir / "venv"

    try:
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        if os.name == "nt":
            pip_path = venv_dir / "Scripts" / "pip.exe"
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            pip_path = venv_dir / "bin" / "pip"
            python_path = venv_dir / "bin" / "python"

        subprocess.run([str(pip_path), "install", str(wheel_path)], check=True)  # noqa: S603
        subprocess.run([str(python_path), "-c", "import typewiz"], check=True)  # noqa: S603
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
