"""Reading <dim>, <dimIncrement> and <dimIndex>, on every element that allows them.

The reader captures the three values and leaves the template in place; the
expansion pass turns it into copies. Only what makes a file unexpandable is
refused here, never the stride, which needs a resolved size.
"""

import pytest

from regforge.readers.svd import SvdReader, parse_dim_index

_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>D</name><addressUnitBits>8</addressUnitBits><width>32</width>
  <size>32</size><access>read-write</access>
  <peripherals>
{peripherals}
  </peripherals>
</device>
"""


def _read(tmp_path, peripherals):
    path = tmp_path / "d.svd"
    path.write_text(_TEMPLATE.format(peripherals=peripherals), encoding="utf-8")
    return SvdReader().read(path)


def _peripheral(body):
    return f"<peripheral>{body}<baseAddress>0x40000000</baseAddress></peripheral>"


def _register(body):
    return _peripheral(f"<name>P</name><registers><register>{body}</register></registers>")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A,B,C", ["A", "B", "C"]),
        ("0, 1, 2", ["0", "1", "2"]),  # whitespace around a label is not part of it
        ("0-3", ["0", "1", "2", "3"]),
        ("10-12", ["10", "11", "12"]),
        ("A-D", ["A", "B", "C", "D"]),
        ("X", ["X"]),  # one label, for a dim of 1
        ("0-3,7", ["0", "1", "2", "3", "7"]),  # a range inside a list
        ("3-0", ["0", "1", "2", "3"]),  # reversed: read ascending, and reported
        ("D-A", ["A", "B", "C", "D"]),
    ],
)
def test_parse_dim_index(text, expected):
    assert parse_dim_index(text) == expected


def test_peripheral_dim_is_captured_not_expanded(tmp_path):
    device = _read(
        tmp_path,
        _peripheral("<dim>4</dim><dimIncrement>0x400</dimIncrement><name>UART%s</name>"),
    )
    assert [p.name for p in device.peripherals] == ["UART%s"]  # still the template
    dim = device.peripherals[0].dim
    assert (dim.count, dim.increment, dim.index) == (4, 0x400, None)
    assert dim.labels == ["0", "1", "2", "3"]


def test_peripheral_dim_index_labels(tmp_path):
    device = _read(
        tmp_path,
        _peripheral(
            "<dim>3</dim><dimIncrement>0x1000</dimIncrement><dimIndex>A,B,C</dimIndex>"
            "<name>GPIO%s</name>"
        ),
    )
    assert device.peripherals[0].dim.index == ["A", "B", "C"]


def test_register_dim_is_captured(tmp_path):
    device = _read(
        tmp_path,
        _register(
            "<dim>8</dim><dimIncrement>4</dimIncrement><name>DATA[%s]</name>"
            "<addressOffset>0x10</addressOffset>"
        ),
    )
    register = device.peripherals[0].registers[0]
    assert register.name == "DATA[%s]"  # brackets kept: the expander reads them
    assert (register.dim.count, register.dim.increment) == (8, 4)


def test_field_dim_is_captured(tmp_path):
    device = _read(
        tmp_path,
        _register(
            "<name>MODER</name><addressOffset>0x0</addressOffset><fields><field>"
            "<dim>16</dim><dimIncrement>2</dimIncrement><name>MODE%s</name>"
            "<bitOffset>0</bitOffset><bitWidth>2</bitWidth></field></fields>"
        ),
    )
    field = device.peripherals[0].registers[0].fields[0]
    assert (field.dim.count, field.dim.increment) == (16, 2)  # increment in bits


def test_cluster_dim_is_captured(tmp_path):
    device = _read(
        tmp_path,
        _peripheral(
            "<name>DMA</name><registers><cluster><dim>3</dim><dimIncrement>0x10</dimIncrement>"
            "<dimIndex>A-C</dimIndex><name>CH%s</name><addressOffset>0x10</addressOffset>"
            "<register><name>CTRL</name><addressOffset>0x0</addressOffset></register>"
            "</cluster></registers>"
        ),
    )
    dim = device.peripherals[0].clusters[0].dim
    assert (dim.count, dim.increment, dim.index) == (3, 0x10, ["A", "B", "C"])


def test_no_dim_reads_as_none(tmp_path):
    device = _read(tmp_path, _register("<name>R</name><addressOffset>0x0</addressOffset>"))
    assert device.peripherals[0].dim is None
    assert device.peripherals[0].registers[0].dim is None


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("<name>UART%s</name>", "no <dim>"),
        ("<dim>-1</dim><dimIncrement>0x400</dimIncrement><name>UART%s</name>", "negative"),
    ],
)
def test_unexpandable_dim_is_refused_at_read(tmp_path, body, message):
    with pytest.raises(ValueError, match=message):
        _read(tmp_path, _peripheral(body))


def test_reversed_range_is_reported_by_the_reader(tmp_path):
    reader = SvdReader()
    path = tmp_path / "d.svd"
    path.write_text(
        _TEMPLATE.format(
            peripherals=_peripheral(
                "<dim>4</dim><dimIncrement>0x400</dimIncrement><dimIndex>3-0</dimIndex>"
                "<name>UART%s</name>"
            )
        ),
        encoding="utf-8",
    )
    device = reader.read(path)
    assert device.peripherals[0].dim.index == ["0", "1", "2", "3"]
    assert reader.warnings == ["UART%s: dimIndex range 3-0 is reversed -- read as 0-3"]
    reader.read(path)
    assert len(reader.warnings) == 1  # cleared per read, not accumulated


def test_label_count_mismatch_is_read_as_is(tmp_path):
    # Not refused: expansion trusts <dim> and reports it (see tests/resolve).
    device = _read(
        tmp_path,
        _peripheral(
            "<dim>4</dim><dimIncrement>0x400</dimIncrement><dimIndex>A,B</dimIndex>"
            "<name>UART%s</name>"
        ),
    )
    assert device.peripherals[0].dim.index == ["A", "B"]


def test_dim_name_and_array_index_are_captured(tmp_path):
    device = _read(
        tmp_path,
        _register(
            "<dim>2</dim><dimIncrement>4</dimIncrement><name>BUF[%s]</name>"
            "<dimName>Buffer</dimName><dimArrayIndex>"
            "<enumeratedValue><name>RX</name><description>receive</description><value>0</value></enumeratedValue>"
            "<enumeratedValue><name>TX</name><value>1</value></enumeratedValue>"
            "</dimArrayIndex><addressOffset>0x0</addressOffset>"
        ),
    )
    dim = device.peripherals[0].registers[0].dim
    assert dim.name == "Buffer"
    assert [(v.name, v.value, v.description) for v in dim.array_index] == [
        ("RX", 0, "receive"),
        ("TX", 1, None),
    ]


def test_missing_increment_and_zero_dim_are_read_as_is(tmp_path):
    # Neither is refused: expansion reports them (one instance / dropped).
    device = _read(
        tmp_path,
        _peripheral("<dim>2</dim><name>UART%s</name>")
        + _peripheral("<dim>0</dim><dimIncrement>0x100</dimIncrement><name>GHOST%s</name>"),
    )
    uart, ghost = device.peripherals
    assert (uart.dim.count, uart.dim.increment) == (2, None)
    assert ghost.dim.count == 0


def test_increment_without_dim_is_noted_and_ignored(tmp_path):
    reader = SvdReader()
    path = tmp_path / "d.svd"
    path.write_text(
        _TEMPLATE.format(
            peripherals=_peripheral("<name>P</name><dimIncrement>0x100</dimIncrement>")
        ),
        encoding="utf-8",
    )
    device = reader.read(path)
    assert device.peripherals[0].dim is None
    assert reader.warnings == ["P: <dimIncrement> without <dim> -- ignored"]


def test_partial_dim_is_kept_for_a_derived_peripheral(tmp_path):
    # No <dim> of its own, but derivedFrom: the count comes from the base later.
    device = _read(
        tmp_path,
        '<peripheral derivedFrom="SER%s"><dimIncrement>0x200</dimIncrement><name>SERX%s</name>'
        "<baseAddress>0x40063000</baseAddress></peripheral>",
    )
    dim = device.peripherals[0].dim
    assert (dim.count, dim.increment, dim.index) == (None, 0x200, None)


def test_dim_without_placeholder_is_read_as_is(tmp_path):
    # Not refused: expansion appends the index and reports it (see tests/resolve).
    device = _read(
        tmp_path, _peripheral("<dim>4</dim><dimIncrement>0x400</dimIncrement><name>UART</name>")
    )
    assert device.peripherals[0].name == "UART"
    assert device.peripherals[0].dim.count == 4


def test_register_and_field_get_the_same_checks(tmp_path):
    # One rule for every element: the register and field builders route through it too.
    with pytest.raises(ValueError, match="no <dim>"):
        _read(tmp_path, _register("<name>D%s</name><addressOffset>0x0</addressOffset>"))
    with pytest.raises(ValueError, match="no <dim>"):
        _read(
            tmp_path,
            _register(
                "<name>R</name><addressOffset>0x0</addressOffset><fields><field><name>F%s</name>"
                "<bitOffset>0</bitOffset><bitWidth>1</bitWidth></field></fields>"
            ),
        )
