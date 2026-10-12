"""The HTML wording of what a read does."""

from __future__ import annotations

from regforge.ir import ReadAction
from regforge.writers.html.context import LeafHtml


class ReadActionHtml(LeafHtml):
    """Renders a :class:`~regforge.ir.ReadAction` as the note a reader needs."""

    _TEXT = {
        ReadAction.CLEAR: "a read clears it",
        ReadAction.SET: "a read sets it",
        ReadAction.MODIFY: "a read modifies it",
        ReadAction.MODIFY_EXTERNAL: "a read changes it from outside, as a FIFO pop does",
    }

    def note(self, action: ReadAction | None) -> str | None:
        """What a read does, with the warning not to read it for a look; ``None`` if nothing."""
        if action is None:
            return None
        return self._TEXT[action] + "; do not read it just to look"
