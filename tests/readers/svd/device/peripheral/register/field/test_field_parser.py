"""FieldParser: reads a <field> element."""

import xml.etree.ElementTree as ET

import pytest

from regforge.ir import (
    Access,
    ModifiedWriteValues,
    ReadAction,
)
from regforge.readers.svd.device.peripheral.register.field.field import FieldParser
from regforge.readers.svd.element_parser import ParseContext


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


@pytest.mark.parametrize(
    "bits",
    [
        "<bitRange>[7:4]</bitRange>",
        "<bitOffset>4</bitOffset><bitWidth>4</bitWidth>",
        "<lsb>4</lsb><msb>7</msb>",
    ],
)
def test_a_field_reads_all_three_bit_range_encodings(bits):
    field = FieldParser(ParseContext()).parse(_el(f"<field><name>F</name>{bits}</field>"))
    assert (field.bit_offset, field.bit_width) == (4, 4)


def test_a_field_without_a_bit_range_is_refused():
    with pytest.raises(ValueError, match="no recognizable bit-range"):
        FieldParser(ParseContext()).parse(_el("<field><name>F</name></field>"))


def test_a_field_reads_everything_it_owns():
    field = FieldParser(ParseContext()).parse(
        _el(
            "<field><name>MODE</name><description>Pin mode</description>"
            "<bitOffset>0</bitOffset><bitWidth>2</bitWidth><access>read-only</access>"
            "<modifiedWriteValues>oneToClear</modifiedWriteValues><readAction>clear</readAction>"
            "<writeConstraint><writeAsRead>true</writeAsRead></writeConstraint>"
            "<enumeratedValues><enumeratedValue><name>A</name><value>0</value>"
            "</enumeratedValue></enumeratedValues></field>"
        )
    )
    assert (field.name, field.description, field.access) == ("MODE", "Pin mode", Access.READ_ONLY)
    assert field.modified_write_values is ModifiedWriteValues.ONE_TO_CLEAR
    assert field.read_action is ReadAction.CLEAR
    assert field.write_constraint is not None and field.write_constraint.write_as_read
    assert [e.name for e in field.enums] == ["A"]
