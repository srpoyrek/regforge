"""EnumUsageParser: the direction an enumerated set describes."""

import xml.etree.ElementTree as ET

from regforge.ir import (
    EnumUsage,
)
from regforge.readers.svd.device.peripheral.register.field.enum_set.enum_usage import (
    EnumUsageParser,
)


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_enum_usage_defaults_to_read_write():
    parser = EnumUsageParser()
    assert parser.parse(_el("<x><usage>write</usage></x>")) is EnumUsage.WRITE
    assert parser.parse(_el("<x/>")) is EnumUsage.READ_WRITE
    assert parser.parse(_el("<x><usage>sideways</usage></x>")) is EnumUsage.READ_WRITE
