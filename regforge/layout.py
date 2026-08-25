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
    """One slot in a register block: a register member, or a reserved gap.

    Attributes:
        offset: Byte offset of the slot from the block base.
        register: The register at this offset, or ``None`` for a reserved gap.
        gap_bytes: Size of a reserved gap in bytes (``0`` for a register member).
    """

    offset: int
    register: Register | None
    gap_bytes: int = 0

    @property
    def is_reserved(self) -> bool:
        """Whether this slot is a reserved padding gap rather than a register."""
        return self.register is None


def struct_block(peripheral: Peripheral) -> AddressBlock | None:
    """The single ``registers`` block that defines the struct's size, or ``None``.

    Only the clean case yields a size contract: exactly one block, ``registers``
    usage (or unspecified), starting at offset 0. Anything else -- no block,
    several blocks, a ``buffer``/``reserved`` block, or a non-zero offset -- has
    no single struct-size contract and returns ``None`` (handled by later work).
    """
    if len(peripheral.address_blocks) != 1:
        return None
    block = peripheral.address_blocks[0]
    if block.offset != 0 or block.usage not in (None, "registers"):
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
    """
    block = struct_block(peripheral)
    if block is None:
        return None
    block_bytes = units_to_bytes(block.size, address_unit_bits)
    return max(block_bytes, registers_end(peripheral, address_unit_bits))


def peripheral_layout(
    peripheral: Peripheral, address_unit_bits: int, pad_to_bytes: int | None = None
) -> list[LayoutEntry]:
    """Order a peripheral's registers into members + reserved gaps, by offset.

    Every register's size must already be resolved. Overlapping registers cannot
    be represented as a linear block and raise :class:`LayoutError` (union /
    alternateRegister layouts are a later feature). When ``pad_to_bytes`` exceeds
    the last register's end, a trailing reserved gap fills the struct out to that
    size (so ``sizeof`` matches the declared addressBlock).
    """
    entries: list[LayoutEntry] = []
    cursor = 0
    for register in sorted(peripheral.registers, key=lambda r: r.address_offset):
        offset = units_to_bytes(register.address_offset, address_unit_bits)
        if offset < cursor:
            raise LayoutError(
                f"{peripheral.name}.{register.name}: register at offset 0x{offset:X} "
                "overlaps the preceding register (overlapping / alternateRegister "
                "layouts are not yet supported)"
            )
        if offset > cursor:
            entries.append(LayoutEntry(offset=cursor, register=None, gap_bytes=offset - cursor))
        entries.append(LayoutEntry(offset=offset, register=register))
        cursor = offset + (register.size or 0) // BITS_PER_BYTE
    if pad_to_bytes is not None and pad_to_bytes > cursor:
        entries.append(LayoutEntry(offset=cursor, register=None, gap_bytes=pad_to_bytes - cursor))
    return entries
