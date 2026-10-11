"""A parser for one child element that names a member of a closed vocabulary."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Generic

from regforge.readers.svd.primitives import E, child_choice


class ChoiceParser(Generic[E]):
    """Reads a child element as a member of the enum ``kind``.

    A subclass names the enum and the tag. A spelling the schema does not list, or an
    absent child, is read as ``None``.
    """

    kind: type[E]
    tag: str

    def parse(self, element: ET.Element) -> E | None:
        """The vocabulary member ``element`` holds under :attr:`tag`, or ``None``."""
        return child_choice(element, self.tag, self.kind)
