"""Shared, language-neutral register-block layout: offsets, gaps, overlap."""

import pytest

from regforge.ir import AddressBlock, Peripheral, Register
from regforge.layout import (
    LayoutError,
    asserted_struct_size,
    peripheral_layout,
    struct_block,
    units_to_bytes,
)


def test_orders_registers_and_inserts_reserved_gaps():
    # R0 @ 0x0 (4 bytes), then a gap, then R1 @ 0x10.
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[
            Register("R1", address_offset=0x10, size=32),
            Register("R0", address_offset=0x0, size=32),  # declared out of order
        ],
    )
    slots = peripheral_layout(peripheral, address_unit_bits=8)
    assert [
        (s.offset, s.gap_bytes, None if s.register is None else s.register.name) for s in slots
    ] == [
        (0x0, 0, "R0"),
        (0x4, 12, None),  # reserved gap 0x4..0x10
        (0x10, 0, "R1"),
    ]
    assert slots[1].is_reserved and not slots[0].is_reserved


def test_contiguous_registers_have_no_gap():
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("A", 0x0, size=32), Register("B", 0x4, size=32)],
    )
    slots = peripheral_layout(peripheral, address_unit_bits=8)
    assert [s.register.name for s in slots] == ["A", "B"]  # no reserved slot between


def test_overlapping_registers_raise_layout_error():
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("A", 0x0, size=32), Register("B", 0x2, size=32)],  # B overlaps A
    )
    with pytest.raises(LayoutError, match="overlaps"):
        peripheral_layout(peripheral, address_unit_bits=8)


def test_offsets_convert_from_address_units():
    # Word-addressable (16 bits/unit): unit 0x2 -> byte 0x4.
    peripheral = Peripheral(name="P", base_address=0x0, registers=[Register("A", 0x2, size=16)])
    slots = peripheral_layout(peripheral, address_unit_bits=16)
    register_slot = next(s for s in slots if not s.is_reserved)
    assert register_slot.offset == units_to_bytes(0x2, 16) == 0x4


def test_struct_block_accepts_only_a_clean_registers_block():
    def periph(*blocks):
        return Peripheral(name="P", base_address=0x0, address_blocks=list(blocks))

    assert struct_block(periph(AddressBlock(0, 0x20, "registers"))) is not None
    assert struct_block(periph(AddressBlock(0, 0x20, None))) is not None  # usage omitted
    assert struct_block(periph(AddressBlock(0, 0x20, "buffer"))) is None  # window, not registers
    assert struct_block(periph(AddressBlock(0x10, 0x20, "registers"))) is None  # non-zero offset
    assert struct_block(periph(AddressBlock(0, 0x20), AddressBlock(0x800, 0x10))) is None  # multi
    assert struct_block(periph()) is None  # no block
    assert struct_block(periph(AddressBlock(0, 0, "registers"))) is None  # zero-size window


def test_struct_block_looks_past_buffer_and_reserved_blocks():
    # One register window plus a buffer and a reserved range: those two are
    # emitted (member / padding), so the peripheral keeps its size contract.
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        address_blocks=[
            AddressBlock(0x0, 0x20, "registers"),
            AddressBlock(0x20, 0x40, "buffer"),
            AddressBlock(0x60, 0x10, "reserved"),
        ],
    )
    block = struct_block(peripheral)
    assert block is not None and block.usage == "registers"
    # The contract reaches past every declared block: 0x60 + 0x10.
    assert asserted_struct_size(peripheral, address_unit_bits=8) == 0x70


def test_buffer_block_becomes_a_window_slot_ordered_by_offset():
    # CR @ 0x0 (4 bytes), gap to 0x10, then a 0x20-byte buffer window.
    peripheral = Peripheral(
        name="DMA",
        base_address=0x0,
        registers=[Register("CR", 0x0, size=32)],
        address_blocks=[
            AddressBlock(0x0, 0x20, "registers"),
            AddressBlock(0x10, 0x20, "buffer"),
        ],
    )
    size = asserted_struct_size(peripheral, address_unit_bits=8)
    assert size == 0x30
    slots = peripheral_layout(peripheral, address_unit_bits=8, pad_to_bytes=size)
    assert [(s.offset, s.gap_bytes, s.buffer, s.is_reserved) for s in slots] == [
        (0x00, 0, False, False),  # CR
        (0x04, 12, False, True),  # reserved gap
        (0x10, 32, True, False),  # buffer window
    ]


def test_buffer_window_overlapping_a_register_is_an_error():
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("R", 0x0, size=32)],
        address_blocks=[AddressBlock(0x2, 0x10, "buffer")],  # starts inside R
    )
    with pytest.raises(LayoutError, match="buffer addressBlock"):
        peripheral_layout(peripheral, address_unit_bits=8)


def test_reserved_block_is_padding_not_a_member():
    # A reserved range contributes no slot of its own; it only extends the pad.
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("R", 0x0, size=32)],
        address_blocks=[
            AddressBlock(0x0, 0x4, "registers"),
            AddressBlock(0x4, 0xC, "reserved"),
        ],
    )
    size = asserted_struct_size(peripheral, address_unit_bits=8)
    assert size == 0x10
    slots = peripheral_layout(peripheral, address_unit_bits=8, pad_to_bytes=size)
    assert [(s.offset, s.gap_bytes, s.buffer) for s in slots] == [
        (0x0, 0, False),  # R
        (0x4, 12, False),  # trailing pad over the reserved range
    ]


def test_asserted_size_covers_floors_or_none():
    regs = [Register("A", 0x0, size=32), Register("B", 0x14, size=32)]  # end at 0x18
    covering = Peripheral(
        name="P",
        base_address=0,
        registers=regs,
        address_blocks=[AddressBlock(0, 0x20, "registers")],
    )
    assert asserted_struct_size(covering, 8) == 0x20  # block covers -> block size
    small = Peripheral(
        name="P",
        base_address=0,
        registers=regs,
        address_blocks=[AddressBlock(0, 0x10, "registers")],
    )
    assert asserted_struct_size(small, 8) == 0x18  # block below registers -> floor at reg end
    assert asserted_struct_size(Peripheral(name="P", base_address=0, registers=regs), 8) is None


def test_peripheral_layout_pads_to_bytes():
    peripheral = Peripheral(name="P", base_address=0, registers=[Register("A", 0x0, size=32)])
    slots = peripheral_layout(peripheral, 8, pad_to_bytes=0x10)
    assert slots[-1].is_reserved  # trailing pad 0x4..0x10
    assert (slots[-1].offset, slots[-1].gap_bytes) == (0x4, 0xC)
    # pad target at or below the natural end adds nothing.
    assert not peripheral_layout(peripheral, 8, pad_to_bytes=0x4)[-1].is_reserved
