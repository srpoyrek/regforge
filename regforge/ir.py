"""Intermediate representation of a device register map.

The intermediate representation (IR) is the format-independent data model at
the centre of regforge. Input readers parse a source description into these
dataclasses, and output writers render them into a target language. Neither
side depends on the other: adding an input format or an output language only
touches its own package.

The hierarchy mirrors the structure of a memory-mapped device:

``Device`` -> ``Peripheral`` -> ``Register`` -> ``Field`` -> ``EnumeratedValue``
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnumeratedValue:
    """A named constant that a :class:`Field` may hold.

    Attributes:
        name: Identifier of the value, e.g. ``"OUTPUT"``.
        value: The numeric value written to the field.
        description: Optional human-readable description.
    """

    name: str
    value: int
    description: str | None = None


@dataclass
class Field:
    """A contiguous group of bits within a :class:`Register`.

    Attributes:
        name: Identifier of the field.
        bit_offset: Zero-based index of the field's least-significant bit.
        bit_width: Number of bits the field occupies.
        description: Optional human-readable description.
        access: Access policy such as ``"read-write"`` or ``"read-only"``.
        enums: Enumerated values the field may take, if any.
    """

    name: str
    bit_offset: int
    bit_width: int
    description: str | None = None
    access: str | None = None
    enums: list[EnumeratedValue] = field(default_factory=list)

    @property
    def mask(self) -> int:
        """The field's bit mask, shifted into position."""
        return ((1 << self.bit_width) - 1) << self.bit_offset


@dataclass
class Register:
    """A single addressable register within a :class:`Peripheral`.

    Attributes:
        name: Identifier of the register.
        address_offset: Byte offset from the owning peripheral's base address.
        size: Width of the register in bits.
        reset_value: Value the register holds after reset.
        description: Optional human-readable description.
        access: Access policy such as ``"read-write"`` or ``"read-only"``.
        fields: Bit fields defined within the register.
    """

    name: str
    address_offset: int
    size: int = 32
    reset_value: int = 0
    description: str | None = None
    access: str | None = None
    fields: list[Field] = field(default_factory=list)


@dataclass
class Peripheral:
    """A peripheral block mapped at a base address.

    Attributes:
        name: Identifier of the peripheral.
        base_address: Absolute base address of the peripheral.
        description: Optional human-readable description.
        registers: Registers belonging to the peripheral.
    """

    name: str
    base_address: int
    description: str | None = None
    registers: list[Register] = field(default_factory=list)


@dataclass
class Device:
    """A complete device and the peripherals it exposes.

    Attributes:
        name: Identifier of the device.
        description: Optional human-readable description.
        peripherals: Peripherals defined by the device.
    """

    name: str
    description: str | None = None
    peripherals: list[Peripheral] = field(default_factory=list)
