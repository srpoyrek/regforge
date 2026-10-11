"""DeviceParser: reads the root <device> element."""

import xml.etree.ElementTree as ET

from regforge.ir import (
    Protection,
)
from regforge.readers.svd.device import DeviceParser
from regforge.readers.svd.element_parser import ParseContext


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_a_device_with_nothing_says_nothing_and_takes_the_schema_defaults():
    device = DeviceParser(ParseContext()).parse(_el("<device><name>D</name></device>"))
    assert (device.name, device.address_unit_bits, device.bus_width) == ("D", 8, 32)
    assert device.cpu is None and device.peripherals == []


def test_a_device_reads_its_identity_defaults_and_peripherals():
    device = DeviceParser(ParseContext()).parse(
        _el(
            "<device><name>D</name><vendor>V</vendor><series>S</series><version>1.0</version>"
            "<headerDefinitionsPrefix>D_</headerDefinitionsPrefix>"
            "<addressUnitBits>8</addressUnitBits><width>64</width><protection>n</protection>"
            "<vendorExtensions><x/></vendorExtensions><cpu><name>CM0</name></cpu>"
            "<peripherals><peripheral><name>P</name><baseAddress>0x0</baseAddress></peripheral>"
            "</peripherals></device>"
        )
    )
    assert (device.vendor, device.series, device.version) == ("V", "S", "1.0")
    assert (device.header_prefix, device.bus_width) == ("D_", 64)
    assert device.default_protection is Protection.NON_SECURE
    assert device.vendor_extensions_xml is not None and "<x" in device.vendor_extensions_xml
    assert device.cpu is not None and device.cpu.name == "CM0"
    assert [p.name for p in device.peripherals] == ["P"]
