"""The HTML block of a list of labelled facts."""

from __future__ import annotations

from markupsafe import Markup

from regforge.writers.html.context import ElementHtml


class FactsHtml(ElementHtml):
    """Renders ``(label, value)`` pairs as a two-column table."""

    def render(self, title: str, pairs: list[tuple[str, str]]) -> Markup:
        """The table, or nothing when there are no facts."""
        if not pairs:
            return Markup("")
        return self._fill("facts.html.j2", title=title, pairs=pairs)
