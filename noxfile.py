from __future__ import annotations

import nox


@nox.session(python="3.12")
def tests(session: nox.Session) -> None:
    session.install("-r", "requirements-dev.txt")
    session.run("pytest", "-q", *session.posargs)


@nox.session(python=False)
def mypy(session: nox.Session) -> None:
    session.install("-r", "requirements.txt")
    session.run("mypy", "--config-file", "mypy.ini", *session.posargs)


@nox.session(python=False)
def pyright(session: nox.Session) -> None:
    session.install("-r", "requirements.txt")
    session.run("pyright", "-p", "pyrightconfig.json", *session.posargs)


# Alias with version suffix for CI convenience
@nox.session(name="tests-3.12", python="3.12")
def tests_312(session: nox.Session) -> None:
    tests(session)

