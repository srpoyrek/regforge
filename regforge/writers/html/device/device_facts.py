"""The numbers of one device that every block of its HTML page is laid out by."""

from __future__ import annotations

from dataclasses import dataclass

from regforge.ir import Device
from regforge.writers.html.device.peripheral.placement import placed_registers
from regforge.writers.html.wording import hex_digits


@dataclass(frozen=True)
class DeviceFacts:
    """What the device says about its own widths, worked out once and passed down the render.

    No block picks a width of its own: the bit map wraps at the bus width, addresses are
    written with as many digits as the bus is wide, and offsets with as many as the
    largest offset of the device needs, so every column of the page lines up.

    Attributes:
        bus_width: Data bus width in bits; a bit map row holds this many bits.
        address_digits: Hex digits of an absolute address.
        offset_digits: Hex digits of an offset or a size inside a peripheral.
    """

    bus_width: int
    address_digits: int
    offset_digits: int

    @classmethod
    def of(cls, device: Device) -> DeviceFacts:
        """The facts of ``device``."""
        largest = 0
        for peripheral in device.peripherals:
            for placed in placed_registers(peripheral):
                largest = max(largest, placed.offset)
            for block in peripheral.address_blocks:
                largest = max(largest, block.offset, block.size)
        return cls(
            bus_width=device.bus_width,
            address_digits=hex_digits(device.bus_width),
            offset_digits=hex_digits(largest.bit_length()),
        )
