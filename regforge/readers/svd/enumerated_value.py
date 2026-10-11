"""Reads an ``<enumeratedValue>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import EnumeratedValue
from regforge.readers.svd.primitives import child_bool, child_text, parse_svd_int


class EnumeratedValueParser:
    """Reads one ``<enumeratedValue>``."""

    def parse(self, element: ET.Element) -> EnumeratedValue | None:
        """The value, or ``None`` when it has no ``<value>`` child, as there is nothing to name."""
        number = child_text(element, "value")
        if number is None:
            return None
        return EnumeratedValue(
            name=child_text(element, "name") or "",
            value=parse_svd_int(number),
            description=child_text(element, "description"),
            is_default=child_bool(element, "isDefault") or False,
        )

    def parse_all(self, parent: ET.Element, path: str) -> list[EnumeratedValue]:
        """Every value found at ``path`` under ``parent``, skipping those with no number."""
        parsed = (self.parse(element) for element in parent.findall(path))
        return [value for value in parsed if value is not None]
