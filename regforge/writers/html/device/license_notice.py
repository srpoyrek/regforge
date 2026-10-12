"""The HTML block of the licence notice."""

from __future__ import annotations

from markupsafe import Markup

from regforge.writers.html.context import ElementHtml


class LicenseHtml(ElementHtml):
    """Renders the source file's licence text as a collapsed block."""

    def render(self, text: str | None) -> Markup:
        """The notice, or nothing when the file carries none."""
        if not text or not text.strip():
            return Markup("")
        return self._fill("license.html.j2", text=text.strip())
