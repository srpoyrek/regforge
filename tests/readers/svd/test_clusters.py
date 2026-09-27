"""Reading <cluster>: a register group inside a peripheral, possibly nested."""

from regforge.ir import Access
from regforge.readers.svd import SvdReader

_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>D</name><addressUnitBits>8</addressUnitBits><width>32</width>
  <size>32</size><access>read-write</access>
  <peripherals>
    <peripheral>
      <name>DMA</name>
      <baseAddress>0x40020000</baseAddress>
      <registers>
        <register><name>CFG</name><addressOffset>0x0</addressOffset></register>
{clusters}
      </registers>
    </peripheral>
  </peripherals>
</device>
"""


def _read(tmp_path, clusters):
    path = tmp_path / "d.svd"
    path.write_text(_TEMPLATE.format(clusters=clusters), encoding="utf-8")
    return SvdReader().read(path).peripherals[0]


def test_cluster_is_walked_and_kept_apart_from_registers(tmp_path):
    peripheral = _read(
        tmp_path,
        "<cluster><name>CH</name><description>DMA channel</description>"
        "<addressOffset>0x10</addressOffset>"
        "<register><name>CTRL</name><addressOffset>0x0</addressOffset></register>"
        "<register><name>SRC</name><addressOffset>0x4</addressOffset></register>"
        "</cluster>",
    )
    assert [r.name for r in peripheral.registers] == ["CFG"]  # the cluster is not a register
    cluster = peripheral.clusters[0]
    assert (cluster.name, cluster.address_offset) == ("CH", 0x10)
    assert cluster.description == "DMA channel"
    # Offsets stay relative to the cluster, as written; the layout adds them up.
    assert [(r.name, r.address_offset) for r in cluster.registers] == [("CTRL", 0x0), ("SRC", 0x4)]


def test_cluster_defaults_names_and_derived_from_are_captured(tmp_path):
    peripheral = _read(
        tmp_path,
        "<cluster derivedFrom='CH'><name>CH2</name><addressOffset>0x40</addressOffset>"
        "<headerStructName>CHANNEL</headerStructName><size>16</size><access>read-only</access>"
        "<resetValue>0x1</resetValue><resetMask>0xF</resetMask></cluster>",
    )
    cluster = peripheral.clusters[0]
    assert cluster.derived_from == "CH"  # an attribute, as on a peripheral
    assert cluster.header_struct_name == "CHANNEL"
    assert (cluster.default_size, cluster.default_access) == (16, Access.READ_ONLY)
    assert (cluster.default_reset_value, cluster.default_reset_mask) == (0x1, 0xF)


def test_nested_cluster_is_walked(tmp_path):
    peripheral = _read(
        tmp_path,
        "<cluster><name>CH</name><addressOffset>0x10</addressOffset>"
        "<cluster><name>SUB</name><addressOffset>0x8</addressOffset>"
        "<register><name>R</name><addressOffset>0x0</addressOffset></register>"
        "</cluster></cluster>",
    )
    inner = peripheral.clusters[0].clusters[0]
    assert (inner.name, inner.address_offset) == ("SUB", 0x8)
    assert [r.name for r in inner.registers] == ["R"]


def test_cluster_registers_are_built_by_the_register_builder(tmp_path):
    # Fields and dim on a register inside a cluster read exactly as they do outside one.
    peripheral = _read(
        tmp_path,
        "<cluster><name>CH</name><addressOffset>0x10</addressOffset>"
        "<register><dim>2</dim><dimIncrement>4</dimIncrement><name>DATA[%s]</name>"
        "<addressOffset>0x0</addressOffset><fields><field><name>EN</name>"
        "<bitOffset>0</bitOffset><bitWidth>1</bitWidth></field></fields></register>"
        "</cluster>",
    )
    register = peripheral.clusters[0].registers[0]
    assert register.dim.count == 2
    assert [f.name for f in register.fields] == ["EN"]
