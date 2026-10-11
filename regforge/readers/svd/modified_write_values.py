"""Reads the ``modifiedWriteValues`` child of an element."""

from __future__ import annotations

from regforge.ir import ModifiedWriteValues
from regforge.readers.svd.choice_parser import ChoiceParser


class ModifiedWriteValuesParser(ChoiceParser[ModifiedWriteValues]):
    """Reads ``<modifiedWriteValues>`` as a :class:`~regforge.ir.ModifiedWriteValues`."""

    kind = ModifiedWriteValues
    tag = "modifiedWriteValues"
