"""Bit view: the smallest element of a register and which field groups it."""

import pytest

from regforge.ir import Access, Dim, Field, Register
from regforge.ir.bit import bits, claims


def _ctrl() -> Register:
    # 8-bit register, reset 0x01: EN is bit 0, MODE is bits [2:1], bits 7..3 are unclaimed.
    return Register(
        "CTRL",
        0x0,
        size=8,
        reset_value=0x01,
        reset_mask=0xFF,
        fields=[
            Field("EN", 0, 1, access=Access.READ_WRITE),
            Field("MODE", 1, 2, access=Access.READ_ONLY),
        ],
    )


def test_a_register_has_one_bit_per_width_least_significant_first():
    assert [b.position for b in bits(_ctrl())] == list(range(8))


def test_a_field_claims_exactly_its_bit_range():
    names = [b.field.name if b.field else None for b in bits(_ctrl())]
    assert names == ["EN", "MODE", "MODE", None, None, None, None, None]


def test_a_claimed_bit_reaches_its_access_through_its_field():
    result = bits(_ctrl())
    assert result[0].field.access is Access.READ_WRITE
    assert result[1].field.access is Access.READ_ONLY


def test_reset_bit_is_read_from_the_register_reset_value():
    assert [b.reset for b in bits(_ctrl())] == [1, 0, 0, 0, 0, 0, 0, 0]


def test_reset_mask_leaves_a_bit_undefined():
    register = _ctrl()
    register.reset_mask = 0x0F  # only bits 3..0 have a defined reset
    assert [b.reset for b in bits(register)] == [1, 0, 0, 0, None, None, None, None]


def test_no_reset_value_means_no_reset_bits():
    register = _ctrl()
    register.reset_value = None
    assert all(b.reset is None for b in bits(register))


def test_array_field_claims_every_copy():
    # OD[%s]: four 1-bit copies two bits apart, so bits 0, 2, 4 and 6.
    register = Register("ODR", 0x0, size=8, fields=[Field("OD", 0, 1, dim=Dim(4, 2, array=True))])
    claimed = [b.field is not None for b in bits(register)]
    assert claimed == [True, False, True, False, True, False, True, False]


def test_field_bits_past_the_register_width_are_ignored():
    register = Register("R", 0x0, size=4, fields=[Field("WIDE", 2, 4)])  # bits 2..5, 2 and 3 exist
    assert [b.field is not None for b in bits(register)] == [False, False, True, True]


def test_first_declared_field_keeps_a_contested_bit():
    register = Register("R", 0x0, size=4, fields=[Field("A", 0, 2), Field("B", 1, 2)])
    assert bits(register)[1].field.name == "A"  # bit 1 is in both; A was declared first


def test_unresolved_size_is_refused():
    with pytest.raises(ValueError, match="CTRL"):
        bits(Register("CTRL", 0x0))


def test_is_claimed_says_whether_a_field_names_the_bit():
    claimed = [b.is_claimed for b in bits(_ctrl())]
    assert claimed == [True, True, True, False, False, False, False, False]


def test_claims_lists_every_field_on_a_bit_in_declaration_order():
    register = Register("R", 0x0, size=8, fields=[Field("A", 0, 2), Field("B", 1, 2)])
    found = claims(register)
    assert [f.name for f in found[0]] == ["A"]
    assert [f.name for f in found[1]] == ["A", "B"]  # bit 1 is in both
    assert [f.name for f in found[2]] == ["B"]
    assert 3 not in found


def test_claims_lists_a_field_array_once_per_position():
    register = Register("R", 0x0, size=8, fields=[Field("A", 0, 2, dim=Dim(2, 1, array=True))])
    found = claims(register)  # copy 0 is bits 0..1, copy 1 is bits 1..2: bit 1 is in both copies
    assert [f.name for f in found[1]] == ["A"]
    assert sorted(found) == [0, 1, 2]


def test_claims_includes_positions_past_the_register_width():
    register = Register("R", 0x0, size=4, fields=[Field("WIDE", 2, 4)])
    assert sorted(claims(register)) == [2, 3, 4, 5]  # the caller knows the width


def test_claims_names_the_very_field_object():
    field = Field("A", 0, 1)
    assert claims(Register("R", 0x0, size=1, fields=[field]))[0][0] is field
