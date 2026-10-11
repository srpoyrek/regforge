"""AddressBlockParser: reads an <addressBlock> element."""

import xml.etree.ElementTree as ET

from regforge.readers.svd.address_block import AddressBlockParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_an_address_block_reads_offset_size_and_usage():
    block = AddressBlockParser().parse(
        _el("<b><offset>0x10</offset><size>0x20</size><usage>buffer</usage></b>")
    )
    assert (block.offset, block.size, block.usage) == (0x10, 0x20, "buffer")
    empty = AddressBlockParser().parse(_el("<b/>"))
    assert (empty.offset, empty.size, empty.usage) == (0, 0, None)
