"""SVD structural parsing: peripherals, registers, fields, enums, literals."""

import pytest

from regforge.ir import EnumUsage
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


def _field_with_enums(tmp_path, enum_xml):
    svd = tmp_path / "enums.svd"
    svd.write_text(
        "<device><name>X</name><peripherals><peripheral><name>P</name>"
        "<baseAddress>0x0</baseAddress><registers><register><name>R</name>"
        "<addressOffset>0x0</addressOffset><fields><field><name>F</name>"
        "<bitOffset>0</bitOffset><bitWidth>2</bitWidth>" + enum_xml + "</field>"
        "</fields></register></registers></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    return SvdReader().read(svd).peripherals[0].registers[0].fields[0]


def test_each_enumerated_values_block_becomes_a_set(tmp_path):
    # A field may carry a read set and a write set; each keeps its own settings.
    field = _field_with_enums(
        tmp_path,
        "<enumeratedValues><name>F_READ</name><headerEnumName>FRead</headerEnumName>"
        "<usage>read</usage>"
        "<enumeratedValue><name>OFF</name><value>0</value></enumeratedValue>"
        "<enumeratedValue><name>ON</name><value>1</value></enumeratedValue>"
        "</enumeratedValues>"
        "<enumeratedValues derivedFrom='F_READ'><usage>write</usage></enumeratedValues>",
    )
    read, write = field.enum_sets
    assert (read.name, read.header_enum_name, read.usage) == ("F_READ", "FRead", EnumUsage.READ)
    assert [v.name for v in read.values] == ["OFF", "ON"]
    assert (write.usage, write.derived_from, write.values) == (EnumUsage.WRITE, "F_READ", [])
    assert [e.name for e in field.enums] == ["OFF", "ON"]  # the flat view across both sets


def test_enumerated_values_usage_defaults_to_read_write(tmp_path):
    absent = _field_with_enums(tmp_path, "<enumeratedValues></enumeratedValues>")
    unknown = _field_with_enums(
        tmp_path, "<enumeratedValues><usage>sideways</usage></enumeratedValues>"
    )
    assert absent.enum_sets[0].usage is EnumUsage.READ_WRITE
    assert unknown.enum_sets[0].usage is EnumUsage.READ_WRITE


def test_an_enumerated_value_with_no_number_is_skipped(tmp_path):
    field = _field_with_enums(
        tmp_path,
        "<enumeratedValues>"
        "<enumeratedValue><name>NAMED_ONLY</name></enumeratedValue>"
        "<enumeratedValue><name>OK</name><value>1</value></enumeratedValue>"
        "</enumeratedValues>",
    )
    assert [e.name for e in field.enums] == ["OK"]


def test_catch_all_and_dont_care_entries_read_instead_of_stopping_the_read(tmp_path):
    field = _field_with_enums(
        tmp_path,
        "<enumeratedValues>"
        "<enumeratedValue><name>BUSY</name><value>#01xx</value></enumeratedValue>"
        "<enumeratedValue><name>others</name><isDefault>true</isDefault></enumeratedValue>"
        "</enumeratedValues>",
    )
    busy, others = field.enum_sets[0].values
    assert (busy.value, busy.dont_care) == (4, 3)
    assert others.value is None and others.is_default
