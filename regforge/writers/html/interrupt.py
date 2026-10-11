"""The HTML block of one interrupt."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Interrupt
from regforge.writers.html.context import ElementHtml


class InterruptHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.Interrupt` as a table row."""

    def render(self, interrupt: Interrupt) -> Markup:
        """The interrupt's name, vector number and description."""
        return self._fill(
            "interrupt.html.j2",
            name=interrupt.name,
            vector=interrupt.value,
            description=interrupt.description,
        )
