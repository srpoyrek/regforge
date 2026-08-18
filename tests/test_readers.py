"""Tests for the reader registry and the SVD reader."""

import pytest

from regforge.readers import available_readers, get_reader, reader_for_path
from regforge.readers.svd import SvdReader, parse_svd_int


def test_svd_reader_is_registered():
    assert "svd" in available_readers()
    assert isinstance(get_reader("svd"), SvdReader)


def test_reader_inferred_from_extension(minimal_svd_path):
    assert isinstance(reader_for_path(minimal_svd_path), SvdReader)


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        get_reader("does-not-exist")


def test_unknown_extension_raises():
    with pytest.raises(ValueError):
        reader_for_path("device.unknown")


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


def test_reads_expected_ir(demo_device):
    assert demo_device.name == "DemoMCU"
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
