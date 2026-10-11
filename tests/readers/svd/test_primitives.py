"""Primitives: the integer and boolean spellings every parser relies on."""

import xml.etree.ElementTree as ET

from regforge.readers.svd import parse_svd_bool, parse_svd_int


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_integers_are_read_in_hex_binary_and_decimal():
    assert [parse_svd_int(t) for t in ("0x1F", "0b101", "#101", "42")] == [31, 5, 5, 42]


def test_booleans_accept_true_false_one_and_zero():
    assert [parse_svd_bool(t) for t in ("true", "1", "false", "0", "maybe")] == [
        True,
        True,
        False,
        False,
        None,
    ]
