"""The HTML block of one enumerated set."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import EnumSet
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.enumerated_value import EnumValueHtml


class EnumSetHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.EnumSet` as a list of its values."""

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._value = EnumValueHtml(context)

    def render(
        self, enum_set: EnumSet, label: str | None = None, bit_width: int | None = None
    ) -> Markup:
        """The set's values; ``label`` names the direction when a field has several sets.

        ``bit_width`` is the field's width, so a pattern is spelled to that many bits.
        """
        return self._fill(
            "enum_set.html.j2",
            label=label,
            values=[self._value.render(v, bit_width) for v in enum_set.values],
        )
