"""EnumSet: the named values of one field, and what can be asked of them."""

import pytest

from regforge.ir import EnumeratedValue, EnumSet, EnumUsage


def _mode() -> EnumSet:
    # 0, 1 and 3 are named; 2 is a gap.
    return EnumSet(
        [EnumeratedValue("INPUT", 0), EnumeratedValue("OUTPUT", 1), EnumeratedValue("ANALOG", 3)]
    )


def test_an_empty_set_has_the_schema_defaults():
    empty = EnumSet()
    assert empty.values == []
    assert empty.name is None and empty.header_enum_name is None and empty.derived_from is None
    assert empty.usage is EnumUsage.READ_WRITE


def test_two_sets_do_not_share_one_value_list():
    assert EnumSet().values is not EnumSet().values


def test_it_keeps_its_values_in_the_order_written():
    assert [v.name for v in _mode().values] == ["INPUT", "OUTPUT", "ANALOG"]


def test_name_of_finds_the_name_for_a_number():
    assert _mode().name_of(1) == "OUTPUT"
    assert _mode().name_of(2) is None  # the gap


def test_value_of_finds_the_number_for_a_name():
    assert _mode().value_of("ANALOG") == 3
    assert _mode().value_of("NOPE") is None


def test_the_first_entry_wins_when_two_names_share_a_number():
    shared = EnumSet([EnumeratedValue("RESERVED", 3), EnumeratedValue("ANALOG", 3)])
    assert shared.name_of(3) == "RESERVED"


def test_oversized_lists_the_values_that_do_not_fit_the_width():
    assert [v.name for v in _mode().oversized(1)] == ["ANALOG"]  # 3 needs two bits
    assert _mode().oversized(2) == []


def test_oversized_flags_a_negative_number():
    assert [v.name for v in EnumSet([EnumeratedValue("BAD", -1)]).oversized(8)] == ["BAD"]


def test_a_set_can_be_a_write_set_that_derives_from_another():
    write = EnumSet(usage=EnumUsage.WRITE, derived_from="MODE_READ")
    assert write.usage is EnumUsage.WRITE and write.derived_from == "MODE_READ"


def test_usage_is_spelled_as_in_svd():
    assert [u.value for u in EnumUsage] == ["read", "write", "read-write"]


def test_numbers_lists_every_entrys_number():
    assert _mode().numbers == [0, 1, 3]


def test_default_entry_is_the_catch_all_or_none():
    catch_all = EnumeratedValue("OTHER", 0, is_default=True)
    assert EnumSet([EnumeratedValue("A", 1), catch_all]).default_entry is catch_all
    assert _mode().default_entry is None


def test_duplicates_are_listed_once_in_the_order_they_first_repeat():
    messy = EnumSet(
        [
            EnumeratedValue("A", 1),
            EnumeratedValue("B", 1),
            EnumeratedValue("A", 2),
            EnumeratedValue("A", 1),
        ]
    )
    assert messy.duplicate_numbers() == [1]
    assert messy.duplicate_names() == ["A"]
    assert _mode().duplicate_numbers() == [] and _mode().duplicate_names() == []


def test_gaps_lists_the_numbers_no_entry_names():
    assert _mode().gaps(2) == [2]
    assert _mode().gaps(1) == []  # 0 and 1 are named; 3 is oversized, not a gap


def test_a_catch_all_entry_leaves_no_gaps():
    catch_all = EnumSet([EnumeratedValue("A", 1), EnumeratedValue("OTHER", 0, is_default=True)])
    assert catch_all.gaps(2) == []


def test_gaps_refuses_a_field_too_wide_to_list():
    with pytest.raises(ValueError, match="too wide"):
        _mode().gaps(17)


def test_is_complete_when_every_number_is_named_or_caught():
    assert _mode().is_complete(1)
    assert not _mode().is_complete(2)  # 2 is missing
    assert EnumSet([EnumeratedValue("OTHER", 0, is_default=True)]).is_complete(8)
