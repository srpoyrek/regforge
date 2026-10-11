"""A field: a named group of adjacent bits inside a register.

A field is recorded only as a position (``bit_offset``, ``bit_width``) over the
bits its :class:`~regforge.ir.Register` already has; see :mod:`regforge.ir.bit` for
the view that makes those bits explicit. Its enumerated values name the number the
grouped bits hold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from regforge.ir.access import Access
from regforge.ir.enum_usage import EnumUsage

if TYPE_CHECKING:
    from regforge.ir import (
        Dim,
        EnumeratedValue,
        EnumSet,
        ModifiedWriteValues,
        ReadAction,
        WriteConstraint,
    )
    from regforge.ir.dim_origin import DimOrigin


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
        modified_write_values: What a write does to the bits written, if anything.
        read_action: The side effect of reading the field, if any.
        write_constraint: The values the field accepts when written, if constrained.
        origin: The array declaration this element was unrolled from, with its count,
            step and labels; ``None`` for an element written out by hand or kept whole.
    """

    name: str
    bit_offset: int
    bit_width: int
    description: str | None = None
    access: Access | None = None
    enum_sets: list[EnumSet] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None
    modified_write_values: ModifiedWriteValues | None = None
    read_action: ReadAction | None = None
    write_constraint: WriteConstraint | None = None
    origin: DimOrigin | None = None

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

    @property
    def is_readable(self) -> bool:
        """Whether software may read it; an unresolved access counts as read-write."""
        return (self.access or Access.READ_WRITE).can_read

    @property
    def is_writable(self) -> bool:
        """Whether software may write it; an unresolved access counts as read-write."""
        return (self.access or Access.READ_WRITE).can_write

    # --- geometry ---------------------------------------------------------------

    @property
    def lsb(self) -> int:
        """The least-significant bit the field covers."""
        return self.bit_offset

    @property
    def msb(self) -> int:
        """The most-significant bit the field covers (its first copy, for an array)."""
        return self.bit_offset + self.bit_width - 1

    @property
    def bit_range(self) -> str:
        """The range spelled as SVD's ``bitRange``, ``[msb:lsb]``."""
        return f"[{self.msb}:{self.lsb}]"

    @property
    def is_single_bit(self) -> bool:
        """Whether the field is one bit wide, a flag."""
        return self.bit_width == 1

    def overlaps(self, other: Field) -> bool:
        """Whether the two fields share a bit (their first copies, for an array)."""
        return (
            self.bit_offset < other.bit_offset + other.bit_width
            and other.bit_offset < self.bit_offset + self.bit_width
        )

    def runs(self) -> list[tuple[int, int]]:
        """The runs of bits the field covers, as ``(first, last)``, one run per copy of an array.

        A field with no ``dim`` is one run. A copy may reach past a register's width;
        whoever knows the width decides what to do about that.
        """
        if self.dim is None:
            starts = [self.bit_offset]
        else:
            starts = [
                self.bit_offset + element * self.dim.stride for element in range(self.dim.length)
            ]
        return [(start, start + self.bit_width - 1) for start in starts]

    def fits_in(self, register_size: int) -> bool:
        """Whether every copy of the field lies within a register ``register_size`` bits wide."""
        end = self.bit_offset + self.bit_width
        if self.dim is not None:
            end += (self.dim.length - 1) * self.dim.stride
        return end <= register_size

    # --- side effects -----------------------------------------------------------

    @property
    def has_read_side_effect(self) -> bool:
        """Whether reading the field does something besides return its value."""
        return self.read_action is not None

    @property
    def is_safe_to_read(self) -> bool:
        """Whether the field may be read for inspection, as a debug dump would.

        A write-only field cannot be read, and a field with a read action changes
        when read: reading a receive FIFO's data field pops the FIFO.
        """
        return self.is_readable and not self.has_read_side_effect

    @property
    def needs_direct_write(self) -> bool:
        """Whether a read-modify-write of the field is wrong.

        True for a field whose written bits each act on themselves (write-one-to-clear
        and its kin): writing back what was read disturbs bits that were not meant to
        change, so the field must be written directly.
        """
        return self.modified_write_values is not None and self.modified_write_values.acts_per_bit

    def accepts(self, value: int) -> bool:
        """Whether ``value`` is a legal thing to write to the field.

        It must fit the field's width, the field must be writable, and the value must
        satisfy the write constraint: inside its range, and a name in the write
        enumeration when the constraint says to use enumerated values. A
        ``write_as_read`` constraint depends on what was read, so it is not decided here.
        """
        if not self.is_writable or not 0 <= value <= self.max_value:
            return False
        constraint = self.write_constraint
        if constraint is None:
            return True
        if not constraint.in_range(value):
            return False
        if constraint.use_enumerated_values:
            enum_set = self.enum_set_for(EnumUsage.WRITE)
            return (
                enum_set is not None
                and enum_set.entry_for(value, include_default=False) is not None
            )
        return True

    # --- enumerated values ------------------------------------------------------

    def enum_set_for(self, usage: EnumUsage) -> EnumSet | None:
        """The enumerated set that applies in direction ``usage``, or ``None``.

        A set written for exactly that direction wins; otherwise the read-write set
        serves both directions.
        """
        exact = next((s for s in self.enum_sets if s.usage is usage), None)
        if exact is not None:
            return exact
        return next((s for s in self.enum_sets if s.usage is EnumUsage.READ_WRITE), None)

    def enum_name(self, number: int, usage: EnumUsage = EnumUsage.READ) -> str | None:
        """What ``number`` means when read from the field, or ``None`` if it is unnamed."""
        enum_set = self.enum_set_for(usage)
        return enum_set.name_of(number) if enum_set is not None else None

    def enum_value(self, name: str, usage: EnumUsage = EnumUsage.WRITE) -> int | None:
        """The number to write for the enumerated ``name``, or ``None`` if there is none."""
        enum_set = self.enum_set_for(usage)
        return enum_set.value_of(name) if enum_set is not None else None

    @property
    def is_write_once(self) -> bool:
        """Whether it may be written only once after reset; unresolved counts as read-write."""
        return (self.access or Access.READ_WRITE).is_write_once
