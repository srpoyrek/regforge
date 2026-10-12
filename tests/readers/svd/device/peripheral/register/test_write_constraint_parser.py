"""WriteConstraintParser: reads a <writeConstraint> element."""

import xml.etree.ElementTree as ET

from regforge.readers.svd.device.peripheral.register.write_constraint import WriteConstraintParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_write_constraint_reads_its_flags_and_range():
    constraint = WriteConstraintParser().parse(
        _el(
            "<x><writeConstraint><writeAsRead>1</writeAsRead>"
            "<range><minimum>#10</minimum><maximum>0x1F</maximum></range></writeConstraint></x>"
        )
    )
    assert constraint is not None
    assert (constraint.write_as_read, constraint.minimum, constraint.maximum) == (True, 2, 31)


def test_a_missing_write_constraint_is_none():
    assert WriteConstraintParser().parse(_el("<x/>")) is None
