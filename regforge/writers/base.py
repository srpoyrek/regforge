"""Writer interface.

A writer renders a :class:`~regforge.ir.Device` into source text for a target
language. Concrete writers subclass :class:`Writer`, declare the target they
produce, and are registered with the writer registry in
:mod:`regforge.writers`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..ir import Device
from ..provenance import Provenance


class EmitError(RuntimeError):
    """Raised when a writer cannot faithfully emit the given device.

    Signals a deliberate, named refusal (for example, a target that only
    supports byte-addressable devices being handed a word-addressable one) so
    the pipeline fails loudly instead of generating subtly wrong output.
    """


class Writer(ABC):
    """Base class for output-target writers.

    Subclasses must set :attr:`target_name` and implement :meth:`render`.
    :attr:`file_extension` enables extension-based target detection, and
    :attr:`language` names the source language for optional post-processing
    (for example, uncrustify formatting of C-family output).
    """

    #: Short identifier for the output target, e.g. ``"c"``.
    target_name: str = ""

    #: Conventional output file extension, including the dot, e.g. ``".h"``.
    file_extension: str = ""

    #: Source language identifier for post-processors. Empty if not applicable.
    language: str = ""

    @abstractmethod
    def render(self, device: Device, provenance: Provenance | None = None) -> str:
        """Render ``device`` and return the generated source as a string.

        If ``provenance`` is given, writers embed it into the output as an
        audit trail (banner lines and compile-time constants).
        """
        raise NotImplementedError
