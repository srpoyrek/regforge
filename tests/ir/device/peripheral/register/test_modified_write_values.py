"""ModifiedWriteValues: what a write does to the bits written."""

from regforge.ir import ModifiedWriteValues


def test_values_are_spelled_as_in_svd():
    assert [m.value for m in ModifiedWriteValues] == [
        "oneToClear",
        "oneToSet",
        "oneToToggle",
        "zeroToClear",
        "zeroToSet",
        "zeroToToggle",
        "clear",
        "set",
        "modify",
    ]


def test_the_one_to_and_zero_to_kinds_act_per_bit():
    per_bit = [m for m in ModifiedWriteValues if m.acts_per_bit]
    assert [m.value for m in per_bit] == [
        "oneToClear",
        "oneToSet",
        "oneToToggle",
        "zeroToClear",
        "zeroToSet",
        "zeroToToggle",
    ]


def test_clear_set_and_modify_do_not_act_per_bit():
    # They act on the whole field or register, whatever the bits written.
    assert not ModifiedWriteValues.CLEAR.acts_per_bit
    assert not ModifiedWriteValues.SET.acts_per_bit
    assert not ModifiedWriteValues.MODIFY.acts_per_bit


def test_which_kinds_act_on_ones_and_which_on_zeros():
    on_one = [m.value for m in ModifiedWriteValues if m.acts_on_one]
    on_zero = [m.value for m in ModifiedWriteValues if m.acts_on_zero]
    assert on_one == ["oneToClear", "oneToSet", "oneToToggle"]
    assert on_zero == ["zeroToClear", "zeroToSet", "zeroToToggle"]


def test_value_after_write_for_the_per_bit_kinds():
    # A 4-bit field holding 0b1100, written 0b1010.
    expected = {
        ModifiedWriteValues.ONE_TO_CLEAR: 0b0100,
        ModifiedWriteValues.ONE_TO_SET: 0b1110,
        ModifiedWriteValues.ONE_TO_TOGGLE: 0b0110,
        ModifiedWriteValues.ZERO_TO_CLEAR: 0b1000,
        ModifiedWriteValues.ZERO_TO_SET: 0b1101,
        ModifiedWriteValues.ZERO_TO_TOGGLE: 0b1001,
    }
    for kind, value in expected.items():
        assert kind.value_after_write(0b1100, 0b1010, 4) == value, kind


def test_value_after_write_for_clear_set_and_modify():
    assert ModifiedWriteValues.CLEAR.value_after_write(0b1100, 0b0001, 4) == 0
    assert ModifiedWriteValues.SET.value_after_write(0b0000, 0b0001, 4) == 0b1111
    assert ModifiedWriteValues.MODIFY.value_after_write(0b1100, 0b0001, 4) is None


def test_a_read_modify_write_of_a_write_one_to_clear_register_clears_every_flag():
    clear = ModifiedWriteValues.ONE_TO_CLEAR
    # Two flags are up (0b11). Writing back what was read clears both...
    assert clear.value_after_write(0b11, 0b11, 2) == 0b00
    # ...writing only the bit you handled clears just that flag.
    assert clear.value_after_write(0b11, 0b01, 2) == 0b10
