"""An enumerated value: a name for one number a field's bits can hold.

A :class:`~regforge.ir.Field` is a group of bits; an enumerated value says what one
of the numbers those bits can hold means. It names the field's value as a whole,
never a single bit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnumeratedValue:
    """A named constant that a :class:`Field` may hold.

    The SVD gives an entry either a ``<value>`` or ``<isDefault>``, never both. A plain
    entry names one number, or a run of numbers when the source writes some bits as ``x``
    (``#01xx``); the catch-all entry names whatever the others do not, and has no number.

    Attributes:
        name: Identifier of the value, e.g. ``"OUTPUT"``.
        value: The number the entry names, with any don't-care bits read as 0; ``None`` for
            a catch-all entry, which names no single number.
        description: Optional human-readable description.
        is_default: Whether this is the catch-all entry (SVD ``isDefault``): it names
            every number the other entries do not.
        dont_care: The bits the source wrote as ``x``, which may be either value; 0 for a
            plain number.
    """

    name: str
    value: int | None
    description: str | None = None
    is_default: bool = False
    dont_care: int = 0

    @property
    def is_pattern(self) -> bool:
        """Whether the entry names a run of numbers, because some bits are don't-care."""
        return self.dont_care != 0

    def matches(self, number: int) -> bool:
        """Whether this entry names ``number``.

        A catch-all entry never matches by itself: it is what is left over, see
        :meth:`~regforge.ir.EnumSet.entry_for`.
        """
        if self.value is None:
            return False
        return (number & ~self.dont_care) == self.value

    def fits_in(self, bit_width: int) -> bool:
        """Whether the number, or the widest of the pattern, fits in ``bit_width`` bits."""
        if self.value is None:
            return True
        return 0 <= self.value and (self.value | self.dont_care) < (1 << bit_width)

    def label(self, bit_width: int | None = None) -> str:
        """The entry's number as text: hex, binary with ``x`` for a pattern, or ``other values``.

        ``bit_width`` pads a pattern to the field's width; without it the pattern is as wide
        as its highest bit.
        """
        if self.value is None:
            return "other values"
        if not self.dont_care:
            return f"{self.value:#x}"
        width = max(bit_width or 0, (self.value | self.dont_care).bit_length())
        digits = "".join(
            "x" if (self.dont_care >> bit) & 1 else str((self.value >> bit) & 1)
            for bit in reversed(range(width))
        )
        return f"0b{digits}"
