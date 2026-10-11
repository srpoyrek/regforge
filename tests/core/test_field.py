"""Field: the number its bits hold, and how to read and write it in a register word."""

import pytest

from regforge.ir import (
    Access,
    Dim,
    EnumeratedValue,
    EnumSet,
    EnumUsage,
    Field,
    ModifiedWriteValues,
    ReadAction,
    WriteConstraint,
)


def _mode() -> Field:
    return Field("MODE", 1, 2)  # bits [2:1], mask 0b110


def test_max_value_is_the_largest_number_the_width_holds():
    assert _mode().max_value == 0b11
    assert Field("EN", 0, 1).max_value == 1


def test_positions_are_the_bits_the_field_covers():
    assert list(_mode().positions) == [1, 2]


def test_extract_reads_the_number_in_the_fields_bits():
    assert _mode().extract(0b0110) == 3
    assert _mode().extract(0b0010) == 1  # the neighbouring bits are ignored
    assert _mode().extract(0b1001) == 0


def test_insert_replaces_only_the_fields_bits():
    assert _mode().insert(0b0000, 2) == 0b0100
    assert _mode().insert(0b1111, 0) == 0b1001  # bits outside the field survive


def test_insert_then_extract_round_trips():
    word = _mode().insert(0b1000, 3)
    assert _mode().extract(word) == 3


def test_insert_refuses_a_value_that_does_not_fit():
    with pytest.raises(ValueError, match="MODE"):
        _mode().insert(0, 4)  # 4 needs three bits, the field has two
    with pytest.raises(ValueError, match="MODE"):
        _mode().insert(0, -1)


def test_a_field_with_no_enumerated_sets_has_no_enums():
    field = Field("EN", 0, 1)
    assert field.enum_sets == []
    assert field.enums == []


def test_enums_flattens_every_sets_values_in_order():
    read = EnumSet([EnumeratedValue("OFF", 0)], usage=EnumUsage.READ)
    write = EnumSet([EnumeratedValue("CLEAR", 1)], usage=EnumUsage.WRITE)
    field = Field("FLAG", 0, 1, enum_sets=[read, write])
    assert [e.name for e in field.enums] == ["OFF", "CLEAR"]


def test_the_side_effect_characteristics_default_to_none():
    field = Field("F", 0, 1)
    assert field.modified_write_values is None and field.read_action is None
    assert field.write_constraint is None


def test_a_flag_field_can_describe_its_side_effects():
    field = Field(
        "OVF",
        0,
        1,
        modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR,
        read_action=ReadAction.CLEAR,
        write_constraint=WriteConstraint(write_as_read=True),
    )
    assert field.modified_write_values is ModifiedWriteValues.ONE_TO_CLEAR
    assert field.read_action is ReadAction.CLEAR
    assert field.write_constraint is not None and field.write_constraint.write_as_read


def test_a_field_is_readable_and_writable_by_its_access():
    read_only = Field("R", 0, 1, access=Access.READ_ONLY)
    write_once = Field("W", 0, 1, access=Access.WRITE_ONCE)
    assert (read_only.is_readable, read_only.is_writable) == (True, False)
    assert (write_once.is_readable, write_once.is_writable) == (False, True)


def test_an_unresolved_field_access_counts_as_read_write():
    field = Field("F", 0, 1)
    assert (field.is_readable, field.is_writable) == (True, True)


def test_lsb_msb_and_bit_range_spell_the_svd_range():
    mode = _mode()  # bits [2:1]
    assert (mode.lsb, mode.msb, mode.bit_range) == (1, 2, "[2:1]")
    assert Field("EN", 0, 1).bit_range == "[0:0]"


def test_a_one_bit_field_is_a_single_bit():
    assert Field("EN", 0, 1).is_single_bit
    assert not _mode().is_single_bit


def test_overlaps_is_true_when_two_fields_share_a_bit():
    a, b, c = Field("A", 0, 2), Field("B", 1, 2), Field("C", 2, 2)
    assert a.overlaps(b) and b.overlaps(a)
    assert not a.overlaps(c)  # A is bits 0-1, C is bits 2-3


def test_fits_in_the_register_width():
    assert Field("F", 0, 8).fits_in(8)
    assert not Field("F", 1, 8).fits_in(8)


def test_an_array_field_fits_only_if_its_last_copy_does():
    od = Field("OD", 0, 1, dim=Dim(16, 2, array=True))  # copies at bits 0, 2, ..., 30
    assert od.fits_in(31)
    assert not od.fits_in(30)


def test_a_field_with_a_read_action_is_not_safe_to_read():
    pop = Field("DATA", 0, 8, access=Access.READ_ONLY, read_action=ReadAction.CLEAR)
    plain = Field("STATUS", 0, 8, access=Access.READ_ONLY)
    assert pop.has_read_side_effect and not pop.is_safe_to_read
    assert not plain.has_read_side_effect and plain.is_safe_to_read


def test_a_write_only_field_is_not_safe_to_read():
    assert not Field("CMD", 0, 8, access=Access.WRITE_ONLY).is_safe_to_read


def test_a_per_bit_write_field_needs_a_direct_write():
    flag = Field("OVF", 0, 1, modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR)
    whole = Field("X", 0, 1, modified_write_values=ModifiedWriteValues.CLEAR)
    assert flag.needs_direct_write
    assert not whole.needs_direct_write  # acts on the whole field, not per bit
    assert not Field("MODE", 0, 2).needs_direct_write


def test_accepts_checks_width_access_and_range():
    level = Field(
        "LEVEL",
        0,
        4,
        access=Access.READ_WRITE,
        write_constraint=WriteConstraint(minimum=2, maximum=9),
    )
    assert [level.accepts(v) for v in (0, 1, 2, 9, 10, 16)] == [
        False,
        False,
        True,
        True,
        False,
        False,
    ]


def test_accepts_refuses_a_read_only_field_and_a_value_too_wide_for_it():
    assert not Field("ID", 0, 4, access=Access.READ_ONLY).accepts(1)
    assert not Field("MODE", 0, 2).accepts(4)
    assert Field("MODE", 0, 2).accepts(3)


def test_accepts_with_use_enumerated_values_allows_only_the_named_numbers():
    mode = Field(
        "MODE",
        0,
        2,
        enum_sets=[EnumSet([EnumeratedValue("A", 0), EnumeratedValue("C", 3)])],
        write_constraint=WriteConstraint(use_enumerated_values=True),
    )
    assert [mode.accepts(v) for v in range(4)] == [True, False, False, True]


def test_enum_set_for_prefers_the_matching_direction():
    both = EnumSet(usage=EnumUsage.READ_WRITE)
    read = EnumSet(usage=EnumUsage.READ)
    write = EnumSet(usage=EnumUsage.WRITE)
    split = Field("F", 0, 1, enum_sets=[both, read, write])
    assert split.enum_set_for(EnumUsage.READ) is read
    assert split.enum_set_for(EnumUsage.WRITE) is write
    assert Field("G", 0, 1, enum_sets=[both]).enum_set_for(EnumUsage.WRITE) is both
    assert Field("H", 0, 1).enum_set_for(EnumUsage.READ) is None


def test_enum_name_reads_the_read_set_and_enum_value_writes_the_write_set():
    read = EnumSet([EnumeratedValue("IDLE", 0), EnumeratedValue("BUSY", 1)], usage=EnumUsage.READ)
    write = EnumSet(
        [EnumeratedValue("STOP", 0), EnumeratedValue("START", 1)], usage=EnumUsage.WRITE
    )
    cmd = Field("CMD", 0, 1, enum_sets=[read, write])
    assert cmd.enum_name(1) == "BUSY"
    assert cmd.enum_value("START") == 1
    assert cmd.enum_name(5) is None
    assert Field("PLAIN", 0, 1).enum_value("START") is None


def test_a_field_is_write_once_by_its_access():
    assert Field("LOCK", 0, 1, access=Access.WRITE_ONCE).is_write_once
    assert Field("KEY", 0, 8, access=Access.READ_WRITE_ONCE).is_write_once
    assert not Field("EN", 0, 1, access=Access.READ_WRITE).is_write_once
    assert not Field("EN", 0, 1).is_write_once  # unresolved counts as read-write


def test_accepts_does_not_count_the_catch_all_as_a_named_value():
    named_or_other = EnumSet(
        [EnumeratedValue("A", 0), EnumeratedValue("others", None, is_default=True)]
    )
    mode = Field(
        "MODE",
        0,
        2,
        enum_sets=[named_or_other],
        write_constraint=WriteConstraint(use_enumerated_values=True),
    )
    assert [mode.accepts(v) for v in range(4)] == [True, False, False, False]
