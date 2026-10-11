"""Reads an ``<enumeratedValue>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import EnumeratedValue
from regforge.readers.svd.primitives import child_bool, child_text, parse_svd_value


class EnumeratedValueParser:
    """Reads one ``<enumeratedValue>``."""

    def parse(self, element: ET.Element) -> EnumeratedValue | None:
        """The entry, or ``None`` when it has neither a ``<value>`` nor ``<isDefault>``.

        The schema gives an entry one or the other. A ``<value>`` may write some bits as
        ``x``; a catch-all ``<isDefault>`` entry has no number and is kept as such.
        """
        name = child_text(element, "name") or ""
        description = child_text(element, "description")
        is_default = child_bool(element, "isDefault") or False
        number = child_text(element, "value")
        if number is None:
            if not is_default:
                return None
            return EnumeratedValue(name, None, description, is_default=True)
        value, dont_care = parse_svd_value(number)
        return EnumeratedValue(name, value, description, is_default, dont_care)

    def parse_all(
        self, parent: ET.Element, path: str, numbered_only: bool = False
    ) -> list[EnumeratedValue]:
        """Every entry found at ``path`` under ``parent``, skipping those with nothing to name.

        ``numbered_only`` also drops the catch-all entries, for a list that is only a set of
        names for numbers, such as an array's index names.
        """
        parsed = (self.parse(element) for element in parent.findall(path))
        entries = [entry for entry in parsed if entry is not None]
        return [e for e in entries if e.value is not None] if numbered_only else entries
