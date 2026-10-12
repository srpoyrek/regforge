"""DimParser: reads the <dim> group and the <dimIndex> label list."""

import xml.etree.ElementTree as ET

import pytest

from regforge.readers.svd import parse_dim_index
from regforge.readers.svd.device.peripheral.dim import DimParser
from regforge.readers.svd.element_parser import ParseContext


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_dim_index_reads_lists_and_ranges():
    assert parse_dim_index("0-3,7") == ["0", "1", "2", "3", "7"]
    assert parse_dim_index("A-D") == ["A", "B", "C", "D"]
    assert parse_dim_index(" x , y ") == ["x", "y"]


def test_dim_index_notes_a_reversed_range():
    notes: list[str] = []
    assert parse_dim_index("3-0", notes) == ["0", "1", "2", "3"]
    assert len(notes) == 1 and "reversed" in notes[0]


def test_the_dim_parser_reads_the_whole_group():
    dim = DimParser(ParseContext()).parse(
        _el(
            "<r><dim>4</dim><dimIncrement>0x10</dimIncrement><dimIndex>A,B,C,D</dimIndex>"
            "<dimName>CH</dimName></r>"
        ),
        "CH%s",
    )
    assert dim is not None
    assert (dim.count, dim.increment, dim.index, dim.name) == (4, 16, ["A", "B", "C", "D"], "CH")


def test_the_dim_parser_reads_array_index_names():
    dim = DimParser(ParseContext()).parse(
        _el(
            "<r><dim>2</dim><dimIncrement>4</dimIncrement><dimArrayIndex>"
            "<enumeratedValue><name>LOW</name><value>0</value></enumeratedValue>"
            "<enumeratedValue><name>HIGH</name><value>1</value></enumeratedValue>"
            "</dimArrayIndex></r>"
        ),
        "R[%s]",
    )
    assert dim is not None
    assert [e.name for e in dim.array_index] == ["LOW", "HIGH"]


def test_an_element_with_no_dim_has_none():
    assert DimParser(ParseContext()).parse(_el("<r/>"), "R") is None


def test_a_placeholder_without_a_dim_is_refused():
    with pytest.raises(ValueError, match="placeholder"):
        DimParser(ParseContext()).parse(_el("<r/>"), "R%s")


def test_a_negative_dim_is_refused():
    with pytest.raises(ValueError, match="negative"):
        DimParser(ParseContext()).parse(_el("<r><dim>-1</dim></r>"), "R%s")


def test_an_increment_without_a_dim_is_noted_and_ignored():
    context = ParseContext()
    assert DimParser(context).parse(_el("<r><dimIncrement>4</dimIncrement></r>"), "R") is None
    assert len(context.warnings) == 1 and "ignored" in context.warnings[0]


def test_a_derived_element_may_leave_the_count_to_its_base():
    dim = DimParser(ParseContext()).parse(
        _el("<r><dimIncrement>4</dimIncrement></r>"), "R%s", derived=True
    )
    assert dim is not None
    assert (dim.count, dim.increment) == (None, 4)


def test_dim_index_notes_are_reported_with_the_elements_name():
    context = ParseContext()
    DimParser(context).parse(
        _el("<r><dim>4</dim><dimIncrement>4</dimIncrement><dimIndex>3-0</dimIndex></r>"), "CH%s"
    )
    assert context.warnings[0].startswith("CH%s: dimIndex range")
