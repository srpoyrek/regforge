"""A device: the root of the register map, and the peripherals it exposes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import Access, Cpu, Peripheral, Protection

# --- SVD schema defaults (used when the source omits an optional element) ---
#: Default bits per address unit (8 => byte-addressable).
DEFAULT_ADDRESS_UNIT_BITS = 8
#: Default data bus width in bits (SVD ``<width>``; also the register-size
#: last resort in the defaults resolution pass).
DEFAULT_BUS_WIDTH = 32


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
        header_prefix: Vendor prefix for generated identifiers (SVD
            ``headerDefinitionsPrefix``); emitters prepend it to define names.
        vendor_extensions_xml: The raw ``<vendorExtensions>`` subtree, preserved
            verbatim as an opaque string for future interpreters. Never dropped.
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
        default_protection: Device-level default protection.
    """

    name: str
    description: str | None = None
    vendor: str | None = None
    series: str | None = None
    version: str | None = None
    license_text: str | None = None
    header_prefix: str | None = None
    vendor_extensions_xml: str | None = None
    cpu: Cpu | None = None
    address_unit_bits: int = DEFAULT_ADDRESS_UNIT_BITS
    bus_width: int = DEFAULT_BUS_WIDTH
    default_size: int | None = None
    default_access: Access | None = None
    default_reset_value: int | None = None
    default_reset_mask: int | None = None
    peripherals: list[Peripheral] = field(default_factory=list)
    default_protection: Protection | None = None
