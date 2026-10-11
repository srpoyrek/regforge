"""Primitives: the integer and boolean spellings every parser relies on."""

import xml.etree.ElementTree as ET

from regforge.readers.svd import parse_svd_bool, parse_svd_int, parse_svd_value


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


def test_an_enumerated_value_reads_plain_numbers_in_every_form():
    forms = [parse_svd_value(t) for t in ("0x1F", "0b101", "#101", "42")]
    assert forms == [(31, 0), (5, 0), (5, 0), (42, 0)]


def test_an_enumerated_value_may_write_bits_as_dont_care():
    assert parse_svd_value("#01xx") == (0b0100, 0b0011)
    assert parse_svd_value("0b01XX") == (0b0100, 0b0011)
    assert parse_svd_value("#0x") == (0, 1)
