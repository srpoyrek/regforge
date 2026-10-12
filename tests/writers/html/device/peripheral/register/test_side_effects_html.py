"""SideEffectsHtml: what reading and writing a register or a field does, in one list of notes."""

from regforge.ir import Access, Field, ModifiedWriteValues, ReadAction, Register, WriteConstraint
from regforge.writers.html.device.peripheral.register.side_effects import SideEffectsHtml


def test_a_write_one_to_clear_field_is_told_not_to_read_modify_write():
    notes = SideEffectsHtml().notes(
        Field("OVF", 0, 1, modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR)
    )
    assert notes[0].startswith("writing 1 clears the bit")
    assert "read-modify-write" in notes[0]


def test_read_actions_write_once_and_constraints_are_all_covered():
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
    text = " | ".join(SideEffectsHtml().notes(field))
    assert "a read clears it" in text
    assert "written only once" in text
    assert "valid values 1 to 5" in text
    assert "only the listed values" in text
    assert "written back as it was read" in text


def test_the_notes_come_in_the_order_write_read_once_constraint():
    field = Field(
        "KEY",
        0,
        8,
        access=Access.WRITE_ONCE,
        modified_write_values=ModifiedWriteValues.CLEAR,
        read_action=ReadAction.CLEAR,
        write_constraint=WriteConstraint(minimum=1, maximum=5),
    )
    notes = SideEffectsHtml().notes(field)
    assert [note.split(";")[0] for note in notes] == [
        "any write clears it",
        "a read clears it",
        "can be written only once after reset",
        "valid values 1 to 5",
    ]


def test_a_register_says_it_in_the_same_words_as_a_field():
    register = Register(
        "R", 0x0, read_action=ReadAction.SET, modified_write_values=ModifiedWriteValues.SET
    )
    notes = SideEffectsHtml().notes(register)
    assert [note.split(";")[0] for note in notes] == ["any write sets it", "a read sets it"]


def test_an_element_with_nothing_special_has_no_notes():
    assert SideEffectsHtml().notes(Field("MODE", 0, 2)) == []
    assert SideEffectsHtml().notes(Register("R", 0x0)) == []
