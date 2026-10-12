"""The HTML wording of one bit of a bit map."""

from __future__ import annotations

from regforge.ir import Bit
from regforge.writers.html.context import LeafHtml
from regforge.writers.html.wording import NO_VALUE


class BitHtml(LeafHtml):
    """Renders one :class:`~regforge.ir.Bit`: which cell it joins, what the cell says, its reset."""

    def copy_of(self, bit: Bit) -> int:
        """Which copy of an array field covers the bit; 0 for a plain field or an unclaimed bit."""
        field = bit.field
        if field is None or field.dim is None:
            return 0
        return (bit.position - field.bit_offset) // field.dim.stride

    def key(self, bit: Bit) -> tuple[int, int] | None:
        """What makes neighbouring bits one cell: the same field, the same copy of it."""
        if bit.field is None:
            return None
        return (id(bit.field), self.copy_of(bit))

    def label(self, bit: Bit) -> str:
        """What the bit's cell says: its field, with the copy for an array; empty if unclaimed."""
        if bit.field is None:
            return ""
        if bit.field.dim is None:
            return bit.field.name
        return f"{bit.field.name}[{self.copy_of(bit)}]"

    def reset(self, bit: Bit) -> str:
        """The bit's reset value, or an en dash when the register does not say."""
        return NO_VALUE if bit.reset is None else str(bit.reset)
