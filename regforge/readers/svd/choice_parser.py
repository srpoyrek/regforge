"""A parser for one child element that names a member of a closed vocabulary."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Generic

from regforge.readers.svd.element_parser import ParseContext
from regforge.readers.svd.primitives import E, child_choice, child_text


class ChoiceParser(Generic[E]):
    """Reads a child element as a member of the enum ``kind``.

    A subclass names the enum and the tag. The schema's spelling is read as it is. A spelling
    that differs from it only in case (``read-writeonce`` for ``read-writeOnce``) is read as
    the member it names, and any other spelling is ignored; both are noted in the warnings of
    the context, when there is one, so no value is dropped silently. An absent child is read
    as ``None``.
    """

    kind: type[E]
    tag: str

    def __init__(self, context: ParseContext | None = None) -> None:
        self.context = context

    def parse(self, element: ET.Element) -> E | None:
        """The vocabulary member ``element`` holds under :attr:`tag`, or ``None``."""
        text = child_text(element, self.tag)
        if text is None:
            return None
        member = child_choice(element, self.tag, self.kind)
        if member is not None:
            return member
        same = [candidate for candidate in self.kind if candidate.value.lower() == text.lower()]
        if len(same) == 1:
            self._note(element, f"<{self.tag}>{text}</{self.tag}> read as {same[0].value}")
            return same[0]
        self._note(element, f"<{self.tag}>{text}</{self.tag}> is not a CMSIS-SVD value -- ignored")
        return None

    def _note(self, element: ET.Element, message: str) -> None:
        """Record ``message`` against the element's name, when there is a context to hold it."""
        if self.context is not None:
            name = child_text(element, "name") or element.tag
            self.context.warnings.append(f"{name}: {message}")
