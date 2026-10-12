"""Reads an ``<interrupt>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import Interrupt
from regforge.readers.svd.primitives import child_int, child_text


class InterruptParser:
    """Reads one ``<interrupt>`` as a :class:`~regforge.ir.Interrupt`."""

    def parse(self, element: ET.Element) -> Interrupt:
        """The interrupt ``element`` describes."""
        return Interrupt(
            name=child_text(element, "name") or "",
            value=child_int(element, "value", 0),
            description=child_text(element, "description"),
        )
