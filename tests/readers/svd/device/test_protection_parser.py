"""ProtectionParser: reads the ``protection`` child of an element."""

import xml.etree.ElementTree as ET

from regforge.ir import Protection
from regforge.readers.svd.device.protection import ProtectionParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_it_reads_the_tag_it_names():
    element = _el("<x><protection>n</protection></x>")
    assert ProtectionParser().parse(element) is Protection.NON_SECURE


def test_it_reads_every_member_by_its_spelling():
    for member in Protection:
        element = _el(f"<x><protection>{member.value}</protection></x>")
        assert ProtectionParser().parse(element) is member


def test_a_missing_child_is_read_as_absent():
    assert ProtectionParser().parse(_el("<x/>")) is None


def test_a_spelling_the_schema_does_not_list_is_read_as_absent():
    assert ProtectionParser().parse(_el("<x><protection>bogus</protection></x>")) is None
