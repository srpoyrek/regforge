"""Tests for the intermediate representation."""

from regforge.ir import Field


def test_field_mask_is_positioned():
    assert Field("A", bit_offset=0, bit_width=2).mask == 0x3
    assert Field("B", bit_offset=2, bit_width=2).mask == 0xC
    assert Field("C", bit_offset=8, bit_width=8).mask == 0xFF00


def test_field_full_width_mask():
    assert Field("D", bit_offset=0, bit_width=32).mask == 0xFFFFFFFF
