"""The HTML block of one enumerated value."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import EnumeratedValue
from regforge.writers.html.context import ElementHtml


class EnumValueHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.EnumeratedValue` as a list item."""

    def render(self, value: EnumeratedValue, bit_width: int | None = None) -> Markup:
        """The value's number, name and description.

        A pattern is spelled in binary to ``bit_width``; the catch-all entry reads as
        ``other values``.
        """
        return self._fill(
            "enumerated_value.html.j2",
            number=value.label(bit_width),
            name=value.name,
            description=value.description,
        )
