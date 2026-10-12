"""Placement: where each register of a peripheral sits, with the clusters around it."""

from regforge.ir import Cluster, Dim, Peripheral, Register
from regforge.writers.html.device.peripheral.placement import placed_registers


def test_plain_registers_keep_their_offset_and_name():
    peripheral = Peripheral("P", 0x1000, registers=[Register("A", 0x0), Register("B", 0x4)])
    placed = placed_registers(peripheral)
    assert [(p.path, p.offset, p.note) for p in placed] == [("A", 0, None), ("B", 4, None)]


def test_a_register_in_a_cluster_takes_the_clusters_name_and_offset():
    cluster = Cluster("CH", 0x10, registers=[Register("CTRL", 0x4)])
    (placed,) = placed_registers(Peripheral("P", 0x0, clusters=[cluster]))
    assert (placed.path, placed.offset) == ("CH.CTRL", 0x14)


def test_nested_clusters_add_up_and_chain_their_names():
    inner = Cluster("SUB", 0x20, registers=[Register("R", 0x1)])
    outer = Cluster("CH", 0x100, clusters=[inner])
    (placed,) = placed_registers(Peripheral("P", 0x0, clusters=[outer]))
    assert (placed.path, placed.offset) == ("CH.SUB.R", 0x121)


def test_a_cluster_array_leaves_a_note_on_its_registers():
    cluster = Cluster("CH", 0x10, registers=[Register("CTRL", 0x0)], dim=Dim(4, 0x10, array=True))
    (placed,) = placed_registers(Peripheral("P", 0x0, clusters=[cluster]))
    assert placed.note == "array of 4, 0x10 units apart"


def test_registers_come_before_clusters_in_declaration_order():
    peripheral = Peripheral(
        "P",
        0x0,
        registers=[Register("A", 0x0)],
        clusters=[Cluster("C", 0x8, registers=[Register("B", 0x0)])],
    )
    assert [p.path for p in placed_registers(peripheral)] == ["A", "C.B"]
