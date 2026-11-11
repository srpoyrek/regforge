"""Reads a ``<register>`` as the alternate set of one view it starts out as."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import AlternateSet
from regforge.readers.svd.device.peripheral.register.register import RegisterParser
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.primitives import child_text


class AlternateSetParser(ElementParser):
    """Reads one ``<register>`` as the :class:`~regforge.ir.AlternateSet` holding it."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._register = RegisterParser(context)

    def parse(self, element: ET.Element) -> AlternateSet:
        """The set of one view, carrying ``<alternateRegister>`` as written in ``joins``."""
        return AlternateSet((self._register.parse(element),), joins=self.joins(element))

    def joins(self, element: ET.Element) -> str | None:
        """The register this one declares itself another view of, or ``None``."""
        return child_text(element, "alternateRegister") or None
