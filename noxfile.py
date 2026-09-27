"""Task automation for regforge.

Run a single session with ``nox -s <name>``; run the default set (tests and
lint) with a bare ``nox``. Sessions:

* ``tests``   -- run the pytest suite.
* ``lint``    -- check formatting and lint rules without modifying files.
* ``types``   -- static type-check the sources with pyright.
* ``format``  -- apply ruff fixes and black formatting in place.
* ``build``     -- build the wheel and source distribution.
* ``goldens``   -- regenerate the golden test fixtures.
* ``compilers`` -- compile the golden header with every C/C++ compiler on PATH.
* ``sizes``     -- report generated-header size per compiler / optimization level.
"""

import nox

nox.options.sessions = ["tests", "lint", "types"]
# uv builds each session's environment far faster than virtualenv; it is a
# dev dependency (pyproject.toml), so `pip install -e ".[dev]"` provides it.
nox.options.default_venv_backend = "uv"

PYTHON_PATHS = ["regforge", "tests", "tools", "noxfile.py"]


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
def docs(session: nox.Session) -> None:
    """Build the documentation site; a broken link or missing nav entry fails."""
    session.install("mkdocs>=1.6,<2", "mkdocs-material>=9")
    session.run("mkdocs", "build", "--strict")


@nox.session
def types(session: nox.Session) -> None:
    """Static type-check the sources with pyright."""
    session.install("-e", ".[dev]")
    session.run("pyright")


@nox.session
def format(session: nox.Session) -> None:
    """Apply formatting and lint fixes in place."""
    session.install("ruff>=0.5", "black>=24")
    session.run("ruff", "check", "--fix", *PYTHON_PATHS)
    session.run("black", *PYTHON_PATHS)


@nox.session
def build(session: nox.Session) -> None:
    """Build the distribution artifacts and the documentation site.

    The site goes to ``site/`` and is built strictly, so a release build fails
    on a broken documentation link rather than shipping one.
    """
    session.install("build", "mkdocs>=1.6,<2", "mkdocs-material>=9")
    session.run("python", "-m", "build")
    session.run("mkdocs", "build", "--strict")


@nox.session
def goldens(session: nox.Session) -> None:
    """Regenerate golden test fixtures from their inputs."""
    session.install("-e", ".")
    for name in ("minimal", "lint_demo"):
        session.run(
            "python",
            "-m",
            "regforge",
            f"tests/fixtures/svd/{name}.svd",
            "-o",
            f"tests/golden/c/{name}.h",
        )


@nox.session
def compilers(session: nox.Session) -> None:
    """Compile the golden header with every C/C++ compiler found on PATH.

    The matrix skips toolchains that are absent, so this reports on whatever is
    installed; run it wherever a compiler you care about is available.
    """
    session.install("-e", ".[dev]")
    session.run(
        "pytest",
        "tests/writers/c/test_compiles.py",
        "-v",
        *session.posargs,
    )


@nox.session
def sizes(session: nox.Session) -> None:
    """Print generated-header size per compiler and optimization level.

    Object-level bytes (text/data/bss) for each GNU toolchain on PATH; skips any
    that are absent. Needs no dependencies -- it only reads the golden header.
    """
    session.run("python", "-m", "tools.size_report", *session.posargs)
