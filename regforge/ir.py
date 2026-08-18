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
from enum import Enum

# --- SVD schema defaults (used when the source omits an optional element) ---
#: Default bits per address unit (8 => byte-addressable).
DEFAULT_ADDRESS_UNIT_BITS = 8
#: Default data bus width in bits (SVD ``<width>``; also the register-size
#: last resort in the defaults resolution pass).
DEFAULT_BUS_WIDTH = 32


class Access(Enum):
    """Register/field access policy, spelled as in SVD."""

    READ_ONLY = "read-only"
    WRITE_ONLY = "write-only"
    READ_WRITE = "read-write"
    WRITE_ONCE = "writeOnce"
    READ_WRITE_ONCE = "read-writeOnce"


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
        access: Access policy. Raw (possibly ``None``) as parsed; filled in by
            the defaults resolution pass so every field carries a resolved value.
        enums: Enumerated values the field may take, if any.
    """

    name: str
    bit_offset: int
    bit_width: int
    description: str | None = None
    access: Access | None = None
    enums: list[EnumeratedValue] = field(default_factory=list)

    @property
    def mask(self) -> int:
        """The field's bit mask, shifted into position."""
        return ((1 << self.bit_width) - 1) << self.bit_offset


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
    """

    name: str
    address_offset: int
    size: int | None = None
    reset_value: int | None = None
    reset_mask: int | None = None
    description: str | None = None
    access: Access | None = None
    fields: list[Field] = field(default_factory=list)


@dataclass
class Peripheral:
    """A peripheral block mapped at a base address.

    The ``default_*`` fields are register-property defaults declared at the
    peripheral level; the defaults resolution pass hands them down to registers
    that do not declare their own.

    Attributes:
        name: Identifier of the peripheral.
        base_address: Absolute base address of the peripheral.
        description: Optional human-readable description.
        default_size: Peripheral-level default register width in bits.
        default_access: Peripheral-level default access policy.
        default_reset_value: Peripheral-level default reset value.
        default_reset_mask: Peripheral-level default reset mask.
        registers: Registers belonging to the peripheral.
    """

    name: str
    base_address: int
    description: str | None = None
    default_size: int | None = None
    default_access: Access | None = None
    default_reset_value: int | None = None
    default_reset_mask: int | None = None
    registers: list[Register] = field(default_factory=list)


@dataclass
class Cpu:
    """The processor core a device is built around.

    Every field is optional: vendor descriptions routinely omit some, and
    several fields (``nvic_prio_bits``, ``vtor_present``, ``vendor_systick``)
    are specific to Arm Cortex-M cores. A reader for another architecture
    leaves the inapplicable fields ``None``; writers emit only what is present,
    never guessing at absent or suspect values.

    Attributes:
        name: Core identifier, e.g. ``"CM0PLUS"``.
        revision: Core revision, e.g. ``"r0p1"``.
        endian: Byte order, e.g. ``"little"`` or ``"big"``.
        mpu_present: Whether a memory protection unit is present.
        fpu_present: Whether a floating-point unit is present.
        vtor_present: Whether the vector table offset register is present.
        nvic_prio_bits: Implemented interrupt priority bits (Cortex-M).
        vendor_systick: Whether the vendor replaced the standard SysTick.
        num_interrupts: Number of device interrupt lines.
    """

    name: str | None = None
    revision: str | None = None
    endian: str | None = None
    mpu_present: bool | None = None
    fpu_present: bool | None = None
    vtor_present: bool | None = None
    nvic_prio_bits: int | None = None
    vendor_systick: bool | None = None
    num_interrupts: int | None = None


@dataclass
class Device:
    """A complete device and the peripherals it exposes.

    The identity fields (``vendor``, ``name``, ``series``, ``version``) come
    straight from the source description and are preserved so generated output
    can be traced back to the exact input it was produced from.

    Attributes:
        name: Identifier of the device.
        description: Optional human-readable description.
        vendor: Name of the silicon vendor, if given.
        series: Device family or series, if given.
        version: Version string of the source description, if given.
        license_text: License notice carried by the source description, if given.
        cpu: The processor core, if the source describes one.
        address_unit_bits: Bits selected by one address unit (8 for every
            byte-addressable device; the SVD default). All offsets, block sizes,
            and array strides in the IR are stored in these units, unconverted;
            converting to a target's native unit is the emitter's job.
        bus_width: Maximum data bus width in bits (SVD ``<width>``). The last
            fallback for a register's size, and the ceiling a register size is
            checked against.
        default_size: Device-level default register width in bits.
        default_access: Device-level default access policy.
        default_reset_value: Device-level default reset value.
        default_reset_mask: Device-level default reset mask.
        peripherals: Peripherals defined by the device.
    """

    name: str
    description: str | None = None
    vendor: str | None = None
    series: str | None = None
    version: str | None = None
    license_text: str | None = None
    cpu: Cpu | None = None
    address_unit_bits: int = DEFAULT_ADDRESS_UNIT_BITS
    bus_width: int = DEFAULT_BUS_WIDTH
    default_size: int | None = None
    default_access: Access | None = None
    default_reset_value: int | None = None
    default_reset_mask: int | None = None
    peripherals: list[Peripheral] = field(default_factory=list)
