"""Reads the ``protection`` child of an element."""

from __future__ import annotations

from regforge.ir import Protection
from regforge.readers.svd.choice_parser import ChoiceParser


class ProtectionParser(ChoiceParser[Protection]):
    """Reads ``<protection>`` as a :class:`~regforge.ir.Protection`."""

    kind = Protection
    tag = "protection"
