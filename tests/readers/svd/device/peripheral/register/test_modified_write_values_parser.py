"""ModifiedWriteValuesParser: reads the ``modifiedWriteValues`` child of an element."""

import xml.etree.ElementTree as ET

from regforge.ir import ModifiedWriteValues
from regforge.readers.svd.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesParser,
)


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_it_reads_the_tag_it_names():
    element = _el("<x><modifiedWriteValues>zeroToToggle</modifiedWriteValues></x>")
    assert ModifiedWriteValuesParser().parse(element) is ModifiedWriteValues.ZERO_TO_TOGGLE


def test_it_reads_every_member_by_its_spelling():
    for member in ModifiedWriteValues:
        element = _el(f"<x><modifiedWriteValues>{member.value}</modifiedWriteValues></x>")
        assert ModifiedWriteValuesParser().parse(element) is member


def test_a_missing_child_is_read_as_absent():
    assert ModifiedWriteValuesParser().parse(_el("<x/>")) is None


def test_a_spelling_the_schema_does_not_list_is_read_as_absent():
    assert (
        ModifiedWriteValuesParser().parse(
            _el("<x><modifiedWriteValues>bogus</modifiedWriteValues></x>")
        )
        is None
    )
