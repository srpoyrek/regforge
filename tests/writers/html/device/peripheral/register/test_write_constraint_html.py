"""WriteConstraintHtml: the notes on what may be written to a register or a field."""

from regforge.ir import WriteConstraint
from regforge.writers.html.device.peripheral.register.write_constraint import WriteConstraintHtml


def test_a_range_is_spelled_out():
    notes = WriteConstraintHtml().notes(WriteConstraint(minimum=1, maximum=5))
    assert notes == ["valid values 1 to 5"]


def test_listed_values_only():
    notes = WriteConstraintHtml().notes(WriteConstraint(use_enumerated_values=True))
    assert notes == ["only the listed values may be written"]


def test_write_as_read():
    notes = WriteConstraintHtml().notes(WriteConstraint(write_as_read=True))
    assert notes == ["must be written back as it was read"]


def test_every_limit_the_constraint_sets_is_a_note_in_this_order():
    constraint = WriteConstraint(
        write_as_read=True, use_enumerated_values=True, minimum=1, maximum=5
    )
    assert WriteConstraintHtml().notes(constraint) == [
        "valid values 1 to 5",
        "only the listed values may be written",
        "must be written back as it was read",
    ]


def test_half_a_range_is_not_a_range():
    assert WriteConstraintHtml().notes(WriteConstraint(minimum=1)) == []


def test_no_constraint_has_no_notes():
    assert WriteConstraintHtml().notes(None) == []
    assert WriteConstraintHtml().notes(WriteConstraint()) == []
