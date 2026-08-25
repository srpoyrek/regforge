"""Register-block layout shared across output writers.

Turning a peripheral's registers into an ordered sequence of members and the
reserved gaps between them -- with overlap detection -- is structural, not
language-specific: a C struct, a Rust ``#[repr(C)]`` struct, and a C++ struct all
need the same offsets and the same padding. This module computes that abstract
layout once; each writer maps :class:`LayoutEntry` values to its own type syntax.

Address-unit conversion lives here too, for the same reason: offsets are stored
in the device's address units, and turning them into bytes is a target-model
concern any byte-addressable writer shares (a word-addressable target would
convert differently -- which is exactly why it is a function, not a hardcode).
"""

from __future__ import annotations

from dataclasses import dataclass

from .ir import AddressBlock, Peripheral, Register

#: Bits in one byte. The layout math and every byte-addressable writer share it.
BITS_PER_BYTE = 8


class LayoutError(Exception):
    """Raised when a peripheral's registers cannot form a linear block layout."""


def units_to_bytes(units: int, address_unit_bits: int) -> int:
    """Convert an address-unit count to bytes.

    A no-op for byte-addressable devices (``address_unit_bits == 8``); a
    word-addressable target (e.g. TI C2000 at 16) converts differently, which is
    why callers go through this helper instead of assuming bytes.
    """
    return units * address_unit_bits // BITS_PER_BYTE


@dataclass
class LayoutEntry:
    """One slot in a register block: a register, a reserved gap, or a buffer window.

    A ``buffer`` addressBlock is a range the vendor deliberately left unnamed --
    a FIFO or packet window you stream through rather than a set of registers --
    so it occupies the struct as one raw array instead of named members.

    Attributes:
        offset: Byte offset of the slot from the block base.
        register: The register at this offset, or ``None`` for a gap or window.
        gap_bytes: Size in bytes of a reserved gap or a buffer window (``0`` for
            a register member).
        buffer: Whether the slot is a declared ``buffer`` block rather than padding.
    """

    offset: int
    register: Register | None
    gap_bytes: int = 0
    buffer: bool = False

    @property
    def is_reserved(self) -> bool:
        """Whether this slot is reserved padding rather than a register or a window."""
        return self.register is None and not self.buffer


def struct_block(peripheral: Peripheral) -> AddressBlock | None:
    """The single ``registers`` block that defines the struct's size, or ``None``.

    Only the register windows are considered: a ``buffer`` block is emitted as a
    member and a ``reserved`` block as padding, so neither costs the peripheral
    its size contract. What still yields no contract is a peripheral with no
    block, with several register windows, or whose window does not start at
    offset 0 (handled by later work), and a zero-size window, which would assert
    a struct size of 0.
    """
    blocks = [block for block in peripheral.address_blocks if block.holds_registers]
    if len(blocks) != 1:
        return None
    block = blocks[0]
    if block.offset != 0 or block.size <= 0:
        return None
    return block


def registers_end(peripheral: Peripheral, address_unit_bits: int) -> int:
    """The byte offset just past the peripheral's last register."""
    end = 0
    for register in peripheral.registers:
        offset = units_to_bytes(register.address_offset, address_unit_bits)
        end = max(end, offset + (register.size or 0) // BITS_PER_BYTE)
    return end


def asserted_struct_size(peripheral: Peripheral, address_unit_bits: int) -> int | None:
    """The struct size (bytes) to static-assert from the addressBlock, or ``None``.

    With a clean ``registers`` block (see :func:`struct_block`) that *covers* the
    registers, the size is the block size -- the struct is padded to it, so the
    assert is an equality contract and array stride is correct. If the block is
    *smaller* than the registers (a vendor bug), the honest floor is the natural
    register-derived size (and :mod:`regforge.check` flags the bad block). Without
    a clean block, there is no contract -- ``None``.

    Every other declared block extends the contract too: a ``buffer`` window is a
    member and a ``reserved`` range is padding, so both are inside the struct and
    ``sizeof`` has to reach past them.
    """
    block = struct_block(peripheral)
    if block is None:
        return None
    end = max(
        units_to_bytes(block.size, address_unit_bits),
        registers_end(peripheral, address_unit_bits),
    )
    for other in peripheral.address_blocks:
        end = max(end, units_to_bytes(other.offset + other.size, address_unit_bits))
    return end


def peripheral_layout(
    peripheral: Peripheral, address_unit_bits: int, pad_to_bytes: int | None = None
) -> list[LayoutEntry]:
    """Order a peripheral's registers and buffer windows into slots, by offset.

    Every register's size must already be resolved. A ``buffer`` addressBlock
    takes its place among the registers by offset and occupies the struct as one
    unnamed window. Overlapping slots cannot be represented as a linear block and
    raise :class:`LayoutError` (union / alternateRegister layouts are a later
    feature). When ``pad_to_bytes`` exceeds the last slot's end, a trailing
    reserved gap fills the struct out to that size (so ``sizeof`` matches the
    declared addressBlock).
    """
    slots: list[tuple[int, int, Register | None]] = [
        (
            units_to_bytes(register.address_offset, address_unit_bits),
            (register.size or 0) // BITS_PER_BYTE,
            register,
        )
        for register in peripheral.registers
    ]
    slots += [
        (
            units_to_bytes(block.offset, address_unit_bits),
            units_to_bytes(block.size, address_unit_bits),
            None,
        )
        for block in peripheral.address_blocks
        if block.is_buffer
    ]

    entries: list[LayoutEntry] = []
    cursor = 0
    # Sort on the offset alone: two slots at one offset must not fall through to
    # comparing a Register, which is not orderable.
    for offset, size, register in sorted(slots, key=lambda slot: slot[0]):
        if offset < cursor:
            what = (
                f"{peripheral.name}.{register.name}: register"
                if register is not None
                else f"{peripheral.name}: buffer addressBlock"
            )
            raise LayoutError(
                f"{what} at offset 0x{offset:X} overlaps the preceding member "
                "(overlapping / alternateRegister layouts are not yet supported)"
            )
        if offset > cursor:
            entries.append(LayoutEntry(offset=cursor, register=None, gap_bytes=offset - cursor))
        entries.append(
            LayoutEntry(
                offset=offset,
                register=register,
                gap_bytes=0 if register is not None else size,
                buffer=register is None,
            )
        )
        cursor = offset + size
    if pad_to_bytes is not None and pad_to_bytes > cursor:
        entries.append(LayoutEntry(offset=cursor, register=None, gap_bytes=pad_to_bytes - cursor))
    return entries
