"""DataTypeParser: reads the ``dataType`` child of an element."""

import xml.etree.ElementTree as ET

from regforge.ir import DataType
from regforge.readers.svd.data_type import DataTypeParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_it_reads_the_tag_it_names():
    element = _el("<x><dataType>int16_t *</dataType></x>")
    assert DataTypeParser().parse(element) is DataType.INT16_PTR


def test_it_reads_every_member_by_its_spelling():
    for member in DataType:
        element = _el(f"<x><dataType>{member.value}</dataType></x>")
        assert DataTypeParser().parse(element) is member


def test_a_missing_child_is_read_as_absent():
    assert DataTypeParser().parse(_el("<x/>")) is None


def test_a_spelling_the_schema_does_not_list_is_read_as_absent():
    assert DataTypeParser().parse(_el("<x><dataType>bogus</dataType></x>")) is None
