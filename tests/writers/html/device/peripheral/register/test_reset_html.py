"""ResetHtml: the reset value of a register, its mask, and the share of it a field holds."""

from regforge.ir import Field, Register
from regforge.writers.html.device.peripheral.register.reset import ResetHtml
from regforge.writers.html.wording import NO_VALUE


def test_the_register_value_is_hex_sized_to_the_register():
    assert ResetHtml().register_value(Register("R", 0x0, size=8, reset_value=1)) == "0x01"
    assert ResetHtml().register_value(Register("R", 0x0, size=32, reset_value=0)) == "0x00000000"


def test_a_register_with_no_reset_value_or_size_is_an_en_dash():
    assert ResetHtml().register_value(Register("R", 0x0, size=32)) == NO_VALUE
    assert ResetHtml().register_value(Register("R", 0x0, reset_value=1)) == NO_VALUE


def test_the_mask_is_hex_sized_to_the_register_and_absent_without_one():
    assert ResetHtml().register_mask(Register("R", 0x0, size=8, reset_mask=0xF0)) == "0xF0"
    assert ResetHtml().register_mask(Register("R", 0x0, size=8)) is None
    assert ResetHtml().register_mask(Register("R", 0x0, reset_mask=0xF0)) is None


def test_a_field_reads_its_share_out_of_the_registers_reset():
    mode = Field("MODE", 1, 2)
    assert ResetHtml().field_value(Register("R", 0x0, size=8, reset_value=0b100), mode) == "0x2"
    assert ResetHtml().field_value(Register("R", 0x0, size=8), mode) == NO_VALUE


def test_a_field_is_undefined_when_the_mask_does_not_cover_it():
    register = Register("R", 0x0, size=8, reset_value=0b110, reset_mask=0b010)
    assert ResetHtml().field_value(register, Field("MODE", 1, 2)) == NO_VALUE
