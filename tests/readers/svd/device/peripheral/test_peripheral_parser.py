"""PeripheralParser: reads a <peripheral> element."""

import xml.etree.ElementTree as ET

from regforge.ir import (
    Access,
    Protection,
)
from regforge.readers.svd.device.peripheral.peripheral import PeripheralParser
from regforge.readers.svd.element_parser import ParseContext


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_a_peripheral_reads_its_children_from_the_right_places():
    peripheral = PeripheralParser(ParseContext()).parse(
        _el(
            "<peripheral derivedFrom='UART0'><name>UART1</name>"
            "<baseAddress>0x40005000</baseAddress><groupName>UART</groupName>"
            "<size>32</size><access>read-write</access><protection>s</protection>"
            "<addressBlock><offset>0</offset><size>0x20</size><usage>registers</usage>"
            "</addressBlock><interrupt><name>U1</name><value>21</value></interrupt>"
            "<registers><register><name>DR</name><addressOffset>0x4</addressOffset></register>"
            "<cluster><name>CH</name><addressOffset>0x10</addressOffset></cluster>"
            "</registers></peripheral>"
        )
    )
    assert (peripheral.name, peripheral.base_address) == ("UART1", 0x40005000)
    assert (peripheral.derived_from, peripheral.group_name) == ("UART0", "UART")
    assert peripheral.default_size == 32 and peripheral.default_access is Access.READ_WRITE
    assert peripheral.default_protection is Protection.SECURE
    assert [b.size for b in peripheral.address_blocks] == [0x20]
    assert [i.value for i in peripheral.interrupts] == [21]
    assert [r.name for r in peripheral.registers] == ["DR"]
    assert [c.name for c in peripheral.clusters] == ["CH"]
