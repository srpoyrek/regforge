"""The HTML wording of what a write does."""

from __future__ import annotations

from regforge.ir import ModifiedWriteValues
from regforge.writers.html.context import LeafHtml


class ModifiedWriteValuesHtml(LeafHtml):
    """Renders a :class:`~regforge.ir.ModifiedWriteValues` as the note a reader needs."""

    _TEXT = {
        ModifiedWriteValues.ONE_TO_CLEAR: "writing 1 clears the bit",
        ModifiedWriteValues.ONE_TO_SET: "writing 1 sets the bit",
        ModifiedWriteValues.ONE_TO_TOGGLE: "writing 1 toggles the bit",
        ModifiedWriteValues.ZERO_TO_CLEAR: "writing 0 clears the bit",
        ModifiedWriteValues.ZERO_TO_SET: "writing 0 sets the bit",
        ModifiedWriteValues.ZERO_TO_TOGGLE: "writing 0 toggles the bit",
        ModifiedWriteValues.CLEAR: "any write clears it",
        ModifiedWriteValues.SET: "any write sets it",
        ModifiedWriteValues.MODIFY: "a write modifies it in a way the hardware decides",
    }

    def note(self, value: ModifiedWriteValues | None) -> str | None:
        """What a write does, with the warning a per-bit behaviour needs; ``None`` if nothing."""
        if value is None:
            return None
        text = self._TEXT[value]
        if value.acts_per_bit:
            text += "; write the bits you mean directly, as a read-modify-write would change others"
        return text
