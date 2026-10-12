"""Reads the ``readAction`` child of an element."""

from __future__ import annotations

from regforge.ir import ReadAction
from regforge.readers.svd.choice_parser import ChoiceParser


class ReadActionParser(ChoiceParser[ReadAction]):
    """Reads ``<readAction>`` as a :class:`~regforge.ir.ReadAction`."""

    kind = ReadAction
    tag = "readAction"
