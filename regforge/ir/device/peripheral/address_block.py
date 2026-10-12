"""A peripheral's declared memory footprint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import Protection

#: The ``usage`` values CMSIS-SVD defines for an ``<addressBlock>``. A block that
#: omits ``usage`` holds registers: SVDConv's ``AddrBlockUsage`` and svd-rs both
#: model an undefined state that defaults to ``registers``, which regforge spells
#: ``None``. Named here so the layout and the writers share one vocabulary.
BLOCK_REGISTERS = "registers"
BLOCK_BUFFER = "buffer"
BLOCK_RESERVED = "reserved"


@dataclass
class AddressBlock:
    """A peripheral's declared memory footprint (SVD ``<addressBlock>``).

    A peripheral may declare several blocks (registers at one offset, a FIFO
    buffer window at another). The block is the vendor's contract for how much
    address space the peripheral occupies, and its ``usage`` decides what the
    C writer emits for it: a ``registers`` block defines the struct and its
    ``sizeof`` static-assert, a ``buffer`` block becomes one raw array member,
    and a ``reserved`` block becomes padding.

    Attributes:
        offset: Start of the block, in address units, relative to the base.
        size: Size of the block, in address units.
        usage: What the block holds -- ``"registers"``, ``"buffer"``, or
            ``"reserved"`` (``None`` when the source omits it).
        protection: The permission an access to the block needs (the block's SVD
            ``<protection>``, from schema 1.3.2); ``None`` when the source omits it. Kept
            as read: no output uses it yet.
    """

    offset: int
    size: int
    usage: str | None = None
    protection: Protection | None = None

    @property
    def holds_registers(self) -> bool:
        """Whether named registers live in this block (absent ``usage`` means yes)."""
        return self.usage in (None, BLOCK_REGISTERS)

    @property
    def is_buffer(self) -> bool:
        """Whether this block is a raw data window the vendor named no registers for."""
        return self.usage == BLOCK_BUFFER
