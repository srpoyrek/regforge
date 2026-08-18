"""Input-format readers and their registry.

A reader converts a device description in some source format into the
intermediate representation. Readers register themselves here so the CLI can
look them up by name (``--from svd``) or infer them from a file extension.

To add a new input format:

1. Subclass :class:`~regforge.readers.base.Reader` in a new module.
2. Register it with :func:`register_reader`.
"""

from __future__ import annotations

from pathlib import Path

from .base import Reader, Source
from .svd import SvdReader

_READERS: dict[str, type[Reader]] = {}


def register_reader(reader_cls: type[Reader]) -> type[Reader]:
    """Register ``reader_cls`` under its :attr:`~Reader.format_name`.

    Returns the class unchanged so it may be used as a decorator.
    """
    if not reader_cls.format_name:
        raise ValueError(f"{reader_cls.__name__} must define a non-empty format_name")
    _READERS[reader_cls.format_name] = reader_cls
    return reader_cls


def available_readers() -> list[str]:
    """Return the sorted names of all registered input formats."""
    return sorted(_READERS)


def get_reader(format_name: str) -> Reader:
    """Return a reader instance for ``format_name``.

    Raises:
        ValueError: If no reader is registered for the given format.
    """
    try:
        reader_cls = _READERS[format_name]
    except KeyError:
        raise ValueError(
            f"unknown input format {format_name!r}; "
            f"available formats: {', '.join(available_readers())}"
        ) from None
    return reader_cls()


def reader_for_path(path: str | Path) -> Reader:
    """Return a reader chosen from ``path``'s file extension.

    Raises:
        ValueError: If no registered reader handles the extension.
    """
    extension = Path(path).suffix.lower()
    for reader_cls in _READERS.values():
        if extension in reader_cls.file_extensions:
            return reader_cls()
    raise ValueError(
        f"cannot infer input format from extension {extension!r}; "
        f"specify one with --from ({', '.join(available_readers())})"
    )


register_reader(SvdReader)

__all__ = [
    "Reader",
    "Source",
    "SvdReader",
    "register_reader",
    "available_readers",
    "get_reader",
    "reader_for_path",
]
