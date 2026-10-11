"""A field: a named group of adjacent bits inside a register.

A field is recorded only as a position (``bit_offset``, ``bit_width``) over the
bits its :class:`~regforge.ir.Register` already has; see :mod:`regforge.ir.bit` for
the view that makes those bits explicit. Its enumerated values name the number the
grouped bits hold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import Access, Dim, EnumeratedValue, EnumSet


@dataclass
class Field:
    """A contiguous group of bits within a :class:`Register`.

    Attributes:
        name: Identifier of the field.
        bit_offset: Zero-based index of the field's least-significant bit.
        bit_width: Number of bits the field occupies.
        description: Optional human-readable description.
        access: Access policy. Raw (possibly ``None``) as parsed; filled in by
            the defaults resolution pass so every field carries a resolved value.
        enum_sets: The field's enumerated sets, if any: one set, or a read set and
            a write set. :attr:`enums` is their values flattened.
        dim: Array shape when the field is one of several copies (SVD
            ``<dim>``, increment in bits); ``None`` for a single field. After
            expansion only a ``[%s]`` array keeps it, with ``name`` bare.
        expanded_from: The ``<dim>`` template this element was expanded from
            (``UART%s``), so a report can point at the one declaration behind
            several copies; ``None`` when written out by hand.
    """

    name: str
    bit_offset: int
    bit_width: int
    description: str | None = None
    access: Access | None = None
    enum_sets: list[EnumSet] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None

    @property
    def mask(self) -> int:
        """The field's bit mask, shifted into position."""
        return ((1 << self.bit_width) - 1) << self.bit_offset

    @property
    def enums(self) -> list[EnumeratedValue]:
        """The values of every enumerated set, in order, as one flat list.

        What the writers read until they act on the sets themselves.
        """
        return [value for enum_set in self.enum_sets for value in enum_set.values]

    @property
    def max_value(self) -> int:
        """The largest number the field's bits can hold."""
        return (1 << self.bit_width) - 1

    @property
    def positions(self) -> range:
        """The register bit positions the field covers, least-significant first.

        Like :attr:`mask`, this is the field's first copy when it is an array.
        """
        return range(self.bit_offset, self.bit_offset + self.bit_width)

    def extract(self, word: int) -> int:
        """The number the field's bits hold in ``word``."""
        return (word & self.mask) >> self.bit_offset

    def insert(self, word: int, value: int) -> int:
        """``word`` with the field's bits replaced by ``value``.

        Raises ``ValueError`` when ``value`` does not fit in the field's width.
        """
        if not 0 <= value <= self.max_value:
            raise ValueError(f"{self.name}: {value} does not fit in {self.bit_width} bit(s)")
        return (word & ~self.mask) | (value << self.bit_offset)
