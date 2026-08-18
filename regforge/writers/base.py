"""Writer interface.

A writer renders a :class:`~regforge.ir.Device` into source text for a target
language. Concrete writers subclass :class:`Writer`, declare the target they
produce, and are registered with the writer registry in
:mod:`regforge.writers`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..ir import Device


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
    def render(self, device: Device) -> str:
        """Render ``device`` and return the generated source as a string."""
        raise NotImplementedError
