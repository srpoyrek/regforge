"""ReadActionParser: reads the ``readAction`` child of an element."""

import xml.etree.ElementTree as ET

from regforge.ir import ReadAction
from regforge.readers.svd.device.peripheral.register.read_action import ReadActionParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_it_reads_the_tag_it_names():
    element = _el("<x><readAction>modifyExternal</readAction></x>")
    assert ReadActionParser().parse(element) is ReadAction.MODIFY_EXTERNAL


def test_it_reads_every_member_by_its_spelling():
    for member in ReadAction:
        element = _el(f"<x><readAction>{member.value}</readAction></x>")
        assert ReadActionParser().parse(element) is member


def test_a_missing_child_is_read_as_absent():
    assert ReadActionParser().parse(_el("<x/>")) is None


def test_a_spelling_the_schema_does_not_list_is_read_as_absent():
    assert ReadActionParser().parse(_el("<x><readAction>bogus</readAction></x>")) is None
