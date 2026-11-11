"""AlternateSetParser: a register read as the set of one view it starts out as."""

import xml.etree.ElementTree as ET

from regforge.readers.svd.device.peripheral.alternate_set import AlternateSetParser
from regforge.readers.svd.element_parser import ParseContext

PLAIN = """
<register><name>DR</name><addressOffset>0x4</addressOffset><size>32</size></register>
"""
VIEW = """
<register>
  <name>RXD</name><alternateRegister>DR</alternateRegister>
  <addressOffset>0x4</addressOffset><size>32</size>
</register>
"""


def _parse(xml):
    return AlternateSetParser(ParseContext()).parse(ET.fromstring(xml))


def test_a_register_starts_out_as_a_set_of_one_view():
    alternate_set = _parse(PLAIN)
    assert alternate_set.names == ("DR",) and not alternate_set.is_alternate


def test_a_plain_register_joins_nothing():
    assert _parse(PLAIN).joins is None


def test_a_declared_view_keeps_the_target_name_as_written():
    alternate_set = _parse(VIEW)
    assert alternate_set.joins == "DR" and alternate_set.names == ("RXD",)


def test_the_view_is_the_register_the_register_parser_builds():
    (view,) = _parse(VIEW).views
    assert (view.name, view.address_offset, view.size) == ("RXD", 0x4, 32)


def test_an_empty_target_joins_nothing():
    xml = "<register><name>R</name><alternateRegister></alternateRegister></register>"
    assert _parse(xml).joins is None


def test_a_blank_target_joins_nothing():
    xml = "<register><name>R</name><alternateRegister>  </alternateRegister></register>"
    assert _parse(xml).joins is None


def test_a_path_target_is_kept_as_written():
    xml = "<register><name>R</name><alternateRegister>CH.CTRL</alternateRegister></register>"
    assert _parse(xml).joins == "CH.CTRL"
