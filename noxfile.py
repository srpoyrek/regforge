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
* ``misra``     -- check the golden headers against MISRA C:2012 with cppcheck's addon.
"""

import os
import shutil
import subprocess
import sys

import nox

nox.options.sessions = ["tests", "lint", "types"]
# uv builds each session's environment far faster than virtualenv, so use it
# where it is installed (it is a dev dependency) and fall back to virtualenv
# where it is not, rather than failing outright.
nox.options.default_venv_backend = "uv|virtualenv"

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


#: MISRA C:2012 advisory rules the generated header deviates from, each documented
#: in the header's own preamble: 11.4 (integer to pointer, memory-mapped I/O),
#: 19.2 (a union for alternateRegister overlays), 2.3 / 2.4 / 2.5 / 8.9 (rules
#: scoped to one translation unit, meaningless for a definitions header).
MISRA_DEVIATIONS = ("2.3", "2.4", "2.5", "8.9", "11.4", "19.2")


@nox.session(venv_backend="none")
def misra(session: nox.Session) -> None:
    """Check the golden headers against MISRA C:2012 with cppcheck's MISRA addon.

    cppcheck is an external tool (apt / choco / brew install cppcheck); set
    ``REGFORGE_CPPCHECK`` to point at a binary that is not on PATH. Every
    required rule must hold; the advisory deviations above are suppressed.
    ``--platform=unix32`` gives essential-type analysis a 32-bit MCU ABI.
    """
    cppcheck = os.environ.get("REGFORGE_CPPCHECK") or shutil.which("cppcheck")
    if cppcheck is None:
        session.error(
            "cppcheck is not on PATH. Install it (apt install cppcheck, choco install "
            "cppcheck, winget install Cppcheck.Cppcheck, brew install cppcheck) or set "
            "REGFORGE_CPPCHECK to the binary"
        )
    # A cppcheck bundled inside another tool (Strawberry Perl ships one) can have
    # its configuration directory baked to a path that exists only on the build
    # machine; it then fails on every file. Say so, rather than echo its message.
    probe = subprocess.run(
        [cppcheck, "--quiet", "tests/golden/c/minimal.h"], capture_output=True, text=True
    )
    if "Failed to load" in probe.stdout + probe.stderr:
        session.error(
            f"{cppcheck} cannot find its own configuration files (a broken build, "
            "typically one bundled inside another tool). Install the official cppcheck "
            "so it comes first on PATH, or set REGFORGE_CPPCHECK to a working binary"
        )
    session.run(
        cppcheck,
        "--addon=misra",
        f"--addon-python={sys.executable}",
        "--std=c99",
        "--platform=unix32",
        "--enable=style",
        "--error-exitcode=1",
        "--suppress=missingIncludeSystem",
        "--suppress=unusedStructMember",  # cppcheck's own per-TU check, not MISRA
        *(f"--suppress=misra-c2012-{rule}" for rule in MISRA_DEVIATIONS),
        "--template={file}:{line}: {id} {message}",
        "tests/golden/c/minimal.h",
        "tests/golden/c/lint_demo.h",
        external=True,
    )


@nox.session
def sizes(session: nox.Session) -> None:
    """Print generated-header size per compiler and optimization level.

    Object-level bytes (text/data/bss) for each GNU toolchain on PATH; skips any
    that are absent. Needs no dependencies -- it only reads the golden header.
    """
    session.run("python", "-m", "tools.size_report", *session.posargs)
