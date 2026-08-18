"""Task automation for regforge.

Run a single session with ``nox -s <name>``; run the default set (tests and
lint) with a bare ``nox``. Sessions:

* ``tests``   -- run the pytest suite.
* ``lint``    -- check formatting and lint rules without modifying files.
* ``format``  -- apply ruff fixes and black formatting in place.
* ``build``   -- build the wheel and source distribution.
* ``goldens`` -- regenerate the golden test fixtures.
"""

import nox

nox.options.sessions = ["tests", "lint"]

PYTHON_PATHS = ["regforge", "tests", "noxfile.py"]


@nox.session
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    session.install("-e", ".[dev]")
    session.run("pytest", *session.posargs)


@nox.session
def lint(session: nox.Session) -> None:
    """Check formatting and lint rules."""
    session.install("ruff>=0.5", "black>=24")
    session.run("ruff", "check", *PYTHON_PATHS)
    session.run("black", "--check", *PYTHON_PATHS)


@nox.session
def format(session: nox.Session) -> None:
    """Apply formatting and lint fixes in place."""
    session.install("ruff>=0.5", "black>=24")
    session.run("ruff", "check", "--fix", *PYTHON_PATHS)
    session.run("black", *PYTHON_PATHS)


@nox.session
def build(session: nox.Session) -> None:
    """Build the distribution artifacts."""
    session.install("build")
    session.run("python", "-m", "build")


@nox.session
def goldens(session: nox.Session) -> None:
    """Regenerate golden test fixtures from their inputs."""
    session.install("-e", ".")
    session.run(
        "python",
        "-m",
        "regforge",
        "tests/svd/minimal.svd",
        "-o",
        "tests/golden/minimal.h",
    )
