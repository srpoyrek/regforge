"""The HTML wording of a protection."""

from __future__ import annotations

from regforge.ir import Protection
from regforge.writers.html.context import LeafHtml


class ProtectionHtml(LeafHtml):
    """Renders a :class:`~regforge.ir.Protection` as what it requires of an access."""

    _TEXT = {
        Protection.SECURE: "secure access only",
        Protection.NON_SECURE: "non-secure or secure access",
        Protection.PRIVILEGED: "privileged access only",
    }

    def text(self, protection: Protection) -> str:
        """What the protection setting requires of an access."""
        return self._TEXT[protection]
