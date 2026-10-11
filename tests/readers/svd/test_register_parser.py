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


def test_an_alternate_group_is_kept_as_a_label_and_nothing_is_renamed_or_linked():
    register = RegisterParser(ParseContext()).parse(
        _el(
            "<register><name>CTRL</name><alternateGroup>G</alternateGroup>"
            "<addressOffset>0x0</addressOffset></register>"
        )
    )
    assert (register.name, register.alternate_group) == ("CTRL", "G")


def test_a_register_with_no_alternate_group_has_none():
    register = RegisterParser(ParseContext()).parse(
        _el("<register><name>R</name><addressOffset>0</addressOffset></register>")
    )
    assert register.alternate_group is None


def test_a_register_is_read_as_a_set_of_one_view_that_keeps_what_it_declared():
    alternate_set = RegisterParser(ParseContext()).parse_set(
        _el(
            "<register><name>DR</name><alternateGroup>Raw</alternateGroup>"
            "<alternateRegister>DR</alternateRegister><addressOffset>0x0</addressOffset></register>"
        )
    )
    (view,) = alternate_set.views
    assert (view.name, view.alternate_group, alternate_set.joins) == ("DR", "Raw", "DR")


def test_a_register_that_declares_no_alternate_is_a_set_that_joins_nothing():
    alternate_set = RegisterParser(ParseContext()).parse_set(
        _el("<register><name>R</name><addressOffset>0</addressOffset></register>")
    )
    assert alternate_set.joins is None and not alternate_set.is_alternate


def test_a_derived_from_attribute_is_kept_as_written():
    register = RegisterParser(ParseContext()).parse(
        _el(
            '<register derivedFrom="PORT.PMUX0_%s"><name>PMUX1_%s</name>'
            "<dim>16</dim><dimIncrement>1</dimIncrement>"
            "<addressOffset>0xB0</addressOffset></register>"
        )
    )
    assert register.derived_from == "PORT.PMUX0_%s"
    assert register.name == "PMUX1_%s" and register.fields == []


def test_a_register_without_derived_from_has_none():
    register = RegisterParser(ParseContext()).parse(
        _el("<register><name>R</name><addressOffset>0</addressOffset></register>")
    )
    assert register.derived_from is None
