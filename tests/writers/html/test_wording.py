"""Wording: the number formats and sentences every HTML renderer shares."""

from regforge.ir import (
    Access,
    Dim,
    DimOrigin,
    Field,
    ModifiedWriteValues,
    ReadAction,
    Register,
    WriteConstraint,
)
from regforge.writers.html.wording import (
    NO_VALUE,
    access_label,
    anchor,
    array_note,
    bits_label,
    effects,
    field_reset,
    hex_,
    hex_digits,
    register_reset,
    register_reset_mask,
    short,
)


def test_hex_is_zero_padded_upper_case():
    assert hex_(255, 4) == "0x00FF"


def test_hex_digits_round_up_to_a_whole_digit():
    assert [hex_digits(b) for b in (0, 1, 4, 5, 8, 32, 64)] == [0, 1, 1, 2, 2, 8, 16]


def test_anchor_joins_parts_and_removes_spaces():
    assert anchor("P", "CH.CTRL") == "P.CH.CTRL"
    assert anchor("a b") == "a_b"


def test_short_takes_the_first_line_and_cuts_a_long_one():
    assert short(None) == "" and short("   ") == ""
    assert short("first line\nsecond line") == "first line"
    cut = short("x" * 200, limit=20)
    assert len(cut) == 20 and cut.endswith("…")


def test_access_label_is_short_and_an_en_dash_when_unresolved():
    assert access_label(Access.READ_WRITE_ONCE) == "RW (write once)"
    assert access_label(Access.READ_ONLY) == "RO"
    assert access_label(None) == NO_VALUE


def test_array_note_tells_a_kept_array_from_an_unrolled_copy():
    kept = Register("A", 0x0, dim=Dim(4, 4, array=True))
    copy = Register("D0", 0x0, origin=DimOrigin("D%s", Dim(2, 4), 0, "0"))
    assert array_note(kept, "units") == "array of 4, 0x4 units apart"
    assert array_note(copy, "units") == "copy 1 of 2 of D%s"
    assert array_note(Register("R", 0x0), "units") is None


def test_effects_say_not_to_read_modify_write_a_write_one_to_clear_field():
    notes = effects(Field("OVF", 0, 1, modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR))
    assert notes[0].startswith("writing 1 clears the bit")
    assert "read-modify-write" in notes[0]


def test_effects_cover_read_actions_write_once_and_constraints():
    field = Field(
        "KEY",
        0,
        8,
        access=Access.WRITE_ONCE,
        read_action=ReadAction.CLEAR,
        write_constraint=WriteConstraint(
            write_as_read=True, use_enumerated_values=True, minimum=1, maximum=5
        ),
    )
    text = " | ".join(effects(field))
    assert "a read clears it" in text
    assert "written only once" in text
    assert "valid values 1 to 5" in text
    assert "only the listed values" in text
    assert "written back as it was read" in text


def test_a_field_with_nothing_special_has_no_effects():
    assert effects(Field("MODE", 0, 2)) == []


def test_register_reset_is_hex_sized_to_the_register():
    assert register_reset(Register("R", 0x0, size=8, reset_value=1)) == "0x01"
    assert register_reset(Register("R", 0x0, size=32, reset_value=0)) == "0x00000000"
    assert register_reset(Register("R", 0x0, size=32)) == NO_VALUE
    assert register_reset_mask(Register("R", 0x0, size=8, reset_mask=0xF0)) == "0xF0"
    assert register_reset_mask(Register("R", 0x0, size=8)) is None


def test_field_reset_reads_the_field_out_of_the_registers_reset():
    mode = Field("MODE", 1, 2)
    assert field_reset(Register("R", 0x0, size=8, reset_value=0b100), mode) == "0x2"
    assert field_reset(Register("R", 0x0, size=8), mode) == NO_VALUE


def test_field_reset_is_undefined_when_the_mask_does_not_cover_the_field():
    register = Register("R", 0x0, size=8, reset_value=0b110, reset_mask=0b010)
    assert field_reset(register, Field("MODE", 1, 2)) == NO_VALUE


def test_bits_label_spells_a_range_or_a_single_bit():
    assert bits_label(Field("MODE", 1, 2)) == "[2:1]"
    assert bits_label(Field("EN", 3, 1)) == "[3]"
