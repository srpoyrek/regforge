"""Reads an ``<enumeratedValues>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import EnumSet
from regforge.readers.svd.element_parser import ParseContext
from regforge.readers.svd.enum_usage import EnumUsageParser
from regforge.readers.svd.enumerated_value import EnumeratedValueParser
from regforge.readers.svd.primitives import child_text


class EnumSetParser:
    """Reads one ``<enumeratedValues>`` block as an :class:`~regforge.ir.EnumSet`."""

    def __init__(self, context: ParseContext | None = None) -> None:
        self._value = EnumeratedValueParser()
        self._usage = EnumUsageParser(context)

    def parse(self, element: ET.Element) -> EnumSet:
        """The set ``element`` describes: its values and its own settings."""
        return EnumSet(
            values=self._value.parse_all(element, "enumeratedValue"),
            name=child_text(element, "name"),
            header_enum_name=child_text(element, "headerEnumName"),
            usage=self._usage.parse(element),
            derived_from=element.get("derivedFrom"),
        )
