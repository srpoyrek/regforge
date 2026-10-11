"""Field: the number its bits hold, and how to read and write it in a register word."""

import pytest

from regforge.ir import EnumeratedValue, EnumSet, EnumUsage, Field


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
