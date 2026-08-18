"""Reader interface.

A reader turns a device description written in some input format into a
:class:`~regforge.ir.Device`. Concrete readers subclass :class:`Reader`,
declare the format they handle, and are registered with the reader registry
in :mod:`regforge.readers`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from ..ir import Device

#: A reader input: a filesystem path.
Source = Union[str, Path]


class Reader(ABC):
    """Base class for input-format readers.

    Subclasses must set :attr:`format_name`, optionally set
    :attr:`file_extensions` to enable extension-based auto-detection, and
    implement :meth:`read`.
    """

    #: Short identifier for the input format, e.g. ``"svd"``.
    format_name: str = ""

    #: Lower-case file extensions handled by this reader, including the dot.
    file_extensions: tuple[str, ...] = ()

    @abstractmethod
    def read(self, source: Source) -> Device:
        """Parse ``source`` and return the resulting :class:`~regforge.ir.Device`."""
        raise NotImplementedError
