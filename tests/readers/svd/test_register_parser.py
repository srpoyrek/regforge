"""RegisterParser: reads a <register> element."""

import xml.etree.ElementTree as ET

from regforge.ir import (
    Access,
    DataType,
    Protection,
)
from regforge.readers.svd.element_parser import ParseContext
from regforge.readers.svd.register import RegisterParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_a_register_reads_its_properties_and_its_fields_in_order():
    register = RegisterParser(ParseContext()).parse(
        _el(
            "<register><name>MODER</name><addressOffset>0x4</addressOffset><size>32</size>"
            "<resetValue>0x0</resetValue><resetMask>0xFFFFFFFF</resetMask>"
            "<description>Mode</description><access>read-write</access>"
            "<displayName>Mode register</displayName><dataType>uint32_t</dataType>"
            "<protection>s</protection><fields>"
            "<field><name>A</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth></field>"
            "<field><name>B</name><bitRange>[3:2]</bitRange></field></fields></register>"
        )
    )
    assert (register.name, register.address_offset, register.size) == ("MODER", 4, 32)
    assert (register.reset_value, register.reset_mask) == (0, 0xFFFFFFFF)
    assert register.access is Access.READ_WRITE
    assert register.display_name == "Mode register"
    assert register.data_type is DataType.UINT32 and register.protection is Protection.SECURE
    assert [f.name for f in register.fields] == ["A", "B"]
    assert (register.fields[1].bit_offset, register.fields[1].bit_width) == (2, 2)


def test_an_alternate_group_is_spelled_name_group_and_linked_to_the_plain_name():
    register = RegisterParser(ParseContext()).parse(
        _el(
            "<register><name>CTRL</name><alternateGroup>G</alternateGroup>"
            "<addressOffset>0x0</addressOffset></register>"
        )
    )
    assert (register.name, register.alternate_register) == ("CTRL_G", "CTRL")
