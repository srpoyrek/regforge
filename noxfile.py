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
from pathlib import Path

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


#: Where this repository keeps a copy of the addon for platforms whose cppcheck
#: package omits it (the Windows installer ships no addons). Git-ignored: the
#: addon is cppcheck's, GPL-3, and is never committed here.
MISRA_ADDON_LOCAL = ".cppcheck/addons/misra.py"

#: The layouts a cppcheck distribution uses for its own addons, relative to the
#: binary or absolute. Anywhere else is machine-specific and belongs in
#: ``REGFORGE_MISRA_ADDON``, not here.
MISRA_ADDON_PATHS = (
    "addons/misra.py",
    "../share/cppcheck/addons/misra.py",
    "../share/Cppcheck/addons/misra.py",
    "/usr/share/cppcheck/addons/misra.py",
    "/usr/local/share/cppcheck/addons/misra.py",
)


def _misra_addon(cppcheck: str) -> str:
    """The ``--addon`` argument to use: an absolute misra.py, else the bare name.

    ``REGFORGE_MISRA_ADDON`` wins, then the usual places beside the binary and
    under ``share/cppcheck``. Falling back to the bare ``misra`` lets cppcheck
    search its own install directory, which is how the Linux packages work.
    """
    explicit = os.environ.get("REGFORGE_MISRA_ADDON")
    if explicit:
        return explicit
    local = Path(__file__).parent / MISRA_ADDON_LOCAL
    if local.is_file():
        return str(local.resolve())
    binary = Path(cppcheck).resolve().parent
    for relative in MISRA_ADDON_PATHS:
        candidate = Path(relative)
        candidate = candidate if candidate.is_absolute() else binary / candidate
        if candidate.is_file():
            return str(candidate.resolve())
    return "misra"


@nox.session(venv_backend="none")
def misra(session: nox.Session) -> None:
    """Check the golden headers against MISRA C:2012 with cppcheck's MISRA addon.

    cppcheck is an external tool (``apt install cppcheck``, ``brew install
    cppcheck``); set ``REGFORGE_CPPCHECK`` for a binary that is not on PATH.
    The check is the addon, ``misra.py``, which ships with the Linux packages
    but not with the Windows installer. Where it is missing, take ``misra.py``,
    ``misra_9.py`` and ``cppcheckdata.py`` from the cppcheck release that
    matches the binary and either put them in an ``addons`` directory beside
    it, which is where cppcheck itself looks, or point
    ``REGFORGE_MISRA_ADDON`` at the ``misra.py`` wherever you keep it. All
    three must come from that one release: the addon parses the binary's dump
    format, and a mismatch is reported as one.

    No rule is turned off: the session passes no suppression of any kind, so
    every finding the addon produces fails it. ``--platform=unix32`` gives the
    essential-type rules a 32-bit MCU ABI, and ``--enable=style`` is what
    surfaces the addon's findings at all -- without it cppcheck reports none.
    """
    cppcheck = os.environ.get("REGFORGE_CPPCHECK") or shutil.which("cppcheck")
    if cppcheck is None:
        session.error(
            "cppcheck is not on PATH. Install it (apt install cppcheck, brew install "
            "cppcheck, winget install Cppcheck.Cppcheck) or set REGFORGE_CPPCHECK to "
            "the binary"
        )
    addon = _misra_addon(cppcheck)
    # Probe on one of the headers this session checks, so a broken install or a
    # mismatched addon is reported as itself rather than as a wall of cppcheck
    # output. A toy source would not exercise the addon far enough to tell.
    probe = subprocess.run(
        [
            cppcheck,
            f"--addon={addon}",
            f"--addon-python={sys.executable}",
            "--quiet",
            "tests/golden/c/minimal.h",
        ],
        capture_output=True,
        text=True,
    )
    trouble = probe.stdout + probe.stderr
    if "Failed to load" in trouble:
        session.error(
            f"{cppcheck} cannot find its own configuration files (a broken build, "
            "typically one bundled inside another tool). Install the official cppcheck "
            "so it comes first on PATH, or set REGFORGE_CPPCHECK to a working binary"
        )
    if "Did not find addon" in trouble:
        session.error(
            f"{cppcheck} ships no misra.py (the Windows installer does not). Download "
            "addons/misra.py and addons/cppcheckdata.py from the cppcheck release that "
            "matches this binary and set REGFORGE_MISRA_ADDON to the misra.py"
        )
    if "Failed to execute addon" in trouble or "internalError" in trouble:
        session.error(
            f"{addon} could not run against {cppcheck}. The usual cause is a version mismatch: "
            "the addon parses the binary's dump format, so misra.py must come from the "
            f"same cppcheck release. cppcheck said: {trouble.strip().splitlines()[0]}"
        )
    session.run(
        cppcheck,
        f"--addon={addon}",
        f"--addon-python={sys.executable}",
        "--std=c99",
        "--platform=unix32",
        "--enable=style",
        "--error-exitcode=1",
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
