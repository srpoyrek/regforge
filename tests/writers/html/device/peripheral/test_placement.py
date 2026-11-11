"""Placement: where each register of a peripheral sits, with the clusters around it."""

from regforge.ir import AlternateSet, Cluster, Dim, Peripheral, Register
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


def test_a_register_with_no_alternates_names_none():
    (placed,) = placed_registers(Peripheral("P", 0x0, registers=[Register("A", 0x0)]))
    assert placed.alternates == ()


def test_every_view_of_a_word_names_the_others():
    views = AlternateSet((Register("DR", 0x4), Register("RXD", 0x4), Register("TXD", 0x4)))
    placed = placed_registers(Peripheral("P", 0x0, alternate_sets=[views]))
    assert [(p.path, p.alternates) for p in placed] == [
        ("DR", ("RXD", "TXD")),
        ("RXD", ("DR", "TXD")),
        ("TXD", ("DR", "RXD")),
    ]


def test_every_view_of_a_word_shares_its_offset():
    views = AlternateSet((Register("DR", 0x8), Register("DR8", 0x8)))
    placed = placed_registers(Peripheral("P", 0x1000, alternate_sets=[views]))
    assert {p.offset for p in placed} == {0x8}


def test_views_inside_a_cluster_keep_the_cluster_path():
    views = AlternateSet((Register("XFER_Mem", 0xC), Register("XFER_Periph", 0xC)))
    cluster = Cluster("CH", 0x10, alternate_sets=[views])
    placed = placed_registers(Peripheral("P", 0x0, clusters=[cluster]))
    assert [(p.path, p.offset, p.alternates) for p in placed] == [
        ("CH.XFER_Mem", 0x1C, ("XFER_Periph",)),
        ("CH.XFER_Periph", 0x1C, ("XFER_Mem",)),
    ]


def test_registers_come_before_clusters_in_declaration_order():
    peripheral = Peripheral(
        "P",
        0x0,
        registers=[Register("A", 0x0)],
        clusters=[Cluster("C", 0x8, registers=[Register("B", 0x0)])],
    )
    assert [p.path for p in placed_registers(peripheral)] == ["A", "C.B"]
