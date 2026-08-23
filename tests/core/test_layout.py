"""Shared, language-neutral register-block layout: offsets, gaps, overlap."""

import pytest

from regforge.ir import Peripheral, Register
from regforge.layout import LayoutError, peripheral_layout, units_to_bytes


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
