"""EnumSet: the named values of one field, and what can be asked of them."""

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
