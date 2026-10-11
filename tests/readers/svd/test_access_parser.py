"""AccessParser: reads the ``access`` child of an element."""

import xml.etree.ElementTree as ET

from regforge.ir import Access
from regforge.readers.svd.access import AccessParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_it_reads_the_tag_it_names():
    element = _el("<x><access>read-writeOnce</access></x>")
    assert AccessParser().parse(element) is Access.READ_WRITE_ONCE


def test_it_reads_every_member_by_its_spelling():
    for member in Access:
        element = _el(f"<x><access>{member.value}</access></x>")
        assert AccessParser().parse(element) is member


def test_a_missing_child_is_read_as_absent():
    assert AccessParser().parse(_el("<x/>")) is None


def test_a_spelling_the_schema_does_not_list_is_read_as_absent():
    assert AccessParser().parse(_el("<x><access>bogus</access></x>")) is None
