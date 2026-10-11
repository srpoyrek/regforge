"""EnumeratedValueParser: reads an <enumeratedValue> element."""

import xml.etree.ElementTree as ET

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
