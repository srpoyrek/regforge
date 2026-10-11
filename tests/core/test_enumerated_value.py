"""EnumeratedValue: a name for one number a field's bits can hold."""

from regforge.ir import EnumeratedValue, EnumSet, Field
from regforge.ir.enumerated_value import EnumeratedValue as EnumeratedValueFromModule


def test_holds_a_name_and_the_number_it_stands_for():
    value = EnumeratedValue("OUTPUT", 1)
    assert (value.name, value.value) == ("OUTPUT", 1)


def test_description_is_optional():
    assert EnumeratedValue("INPUT", 0).description is None
    assert EnumeratedValue("INPUT", 0, "Input mode").description == "Input mode"


def test_equal_when_name_number_and_description_match():
    assert EnumeratedValue("ALT", 2) == EnumeratedValue("ALT", 2)
    assert EnumeratedValue("ALT", 2) != EnumeratedValue("ANALOG", 3)
    assert EnumeratedValue("ALT", 2) != EnumeratedValue("ALT", 2, "Alternate function")


def test_two_names_may_share_one_number():
    # SVD files repeat numbers; the IR keeps both and leaves judging them to the linter.
    pair = [EnumeratedValue("RESERVED", 3), EnumeratedValue("ANALOG", 3)]
    assert [v.value for v in pair] == [3, 3]


def test_numbers_may_leave_gaps():
    # nRF GPIOTE MODE has 0, 1 and 3 but no 2: only the listed numbers exist.
    field = Field(
        "MODE",
        0,
        2,
        enum_sets=[EnumSet([EnumeratedValue(n, v) for n, v in (("A", 0), ("B", 1), ("C", 3))])],
    )
    assert [e.value for e in field.enums] == [0, 1, 3]


def test_a_field_carries_its_enumerated_values_in_order():
    field = Field(
        "MODE",
        1,
        2,
        enum_sets=[EnumSet([EnumeratedValue("INPUT", 0), EnumeratedValue("OUTPUT", 1)])],
    )
    assert [e.name for e in field.enums] == ["INPUT", "OUTPUT"]


def test_it_is_the_same_class_from_the_package_and_from_its_own_module():
    assert EnumeratedValueFromModule is EnumeratedValue
