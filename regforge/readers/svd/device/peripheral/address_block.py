"""Reads an ``<addressBlock>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import AddressBlock
from regforge.readers.svd.device.protection import ProtectionParser
from regforge.readers.svd.element_parser import ParseContext
from regforge.readers.svd.primitives import child_int, child_text


class AddressBlockParser:
    """Reads one ``<addressBlock>`` as a :class:`~regforge.ir.AddressBlock`."""

    def __init__(self, context: ParseContext | None = None) -> None:
        self._protection = ProtectionParser(context)

    def parse(self, element: ET.Element) -> AddressBlock:
        """The block ``element`` describes."""
        return AddressBlock(
            offset=child_int(element, "offset", 0),
            size=child_int(element, "size", 0),
            usage=child_text(element, "usage"),
            protection=self._protection.parse(element),
        )
