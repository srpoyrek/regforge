"""Reads a ``<writeConstraint>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import WriteConstraint
from regforge.readers.svd.primitives import child_bool, child_int


class WriteConstraintParser:
    """Reads the ``<writeConstraint>`` child of a register or field."""

    def parse(self, element: ET.Element) -> WriteConstraint | None:
        """The constraint ``element`` carries, or ``None`` when it has none."""
        node = element.find("writeConstraint")
        if node is None:
            return None
        return WriteConstraint(
            write_as_read=child_bool(node, "writeAsRead"),
            use_enumerated_values=child_bool(node, "useEnumeratedValues"),
            minimum=child_int(node, "range/minimum"),
            maximum=child_int(node, "range/maximum"),
        )
