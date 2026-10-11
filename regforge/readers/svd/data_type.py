"""Reads the ``dataType`` child of an element."""

from __future__ import annotations

from regforge.ir import DataType
from regforge.readers.svd.choice_parser import ChoiceParser


class DataTypeParser(ChoiceParser[DataType]):
    """Reads ``<dataType>`` as a :class:`~regforge.ir.DataType`."""

    kind = DataType
    tag = "dataType"
