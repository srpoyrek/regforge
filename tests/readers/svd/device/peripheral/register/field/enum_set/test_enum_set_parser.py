"""EnumSetParser: reads an <enumeratedValues> element."""

import xml.etree.ElementTree as ET

from regforge.ir import (
    EnumUsage,
)
from regforge.readers.svd.device.peripheral.register.field.enum_set.enum_set import EnumSetParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_an_enum_set_reads_its_settings_and_values():
    enum_set = EnumSetParser().parse(
        _el(
            "<enumeratedValues derivedFrom='BASE'><name>N</name>"
            "<headerEnumName>H</headerEnumName><usage>read</usage>"
            "<enumeratedValue><name>A</name><value>0</value></enumeratedValue>"
            "</enumeratedValues>"
        )
    )
    assert (enum_set.name, enum_set.header_enum_name) == ("N", "H")
    assert (enum_set.usage, enum_set.derived_from) == (EnumUsage.READ, "BASE")
    assert [v.name for v in enum_set.values] == ["A"]
