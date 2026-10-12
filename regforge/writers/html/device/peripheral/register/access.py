"""The HTML wording of an access."""

from __future__ import annotations

from regforge.ir import Access
from regforge.writers.html.context import LeafHtml
from regforge.writers.html.wording import NO_VALUE


class AccessHtml(LeafHtml):
    """Renders an :class:`~regforge.ir.Access`: the label the tables show, and a write-once note."""

    _LABEL = {
        Access.READ_ONLY: "RO",
        Access.WRITE_ONLY: "WO",
        Access.READ_WRITE: "RW",
        Access.WRITE_ONCE: "WO (once)",
        Access.READ_WRITE_ONCE: "RW (write once)",
    }

    def label(self, access: Access | None) -> str:
        """``RO``, ``WO``, ``RW`` and so on; an en dash when unresolved."""
        return NO_VALUE if access is None else self._LABEL[access]

    def note(self, access: Access | None) -> str | None:
        """What a write-once access means for the reader; ``None`` for any other."""
        if (access or Access.READ_WRITE).is_write_once:
            return "can be written only once after reset"
        return None
