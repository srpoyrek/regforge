"""Shared, language-neutral register-block layout: offsets, gaps, overlap."""

import pytest

from regforge.ir import AddressBlock, Cluster, Dim, Peripheral, Register
from regforge.layout import (
    LayoutError,
    asserted_struct_size,
    cluster_element_bytes,
    peripheral_layout,
    registers_end,
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


# --- arrays and clusters ---


def test_array_register_is_one_slot_spanning_every_element():
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("CR", 0x0, size=32), Register("DATA", 0x10, size=32, dim=Dim(8, 4))],
    )
    data = peripheral_layout(peripheral, address_unit_bits=8)[-1]
    assert (data.offset, data.element_bytes, data.size_bytes, data.count) == (0x10, 4, 32, 8)
    assert data.register is not None and data.register.name == "DATA"


def test_overlapping_array_elements_are_refused():
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("DATA", 0x10, size=32, dim=Dim(4, 2, array=True))],
    )
    with pytest.raises(LayoutError, match=r"P\.DATA\[4\]: stride 2 .* elements overlap"):
        peripheral_layout(peripheral, address_unit_bits=8)


def test_unpacked_array_becomes_one_member_per_element_with_padding():
    # Stride 8 for 4-byte elements: no C array can hold the holes, so CH0..CH3
    # each get a member and the holes become padding; the slots stay in offset order.
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("CH", 0x0, size=32, dim=Dim(4, 8, array=True))],
    )
    slots = peripheral_layout(peripheral, address_unit_bits=8)
    assert [(s.offset, s.gap_bytes, s.label) for s in slots] == [
        (0x00, 0, "CH0"),
        (0x04, 4, "reserved"),
        (0x08, 0, "CH1"),
        (0x0C, 4, "reserved"),
        (0x10, 0, "CH2"),
        (0x14, 4, "reserved"),
        (0x18, 0, "CH3"),
    ]
    assert all(s.count == 1 and s.register is peripheral.registers[0] for s in slots if s.register)


def test_word_addressable_stride_is_converted_like_an_offset():
    # 16 bits per unit: an increment of 2 units is 4 bytes, exactly one 32-bit element.
    peripheral = Peripheral(
        name="P",
        base_address=0x0,
        registers=[Register("D", 0x2, size=32, dim=Dim(2, 2, array=True))],
    )
    (slot,) = peripheral_layout(peripheral, address_unit_bits=16)[1:]
    assert (slot.offset, slot.element_bytes, slot.size_bytes, slot.count) == (0x4, 4, 8, 2)


def test_registers_end_reaches_the_last_array_element():
    peripheral = Peripheral(
        name="P", base_address=0x0, registers=[Register("DATA", 0x10, size=32, dim=Dim(8, 8))]
    )
    # Eight 4-byte elements 8 bytes apart: the last one ends at 0x10 + 7*8 + 4.
    assert registers_end(peripheral, address_unit_bits=8) == 0x10 + 7 * 8 + 4


def _dma(cluster: Cluster) -> Peripheral:
    return Peripheral(
        name="DMA", base_address=0x0, registers=[Register("CFG", 0x0, size=32)], clusters=[cluster]
    )


def _kinds(entries):
    return [
        (
            m.offset,
            m.gap_bytes,
            m.register.name if m.register else m.cluster.name if m.cluster else None,
        )
        for m in entries
    ]


def test_cluster_is_one_slot_carrying_its_own_layout():
    cluster = Cluster(
        "CH", 0x10, registers=[Register("CTRL", 0x0, size=32), Register("SRC", 0x8, size=32)]
    )
    slots = peripheral_layout(_dma(cluster), address_unit_bits=8)
    assert _kinds(slots) == [(0x0, 0, "CFG"), (0x4, 12, None), (0x10, 0, "CH")]
    ch = slots[-1]
    assert ch.cluster is cluster and not ch.is_reserved
    assert (ch.element_bytes, ch.size_bytes, ch.count) == (0xC, 0xC, 1)  # SRC ends at 0xC
    assert _kinds(ch.members) == [(0x0, 0, "CTRL"), (0x4, 4, None), (0x8, 0, "SRC")]


def test_array_cluster_element_is_padded_to_the_stride():
    cluster = Cluster(
        "CH",
        0x10,
        dim=Dim(4, 0x10),
        registers=[Register("CTRL", 0x0, size=32), Register("SRC", 0x4, size=32)],
    )
    ch = peripheral_layout(_dma(cluster), address_unit_bits=8)[-1]
    assert (ch.element_bytes, ch.size_bytes, ch.count) == (0x10, 0x40, 4)
    assert ch.members[-1].is_reserved
    assert (ch.members[-1].offset, ch.members[-1].gap_bytes) == (0x8, 0x8)  # pad to the stride
    assert cluster_element_bytes(cluster, 8) == 0x10


def test_array_cluster_stride_smaller_than_its_contents_is_an_error():
    cluster = Cluster(
        "CH",
        0x10,
        dim=Dim(4, 0x4),
        registers=[Register("CTRL", 0x0, size=32), Register("SRC", 0x4, size=32)],
    )
    with pytest.raises(LayoutError, match=r"DMA\.CH\[4\]: stride 0x4 is smaller"):
        peripheral_layout(_dma(cluster), address_unit_bits=8)


def test_empty_cluster_cannot_be_laid_out():
    with pytest.raises(LayoutError, match="no registers"):
        peripheral_layout(_dma(Cluster("CH", 0x10)), address_unit_bits=8)


def test_nested_cluster_and_array_register_inside_a_cluster():
    inner = Cluster("SUB", 0x8, registers=[Register("R", 0x0, size=16)])
    cluster = Cluster(
        "CH",
        0x10,
        dim=Dim(2, 0x10),
        registers=[Register("D", 0x0, size=32, dim=Dim(2, 4))],
        clusters=[inner],
    )
    ch = peripheral_layout(_dma(cluster), address_unit_bits=8)[-1]
    # D[2] fills 0x0..0x8, SUB sits at 0x8..0xA, then padding to the 0x10 stride.
    assert _kinds(ch.members) == [(0x0, 0, "D"), (0x8, 0, "SUB"), (0xA, 6, None)]
    assert ch.members[1].members[0].register.name == "R"


def test_cluster_overlapping_a_register_is_an_error():
    cluster = Cluster("CH", 0x2, registers=[Register("CTRL", 0x0, size=32)])
    with pytest.raises(LayoutError, match=r"DMA\.CH: cluster at offset 0x2 overlaps"):
        peripheral_layout(_dma(cluster), address_unit_bits=8)


def test_registers_end_covers_a_cluster_array():
    cluster = Cluster("CH", 0x10, dim=Dim(4, 0x10), registers=[Register("CTRL", 0x0, size=32)])
    assert registers_end(_dma(cluster), address_unit_bits=8) == 0x10 + 3 * 0x10 + 4
