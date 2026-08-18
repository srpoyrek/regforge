"""Optional post-processing of generated source through external formatters.

Writers produce clean source directly, but projects usually have a house
formatting style. For C-family output, regforge can pipe the generated text
through `uncrustify <https://github.com/uncrustify/uncrustify>`_ using a
bundled default configuration or one supplied by the caller. This runs on the
generated output only; it never touches regforge's own sources.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

#: Configuration shipped with regforge, applied when no override is given.
DEFAULT_UNCRUSTIFY_CONFIG = Path(__file__).parent / "formatting" / "uncrustify.cfg"

#: Mapping from a writer's ``language`` attribute to an uncrustify language id.
_UNCRUSTIFY_LANGUAGES = {"C": "C", "CPP": "CPP"}


class FormatterNotAvailable(RuntimeError):
    """Raised when a requested external formatter is not installed."""


def uncrustify_available() -> bool:
    """Return ``True`` if the ``uncrustify`` executable is on ``PATH``."""
    return shutil.which("uncrustify") is not None


def uncrustify(
    source: str,
    language: str = "C",
    config: str | Path | None = None,
) -> str:
    """Return ``source`` reformatted by uncrustify.

    Args:
        source: The generated source text to format.
        language: The writer's language identifier (``"C"`` or ``"CPP"``).
        config: Path to an uncrustify configuration file. Defaults to the
            configuration bundled with regforge.

    Raises:
        FormatterNotAvailable: If uncrustify is not installed.
        ValueError: If ``language`` is not supported by uncrustify.
        subprocess.CalledProcessError: If uncrustify exits with an error.
    """
    if not uncrustify_available():
        raise FormatterNotAvailable("uncrustify was not found on PATH")

    uncrustify_language = _UNCRUSTIFY_LANGUAGES.get(language.upper())
    if uncrustify_language is None:
        raise ValueError(f"uncrustify does not support language {language!r}")

    config_path = Path(config) if config is not None else DEFAULT_UNCRUSTIFY_CONFIG
    completed = subprocess.run(
        ["uncrustify", "-c", str(config_path), "-l", uncrustify_language, "-q"],
        input=source,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout
