"""RegistersOf: the flat list of registers a peripheral or cluster reads over its sets."""

import copy

from regforge.ir import AlternateSet, Cluster, Peripheral, Register


def _two() -> tuple[Register, Register]:
    return Register("A", 0x0, size=32), Register("B", 0x4, size=32)


def test_registers_passed_to_the_constructor_become_one_set_each():
    a, b = _two()
    peripheral = Peripheral("P", 0x0, registers=[a, b])
    assert [[v.name for v in s.views] for s in peripheral.alternate_sets] == [["A"], ["B"]]
    assert peripheral.registers == [a, b]


def test_a_peripheral_with_no_registers_has_no_sets_and_an_empty_list():
    peripheral = Peripheral("P", 0x0)
    assert peripheral.alternate_sets == [] and peripheral.registers == []


def test_registers_are_the_views_of_every_set_in_order():
    a, b = _two()
    c = Register("C", 0x0, size=32)
    peripheral = Peripheral("P", 0x0, alternate_sets=[AlternateSet((a, c)), AlternateSet((b,))])
    assert [r.name for r in peripheral.registers] == ["A", "C", "B"]


def test_assigning_registers_replaces_the_sets():
    a, b = _two()
    peripheral = Peripheral("P", 0x0, alternate_sets=[AlternateSet((a, b))])
    peripheral.registers = [b]
    assert [[v.name for v in s.views] for s in peripheral.alternate_sets] == [["B"]]


def test_reading_registers_gives_a_fresh_list_so_changing_it_leaves_the_sets_alone():
    a, b = _two()
    peripheral = Peripheral("P", 0x0, registers=[a, b])
    peripheral.registers.append(Register("C", 0x8, size=32))
    assert [r.name for r in peripheral.registers] == ["A", "B"]


def test_a_cluster_reads_its_registers_the_same_way():
    a, b = _two()
    cluster = Cluster("CH", 0x10, registers=[a, b])
    assert [s.primary.name for s in cluster.alternate_sets] == ["A", "B"]
    cluster.alternate_sets = [AlternateSet((b, a))]
    assert [r.name for r in cluster.registers] == ["B", "A"]


def test_a_copy_of_a_peripheral_keeps_its_sets_and_shares_nothing():
    a, b = _two()
    original = Peripheral("P", 0x0, alternate_sets=[AlternateSet((a, b))])
    duplicate = copy.deepcopy(original)
    assert duplicate == original
    assert duplicate.registers[0] is not original.registers[0]


def test_two_peripherals_are_equal_when_their_sets_are():
    one = Peripheral("P", 0x0, registers=[Register("A", 0x0, size=32)])
    other = Peripheral("P", 0x0, registers=[Register("A", 0x0, size=32)])
    assert one == other


def test_the_registers_are_left_out_of_the_representation():
    assert "registers=" not in repr(Peripheral("P", 0x0, registers=[Register("A", 0x0)]))
