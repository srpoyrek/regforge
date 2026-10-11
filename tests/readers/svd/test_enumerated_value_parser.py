"""EnumeratedValueParser: reads an <enumeratedValue> element."""

import xml.etree.ElementTree as ET

import pytest

from regforge.readers.svd.enumerated_value import EnumeratedValueParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_an_enumerated_value_reads_name_number_description_and_default():
    value = EnumeratedValueParser().parse(
        _el(
            "<e><name>OTHER</name><value>0x3</value><description>rest</description>"
            "<isDefault>true</isDefault></e>"
        )
    )
    assert value is not None
    assert (value.name, value.value, value.description, value.is_default) == (
        "OTHER",
        3,
        "rest",
        True,
    )


def test_an_enumerated_value_with_no_number_is_none():
    assert EnumeratedValueParser().parse(_el("<e><name>NAMED_ONLY</name></e>")) is None


def test_parse_all_skips_the_values_with_no_number():
    parent = _el(
        "<set><enumeratedValue><name>A</name></enumeratedValue>"
        "<enumeratedValue><name>B</name><value>1</value></enumeratedValue></set>"
    )
    assert [v.name for v in EnumeratedValueParser().parse_all(parent, "enumeratedValue")] == ["B"]


def test_a_catch_all_entry_is_kept_with_no_number():
    value = EnumeratedValueParser().parse(
        _el(
            "<e><name>others</name><description>Prohibited</description>"
            "<isDefault>true</isDefault></e>"
        )
    )
    assert value is not None
    assert (value.name, value.value, value.description, value.is_default) == (
        "others",
        None,
        "Prohibited",
        True,
    )


def test_an_entry_marked_not_default_with_no_number_is_nothing():
    element = _el("<e><name>X</name><isDefault>false</isDefault></e>")
    assert EnumeratedValueParser().parse(element) is None


@pytest.mark.parametrize(
    ("text", "value", "dont_care"),
    [("#0x", 0, 1), ("#1x", 2, 1), ("0b01xx", 4, 3), ("#000x", 0, 1), ("#01xX", 4, 3)],
)
def test_bits_written_x_become_a_dont_care_mask(text, value, dont_care):
    parsed = EnumeratedValueParser().parse(_el(f"<e><name>P</name><value>{text}</value></e>"))
    assert parsed is not None
    assert (parsed.value, parsed.dont_care) == (value, dont_care)


def test_parse_all_can_keep_only_the_numbered_entries():
    parent = _el(
        "<set><enumeratedValue><name>A</name><value>1</value></enumeratedValue>"
        "<enumeratedValue><name>others</name><isDefault>true</isDefault></enumeratedValue></set>"
    )
    parser = EnumeratedValueParser()
    assert [v.name for v in parser.parse_all(parent, "enumeratedValue")] == ["A", "others"]
    numbered = parser.parse_all(parent, "enumeratedValue", numbered_only=True)
    assert [v.name for v in numbered] == ["A"]
