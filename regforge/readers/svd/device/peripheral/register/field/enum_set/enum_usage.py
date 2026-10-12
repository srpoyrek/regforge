"""Reads the ``usage`` child of an ``<enumeratedValues>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import EnumUsage
from regforge.readers.svd.choice_parser import ChoiceParser


class EnumUsageParser(ChoiceParser[EnumUsage]):
    """Reads ``<usage>`` as a :class:`~regforge.ir.EnumUsage`."""

    kind = EnumUsage
    tag = "usage"

    def parse(self, element: ET.Element) -> EnumUsage:
        """The usage, ``READ_WRITE`` when it is absent or unrecognized, as the schema defaults."""
        return super().parse(element) or EnumUsage.READ_WRITE
