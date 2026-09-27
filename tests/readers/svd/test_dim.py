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
        ("3-0", []),  # a reversed range names nothing; the count check refuses it
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
        ("<dim>4</dim><name>UART%s</name>", "no <dimIncrement>"),
        ("<dim>4</dim><dimIncrement>0x400</dimIncrement><name>UART</name>", "no %s placeholder"),
        ("<name>UART%s</name>", "no <dim>"),
        (
            "<dim>4</dim><dimIncrement>0x400</dimIncrement><dimIndex>A,B</dimIndex>"
            "<name>UART%s</name>",
            r"2 label\(s\) for <dim> 4",
        ),
        ("<dim>0</dim><dimIncrement>0x400</dimIncrement><name>UART%s</name>", "at least 1"),
    ],
)
def test_unexpandable_dim_is_refused_at_read(tmp_path, body, message):
    with pytest.raises(ValueError, match=message):
        _read(tmp_path, _peripheral(body))


def test_register_and_field_get_the_same_checks(tmp_path):
    # One rule for every element: the register and field builders route through it too.
    with pytest.raises(ValueError, match="no <dimIncrement>"):
        _read(tmp_path, _register("<dim>2</dim><name>D%s</name><addressOffset>0x0</addressOffset>"))
    with pytest.raises(ValueError, match="no <dim>"):
        _read(
            tmp_path,
            _register(
                "<name>R</name><addressOffset>0x0</addressOffset><fields><field><name>F%s</name>"
                "<bitOffset>0</bitOffset><bitWidth>1</bitWidth></field></fields>"
            ),
        )
