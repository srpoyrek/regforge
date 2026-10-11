"""A register: N bits at one address, and the fields that name slices of them.

A register is the addressable word of the hardware map. ``size`` is how many bits it
has; its :class:`~regforge.ir.Field` objects are named groups of those bits. See
:mod:`regforge.ir.bit` for the view that makes the bits themselves explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from regforge.ir.access import Access
from regforge.ir.bit import bits as _bits

if TYPE_CHECKING:
    from regforge.ir import (
        DataType,
        Dim,
        Field,
        ModifiedWriteValues,
        Protection,
        ReadAction,
        WriteConstraint,
    )
    from regforge.ir.bit import Bit
    from regforge.ir.dim_origin import DimOrigin


@dataclass
class Register:
    """A single addressable register within a :class:`Peripheral`.

    The ``size``, ``reset_value``, ``reset_mask``, and ``access`` fields hold
    the register's own declared value (``None`` when the source is silent).
    The defaults resolution pass then fills them from the inheritance chain, so
    every emitter sees fully-resolved values and never re-derives them.

    Attributes:
        name: Identifier of the register.
        address_offset: Offset from the owning peripheral's base, in address units.
        size: Width of the register in bits (resolved).
        reset_value: Value the register holds after reset (resolved; may be
            ``None`` if unspecified at every level).
        reset_mask: Which bits of ``reset_value`` are defined (resolved).
        description: Optional human-readable description.
        access: Access policy (resolved).
        fields: Bit fields defined within the register.
        dim: Array shape when the register is one of several copies (SVD
            ``<dim>``); ``None`` for a single register. After expansion only a
            ``[%s]`` array keeps it, and ``name`` is then the bare array name.
            Its stride is compared to the resolved ``size`` only after defaults
            resolution, in the checks and the layout, never here.
        expanded_from: The ``<dim>`` template this element was expanded from
            (``UART%s``), so a report can point at the one declaration behind
            several copies; ``None`` when written out by hand.
        alternate_register: The register this one is another view of, as
            declared (SVD ``<alternateRegister>``; an ``<alternateGroup>`` is
            read as the same thing, the view renamed ``NAME_GROUP``).
        alternates: Every name in this register's alternate set, the primary
            first, once ``resolve_alternates`` has linked them; empty for a
            register that is the only view of its word.
        display_name: SVD ``displayName`` -- a human-readable name, when the vendor
            gives one.
        data_type: The C type the register is meant to be accessed as (SVD
            ``dataType``).
        protection: Security level an access needs (SVD ``protection``). Raw as
            parsed.
        modified_write_values: What a write does to the bits written, if anything.
        read_action: The side effect of a read, if any.
        write_constraint: The values the register accepts when written, if constrained.
        origin: The array declaration this element was unrolled from, with its count,
            step and labels; ``None`` for an element written out by hand or kept whole.
    """

    name: str
    address_offset: int
    size: int | None = None
    reset_value: int | None = None
    reset_mask: int | None = None
    description: str | None = None
    access: Access | None = None
    fields: list[Field] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None
    alternate_register: str | None = None
    alternates: tuple[str, ...] = ()
    display_name: str | None = None
    data_type: DataType | None = None
    protection: Protection | None = None
    modified_write_values: ModifiedWriteValues | None = None
    read_action: ReadAction | None = None
    write_constraint: WriteConstraint | None = None
    origin: DimOrigin | None = None

    def _width(self) -> int:
        """The register's size in bits; ``ValueError`` while it is still unresolved."""
        if self.size is None:
            raise ValueError(f"{self.name}: size is unresolved")
        return self.size

    def bits(self) -> list[Bit]:
        """Every bit of the register, least-significant first (see :mod:`regforge.ir.bit`)."""
        return _bits(self)

    @property
    def full_mask(self) -> int:
        """All of the register's bits set."""
        return (1 << self._width()) - 1

    def size_in_units(self, address_unit_bits: int) -> int:
        """The register's width in address units (bytes when a unit is 8 bits)."""
        return self._width() // address_unit_bits

    def end_offset(self, address_unit_bits: int) -> int:
        """The offset of the first address unit past the register."""
        return self.address_offset + self.size_in_units(address_unit_bits)

    def field_named(self, name: str) -> Field | None:
        """The field called ``name``, or ``None`` if the register has none."""
        return next((f for f in self.fields if f.name == name), None)

    def field_at(self, position: int) -> Field | None:
        """The field covering bit ``position``, or ``None`` if no field names it.

        ``IndexError`` when ``position`` is not a bit of this register.
        """
        if not 0 <= position < self._width():
            raise IndexError(f"{self.name}: bit {position} is outside the register")
        return self.bits()[position].field

    def unclaimed_positions(self) -> list[int]:
        """The bit positions no field names, least-significant first."""
        return [bit.position for bit in self.bits() if bit.field is None]

    @property
    def is_readable(self) -> bool:
        """Whether software may read it; an unresolved access counts as read-write."""
        return (self.access or Access.READ_WRITE).can_read

    @property
    def is_writable(self) -> bool:
        """Whether software may write it; an unresolved access counts as read-write."""
        return (self.access or Access.READ_WRITE).can_write

    @property
    def has_read_side_effect(self) -> bool:
        """Whether reading the register does something besides return its value."""
        return self.read_action is not None

    @property
    def is_safe_to_read(self) -> bool:
        """Whether the register may be read for inspection, as a debug dump would."""
        return self.is_readable and not self.has_read_side_effect

    @property
    def needs_direct_write(self) -> bool:
        """Whether a read-modify-write of the register is wrong (write-one-to-clear and kin)."""
        return self.modified_write_values is not None and self.modified_write_values.acts_per_bit

    @property
    def is_write_once(self) -> bool:
        """Whether it may be written only once after reset; unresolved counts as read-write."""
        return (self.access or Access.READ_WRITE).is_write_once
