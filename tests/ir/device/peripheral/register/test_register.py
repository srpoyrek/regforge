"""Register: N bits at one address, and the fields that name slices of them."""

import pytest

from regforge.ir import (
    Access,
    DataType,
    Dim,
    Field,
    ModifiedWriteValues,
    Protection,
    ReadAction,
    Register,
    WriteConstraint,
)
from regforge.ir.device.peripheral.register.register import Register as RegisterFromModule


def test_holds_its_name_and_offset_and_leaves_the_rest_unresolved():
    register = Register("CTRL", 0x10)
    assert (register.name, register.address_offset) == ("CTRL", 0x10)
    assert register.size is None
    assert register.reset_value is None and register.reset_mask is None
    assert register.access is None and register.description is None


def test_resolved_values_are_assigned_in_place():
    # The defaults resolution pass fills these from the inheritance chain.
    register = Register("CTRL", 0x0)
    register.size = 32
    register.access = Access.READ_WRITE
    register.reset_value = 0x1
    assert (register.size, register.access, register.reset_value) == (32, Access.READ_WRITE, 0x1)


def test_fields_are_kept_in_the_order_given():
    register = Register("CTRL", 0x0, fields=[Field("EN", 0, 1), Field("MODE", 1, 2)])
    assert [f.name for f in register.fields] == ["EN", "MODE"]


def test_two_registers_do_not_share_one_field_list():
    assert Register("A", 0x0).fields is not Register("B", 0x4).fields


def test_a_register_does_not_know_which_registers_share_its_word():
    # The peripheral or cluster that holds it keeps that, in an AlternateSet.
    register = Register("CR", 0x0)
    assert not hasattr(register, "alternate_register") and not hasattr(register, "alternates")


def test_a_register_array_carries_its_dim_and_a_copy_remembers_its_template():
    template = Register("DATA%s", 0x10, dim=Dim(8, 4))
    copy = Register("DATA0", 0x10, expanded_from="DATA%s")
    assert template.dim is not None and template.dim.length == 8
    assert template.expanded_from is None
    assert copy.dim is None and copy.expanded_from == "DATA%s"


def test_it_is_the_same_class_from_the_package_and_from_its_own_module():
    assert RegisterFromModule is Register


def _ctrl() -> Register:
    # 8-bit register at 0x10: EN is bit 0, MODE is bits [2:1], bits 7..3 are unclaimed.
    return Register("CTRL", 0x10, size=8, fields=[Field("EN", 0, 1), Field("MODE", 1, 2)])


def test_bits_lists_every_bit_least_significant_first():
    result = _ctrl().bits()
    assert [b.position for b in result] == list(range(8))
    assert [b.field.name if b.field else None for b in result][:4] == ["EN", "MODE", "MODE", None]


def test_full_mask_sets_every_bit():
    assert _ctrl().full_mask == 0xFF
    assert Register("WIDE", 0x0, size=32).full_mask == 0xFFFFFFFF


def test_size_in_units_counts_address_units():
    assert _ctrl().size_in_units(8) == 1
    assert Register("WIDE", 0x0, size=32).size_in_units(8) == 4
    assert Register("WIDE", 0x0, size=32).size_in_units(16) == 2  # a 16-bit address unit


def test_end_offset_is_the_first_unit_past_the_register():
    assert _ctrl().end_offset(8) == 0x11
    assert Register("WIDE", 0x20, size=32).end_offset(8) == 0x24


def test_field_named_finds_a_field_or_none():
    register = _ctrl()
    assert register.field_named("MODE") is register.fields[1]
    assert register.field_named("NOPE") is None


def test_field_at_finds_the_field_covering_a_bit():
    register = _ctrl()
    assert register.field_at(0) is register.fields[0]
    assert register.field_at(2) is register.fields[1]  # MODE covers bits 1 and 2
    assert register.field_at(5) is None  # unclaimed


def test_field_at_refuses_a_bit_outside_the_register():
    with pytest.raises(IndexError, match="CTRL"):
        _ctrl().field_at(8)
    with pytest.raises(IndexError, match="CTRL"):
        _ctrl().field_at(-1)


def test_unclaimed_positions_lists_the_bits_no_field_names():
    assert _ctrl().unclaimed_positions() == [3, 4, 5, 6, 7]


def test_functions_that_need_a_size_refuse_an_unresolved_register():
    unresolved = Register("R", 0x0)
    with pytest.raises(ValueError, match="R"):
        _ = unresolved.full_mask
    with pytest.raises(ValueError, match="R"):
        unresolved.end_offset(8)
    with pytest.raises(ValueError, match="R"):
        unresolved.bits()


def test_the_extra_characteristics_default_to_none():
    register = Register("R", 0x0)
    assert register.display_name is None and register.data_type is None
    assert register.protection is None and register.modified_write_values is None
    assert register.read_action is None and register.write_constraint is None


def test_a_status_register_can_describe_its_side_effects():
    register = Register(
        "SR",
        0x4,
        display_name="Status",
        data_type=DataType.UINT32,
        protection=Protection.SECURE,
        modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR,
        read_action=ReadAction.CLEAR,
        write_constraint=WriteConstraint(minimum=0, maximum=3),
    )
    assert register.display_name == "Status" and register.data_type is DataType.UINT32
    assert register.protection is Protection.SECURE
    assert register.modified_write_values is ModifiedWriteValues.ONE_TO_CLEAR
    assert register.read_action is ReadAction.CLEAR
    assert register.write_constraint is not None and register.write_constraint.in_range(2)


def test_a_register_is_readable_and_writable_by_its_access():
    read_only = Register("R", 0x0, access=Access.READ_ONLY)
    write_only = Register("W", 0x0, access=Access.WRITE_ONLY)
    assert (read_only.is_readable, read_only.is_writable) == (True, False)
    assert (write_only.is_readable, write_only.is_writable) == (False, True)


def test_an_unresolved_access_counts_as_read_write():
    register = Register("R", 0x0)
    assert (register.is_readable, register.is_writable) == (True, True)


def test_a_register_with_a_read_action_is_not_safe_to_read():
    fifo = Register("RXDATA", 0x0, access=Access.READ_ONLY, read_action=ReadAction.CLEAR)
    status = Register("STATUS", 0x4, access=Access.READ_ONLY)
    assert fifo.has_read_side_effect and not fifo.is_safe_to_read
    assert not status.has_read_side_effect and status.is_safe_to_read


def test_a_per_bit_write_register_needs_a_direct_write():
    flags = Register("ISR", 0x8, modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR)
    assert flags.needs_direct_write
    assert not Register("CR", 0xC).needs_direct_write


def test_a_register_is_write_once_by_its_access():
    assert Register("LOCK", 0x0, access=Access.WRITE_ONCE).is_write_once
    assert Register("KEY", 0x4, access=Access.READ_WRITE_ONCE).is_write_once
    assert not Register("CR", 0x8, access=Access.READ_WRITE).is_write_once
    assert not Register("CR", 0x8).is_write_once  # unresolved counts as read-write


def test_a_register_is_not_derived_unless_it_says_so():
    assert Register("CTRL", 0x0).derived_from is None
    assert Register("CTRL2", 0x4, derived_from="CTRL").derived_from == "CTRL"


def test_a_register_belongs_to_no_group_unless_the_file_says_so():
    assert Register("CTRL", 0x0).alternate_group is None
    assert Register("CTRL", 0x0, alternate_group="SPI").alternate_group == "SPI"
