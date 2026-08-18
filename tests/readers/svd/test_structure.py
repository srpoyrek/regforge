"""SVD structural parsing: peripherals, registers, fields, enums, literals."""

import pytest

from regforge.readers.svd import parse_svd_int


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0x40020000", 0x40020000),
        ("0b1010", 0b1010),
        ("#1010", 0b1010),
        ("42", 42),
    ],
)
def test_parse_svd_int(text, expected):
    assert parse_svd_int(text) == expected


def test_peripherals_registers_fields(demo_device):
    assert [p.name for p in demo_device.peripherals] == ["GPIOA"]

    gpioa = demo_device.peripherals[0]
    assert gpioa.base_address == 0x40020000
    assert [r.name for r in gpioa.registers] == ["MODER", "ODR"]

    moder = gpioa.registers[0]
    assert moder.address_offset == 0x00
    field = moder.fields[0]
    assert field.name == "MODE0"
    assert (field.bit_offset, field.bit_width) == (0, 2)
    assert [e.name for e in field.enums] == ["INPUT", "OUTPUT", "ALTERNATE", "ANALOG"]


def test_bit_range_encoding(demo_device):
    # ODR.OD0 uses the "[0:0]" bitRange encoding.
    od0 = demo_device.peripherals[0].registers[1].fields[0]
    assert (od0.bit_offset, od0.bit_width) == (0, 1)
