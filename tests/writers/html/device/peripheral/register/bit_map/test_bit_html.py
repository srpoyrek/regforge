"""BitHtml: the cell one bit of a bit map joins, what the cell says, and the bit's reset value."""

from regforge.ir import Dim, Field, Register
from regforge.writers.html.device.peripheral.register.bit_map.bit import BitHtml
from regforge.writers.html.wording import NO_VALUE


def _array() -> Register:
    return Register("R", 0x0, size=4, fields=[Field("OD", 0, 1, dim=Dim(4, 1, array=True))])


def test_a_plain_field_and_an_unclaimed_bit_are_copy_zero():
    bits = Register("R", 0x0, size=4, fields=[Field("A", 0, 2)]).bits()
    assert [BitHtml().copy_of(bit) for bit in bits] == [0, 0, 0, 0]


def test_each_copy_of_an_array_field_is_its_own_copy():
    assert [BitHtml().copy_of(bit) for bit in _array().bits()] == [0, 1, 2, 3]


def test_neighbouring_bits_of_one_field_share_a_key_and_unclaimed_bits_have_none():
    bits = Register("R", 0x0, size=4, fields=[Field("A", 0, 2)]).bits()
    keys = [BitHtml().key(bit) for bit in bits]
    assert keys[0] is not None and keys[0] == keys[1]
    assert keys[2] is None and keys[3] is None


def test_the_copies_of_an_array_field_have_different_keys():
    keys = [BitHtml().key(bit) for bit in _array().bits()]
    assert len(set(keys)) == 4


def test_the_label_is_the_field_name_and_the_copy_for_an_array():
    plain = Register("R", 0x0, size=4, fields=[Field("A", 0, 2)]).bits()
    assert [BitHtml().label(bit) for bit in plain] == ["A", "A", "", ""]
    assert [BitHtml().label(bit) for bit in _array().bits()] == ["OD[0]", "OD[1]", "OD[2]", "OD[3]"]


def test_the_reset_is_the_bits_own_value_or_an_en_dash():
    with_reset = Register("R", 0x0, size=4, reset_value=0b0101).bits()
    assert [BitHtml().reset(bit) for bit in with_reset] == ["1", "0", "1", "0"]
    without = Register("R", 0x0, size=2).bits()
    assert [BitHtml().reset(bit) for bit in without] == [NO_VALUE, NO_VALUE]
