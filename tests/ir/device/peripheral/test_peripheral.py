"""Peripheral: a block mapped at a base address, with what it holds."""

from regforge.ir import AddressBlock, Cluster, Interrupt, Peripheral


def test_a_peripheral_with_a_name_and_a_base_holds_nothing_yet():
    peripheral = Peripheral("UART0", 0x4000C000)
    assert (peripheral.name, peripheral.base_address) == ("UART0", 0x4000C000)
    assert peripheral.alternate_sets == [] and peripheral.registers == []
    assert peripheral.interrupts == [] and peripheral.address_blocks == []
    assert peripheral.clusters == []


def test_what_it_inherits_and_how_it_was_made_are_absent_until_stated():
    peripheral = Peripheral("P", 0x0)
    for name in (
        "description",
        "derived_from",
        "group_name",
        "header_struct_name",
        "default_size",
        "default_access",
        "default_reset_value",
        "default_reset_mask",
        "default_protection",
        "dim",
        "expanded_from",
        "origin",
    ):
        assert getattr(peripheral, name) is None, name


def test_each_peripheral_has_lists_of_its_own():
    one, other = Peripheral("A", 0x0), Peripheral("B", 0x0)
    one.clusters.append(Cluster("C", 0x0))
    one.interrupts.append(Interrupt("I", 1))
    one.address_blocks.append(AddressBlock(0x0, 0x4))
    assert other.clusters == [] and other.interrupts == [] and other.address_blocks == []
