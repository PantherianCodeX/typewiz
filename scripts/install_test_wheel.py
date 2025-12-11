# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Install a built ratchetr wheel inside an isolated throwaway virtualenv."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil

# ignore JUSTIFIED: helper invokes pip/python only inside an isolated, temporary
# virtualenv
import subprocess  # noqa: S404
import tempfile
import venv


def _find_wheel(dist_dir: pathlib.Path) -> pathlib.Path:
    candidates = sorted(dist_dir.glob("ratchetr-*.whl"))
    if not candidates:
        raise SystemExit(MISSING_WHEEL_MSG)
    return candidates[-1]


MISSING_WHEEL_MSG = "No ratchetr wheel found in dist/. Run `make package.build` first."


def main() -> int:
    """Create a disposable venv and install a built wheel in it.

    Returns:
        ``0`` after pip installs the provided (or latest) wheel and verifies the
        package can be imported inside the temporary environment.
    """
    parser = argparse.ArgumentParser(
        description="Install a built ratchetr wheel in an isolated virtualenv",
    )
    _ = parser.add_argument(
        "--wheel",
        type=pathlib.Path,
        default=None,
        help="Optional path to the wheel to install (defaults to latest ratchetr-*.whl in dist/)",
    )
    args = parser.parse_args()

    dist_dir = pathlib.Path("dist")
    wheel_path = args.wheel if args.wheel is not None else _find_wheel(dist_dir)

    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix="ratchetr-install-"))
    venv_dir = tmp_dir / "venv"

    try:
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        if os.name == "nt":
            pip_path = venv_dir / "Scripts" / "pip.exe"
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            pip_path = venv_dir / "bin" / "pip"
            python_path = venv_dir / "bin" / "python"

        # ignore JUSTIFIED: pip is executed from the freshly created virtualenv with a
        # fixed argument list
        _ = subprocess.run(  # noqa: S603
            [str(pip_path), "install", str(wheel_path)],
            check=True,
        )
        # ignore JUSTIFIED: python interpreter from the virtualenv is executed with a
        # fixed validation command
        _ = subprocess.run(  # noqa: S603
            [str(python_path), "-c", "import ratchetr"],
            check=True,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
