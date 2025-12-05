# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Install a built typewiz wheel inside an isolated throwaway virtualenv."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess  # noqa: S404  # JUSTIFIED: invokes trusted pip/python binaries inside freshly created venv
import tempfile
import venv


def _find_wheel(dist_dir: pathlib.Path) -> pathlib.Path:
    candidates = sorted(dist_dir.glob("typewiz-*.whl"))
    if not candidates:
        raise SystemExit(MISSING_WHEEL_MSG)
    return candidates[-1]


MISSING_WHEEL_MSG = "No typewiz wheel found in dist/. Run `make package.build` first."


def main() -> int:
    """Create a disposable venv and install a built wheel in it.

    Returns:
        ``0`` after pip installs the provided (or latest) wheel and verifies the
        package can be imported inside the temporary environment.
    """
    parser = argparse.ArgumentParser(
        description="Install a built typewiz wheel in an isolated virtualenv",
    )
    _ = parser.add_argument(
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

        _ = subprocess.run(  # noqa: S603  # JUSTIFIED: executes pinned pip within controlled virtualenv
            [str(pip_path), "install", str(wheel_path)],
            check=True,
        )
        _ = subprocess.run(  # noqa: S603  # JUSTIFIED: validates installed package using dedicated interpreter
            [str(python_path), "-c", "import typewiz"],
            check=True,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
