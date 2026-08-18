"""Output-target writers and their registry.

A writer converts the intermediate representation into source text for a
target language. Writers register themselves here so the CLI can look them up
by name (``--to c``) or infer them from an output file extension.

To add a new output target:

1. Subclass :class:`~regforge.writers.base.Writer` in a new module.
2. Register it with :func:`register_writer`.
"""

from __future__ import annotations

from pathlib import Path

from .base import Writer
from .c import CWriter

_WRITERS: dict[str, type[Writer]] = {}


def register_writer(writer_cls: type[Writer]) -> type[Writer]:
    """Register ``writer_cls`` under its :attr:`~Writer.target_name`.

    Returns the class unchanged so it may be used as a decorator.
    """
    if not writer_cls.target_name:
        raise ValueError(f"{writer_cls.__name__} must define a non-empty target_name")
    _WRITERS[writer_cls.target_name] = writer_cls
    return writer_cls


def available_writers() -> list[str]:
    """Return the sorted names of all registered output targets."""
    return sorted(_WRITERS)


def get_writer(target_name: str) -> Writer:
    """Return a writer instance for ``target_name``.

    Raises:
        ValueError: If no writer is registered for the given target.
    """
    try:
        writer_cls = _WRITERS[target_name]
    except KeyError:
        raise ValueError(
            f"unknown output target {target_name!r}; "
            f"available targets: {', '.join(available_writers())}"
        ) from None
    return writer_cls()


def writer_for_path(path: str | Path) -> Writer:
    """Return a writer chosen from ``path``'s file extension.

    Raises:
        ValueError: If no registered writer produces the extension.
    """
    extension = Path(path).suffix.lower()
    for writer_cls in _WRITERS.values():
        if writer_cls.file_extension == extension:
            return writer_cls()
    raise ValueError(
        f"cannot infer output target from extension {extension!r}; "
        f"specify one with --to ({', '.join(available_writers())})"
    )


register_writer(CWriter)

__all__ = [
    "Writer",
    "CWriter",
    "register_writer",
    "available_writers",
    "get_writer",
    "writer_for_path",
]
