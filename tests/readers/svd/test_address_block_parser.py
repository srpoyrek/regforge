"""AddressBlockParser: reads an <addressBlock> element."""

import xml.etree.ElementTree as ET

from regforge.ir import Protection
from regforge.readers.svd.address_block import AddressBlockParser
from regforge.readers.svd.element_parser import ParseContext


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_an_address_block_reads_offset_size_and_usage():
    block = AddressBlockParser().parse(
        _el("<b><offset>0x10</offset><size>0x20</size><usage>buffer</usage></b>")
    )
    assert (block.offset, block.size, block.usage) == (0x10, 0x20, "buffer")
    empty = AddressBlockParser().parse(_el("<b/>"))
    assert (empty.offset, empty.size, empty.usage) == (0, 0, None)


def test_an_address_block_reads_its_protection():
    block = AddressBlockParser().parse(
        _el("<b><offset>0</offset><size>4</size><protection>s</protection></b>")
    )
    assert block.protection is Protection.SECURE


def test_a_block_that_says_nothing_about_protection_has_none():
    assert AddressBlockParser().parse(_el("<b><offset>0</offset></b>")).protection is None


def test_a_protection_the_schema_does_not_list_is_read_as_absent():
    block = AddressBlockParser().parse(_el("<b><protection>x</protection></b>"))
    assert block.protection is None


def test_a_protection_the_schema_does_not_list_is_noted_when_there_is_a_context():
    context = ParseContext()
    AddressBlockParser(context).parse(_el("<b><protection>x</protection></b>"))
    assert context.warnings == ["b: <protection>x</protection> is not a CMSIS-SVD value -- ignored"]
