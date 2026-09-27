"""SVD structural parsing: peripherals, registers, fields, enums, literals."""

import pytest

from regforge.readers.svd import SvdReader, parse_svd_int


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
    assert [p.name for p in demo_device.peripherals] == [
        "GPIOA",
        "UART0",
        "UART1",
        "SPI0",
        "SPI1",
        "TIM1",
        "TIM2",
        "TIM3",
        "ADC0",
        "ADC1",
        "WDT0",
        "WDT1",
        "CRC",
        "PWMA",
        "PWMB",
        "DMA",
    ]

    gpioa = demo_device.peripherals[0]
    assert gpioa.base_address == 0x40020000
    assert [r.name for r in gpioa.registers] == ["MODER", "IDR", "ODR"]

    moder = gpioa.registers[0]
    assert moder.address_offset == 0x00
    field = moder.fields[0]
    assert field.name == "MODE0"
    assert (field.bit_offset, field.bit_width) == (0, 2)
    assert [e.name for e in field.enums] == ["INPUT", "OUTPUT", "ALTERNATE", "ANALOG"]


def test_bit_range_encoding(demo_device):
    # ODR.OD (an array field) uses the "[0:0]" bitRange encoding for element 0.
    odr = next(r for r in demo_device.peripherals[0].registers if r.name == "ODR")
    od0 = odr.fields[0]
    assert (od0.bit_offset, od0.bit_width) == (0, 1)


def test_field_without_bit_spec_raises(tmp_path):
    # A field with no bitOffset/bitWidth, bitRange, or lsb/msb is malformed.
    svd = tmp_path / "badfield.svd"
    svd.write_text(
        "<device><name>X</name><peripherals><peripheral><name>P</name>"
        "<baseAddress>0x0</baseAddress><registers><register><name>R</name>"
        "<addressOffset>0x0</addressOffset><fields><field><name>F</name></field>"
        "</fields></register></registers></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no recognizable bit-range"):
        SvdReader().read(svd)


def test_derived_from_attribute_is_captured(tmp_path):
    svd = tmp_path / "derived.svd"
    svd.write_text(
        "<device><name>X</name><peripherals>"
        "<peripheral><name>UART0</name><baseAddress>0x40004000</baseAddress></peripheral>"
        "<peripheral derivedFrom='UART0'><name>UART1</name>"
        "<baseAddress>0x40005000</baseAddress></peripheral>"
        "</peripherals></device>",
        encoding="utf-8",
    )
    device = SvdReader().read(svd)
    assert device.peripherals[0].derived_from is None  # base declares nothing
    assert device.peripherals[1].derived_from == "UART0"  # derived backlink captured


def test_interrupts_are_captured(tmp_path):
    # A peripheral may raise several interrupts, each with its own name/value.
    svd = tmp_path / "irq.svd"
    svd.write_text(
        "<device><name>X</name><peripherals><peripheral><name>DMA</name>"
        "<baseAddress>0x40020000</baseAddress>"
        "<interrupt><name>DMA_CH0</name><description>Channel 0</description>"
        "<value>10</value></interrupt>"
        "<interrupt><name>DMA_ERR</name><value>11</value></interrupt>"
        "</peripheral></peripherals></device>",
        encoding="utf-8",
    )
    device = SvdReader().read(svd)
    interrupts = device.peripherals[0].interrupts
    assert [(i.name, i.value) for i in interrupts] == [("DMA_CH0", 10), ("DMA_ERR", 11)]
    assert interrupts[0].description == "Channel 0"


def test_address_block_is_captured(tmp_path):
    svd = tmp_path / "block.svd"
    svd.write_text(
        "<device><name>X</name><peripherals><peripheral><name>P</name>"
        "<baseAddress>0x0</baseAddress>"
        "<addressBlock><offset>0</offset><size>0x100</size><usage>registers</usage></addressBlock>"
        "</peripheral></peripherals></device>",
        encoding="utf-8",
    )
    device = SvdReader().read(svd)
    blocks = device.peripherals[0].address_blocks
    assert len(blocks) == 1
    assert (blocks[0].offset, blocks[0].size, blocks[0].usage) == (0, 0x100, "registers")
