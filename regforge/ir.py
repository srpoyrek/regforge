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

# --- SVD schema defaults (used when the source omits an optional element) ---
#: Default register width in bits.
DEFAULT_REGISTER_SIZE_BITS = 32
#: Default bits per address unit (8 => byte-addressable).
DEFAULT_ADDRESS_UNIT_BITS = 8


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
    size: int = DEFAULT_REGISTER_SIZE_BITS
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
    peripherals: list[Peripheral] = field(default_factory=list)
