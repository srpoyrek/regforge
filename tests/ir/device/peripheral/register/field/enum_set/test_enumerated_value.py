"""EnumeratedValue: a name for one number a field's bits can hold."""

from regforge.ir import EnumeratedValue, EnumSet, Field
from regforge.ir.device.peripheral.register.field.enum_set.enumerated_value import (
    EnumeratedValue as EnumeratedValueFromModule,
)


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


def test_is_default_is_false_unless_marked():
    assert EnumeratedValue("A", 0).is_default is False
    assert EnumeratedValue("OTHER", 0, is_default=True).is_default is True


def test_fits_in_says_whether_the_number_fits_a_width():
    analog = EnumeratedValue("ANALOG", 3)
    assert analog.fits_in(2) and not analog.fits_in(1)
    assert not EnumeratedValue("BAD", -1).fits_in(8)


def test_a_catch_all_entry_names_no_number_of_its_own():
    other = EnumeratedValue("others", None, "Setting prohibited", is_default=True)
    assert other.value is None and other.is_default
    assert not other.matches(0) and other.fits_in(1)
    assert other.label() == "other values"


def test_a_pattern_names_every_number_that_agrees_on_the_bits_it_cares_about():
    busy = EnumeratedValue("BUSY", 0b0100, dont_care=0b0011)  # 0b01xx
    assert busy.is_pattern and not EnumeratedValue("OFF", 0).is_pattern
    assert [n for n in range(8) if busy.matches(n)] == [4, 5, 6, 7]


def test_a_pattern_fits_only_when_its_widest_bit_does():
    busy = EnumeratedValue("BUSY", 0b0100, dont_care=0b0011)
    assert busy.fits_in(3) and not busy.fits_in(2)


def test_label_spells_a_number_in_hex_and_a_pattern_in_binary():
    busy = EnumeratedValue("BUSY", 0b0100, dont_care=0b0011)
    assert EnumeratedValue("A", 3).label() == "0x3"
    assert busy.label() == "0b1xx" and busy.label(bit_width=4) == "0b01xx"
    assert EnumeratedValue("Z", 0, dont_care=0b1).label(bit_width=3) == "0b00x"
