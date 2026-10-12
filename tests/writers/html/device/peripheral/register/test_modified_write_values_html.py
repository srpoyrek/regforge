"""ModifiedWriteValuesHtml: what a write does, worded for a reader of the register."""

import pytest

from regforge.ir import ModifiedWriteValues
from regforge.writers.html.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesHtml,
)

TEXT = {
    ModifiedWriteValues.ONE_TO_CLEAR: "writing 1 clears the bit",
    ModifiedWriteValues.ONE_TO_SET: "writing 1 sets the bit",
    ModifiedWriteValues.ONE_TO_TOGGLE: "writing 1 toggles the bit",
    ModifiedWriteValues.ZERO_TO_CLEAR: "writing 0 clears the bit",
    ModifiedWriteValues.ZERO_TO_SET: "writing 0 sets the bit",
    ModifiedWriteValues.ZERO_TO_TOGGLE: "writing 0 toggles the bit",
    ModifiedWriteValues.CLEAR: "any write clears it",
    ModifiedWriteValues.SET: "any write sets it",
    ModifiedWriteValues.MODIFY: "a write modifies it in a way the hardware decides",
}


def test_every_behaviour_has_its_wording():
    assert set(TEXT) == set(ModifiedWriteValues)


@pytest.mark.parametrize(("value", "text"), list(TEXT.items()))
def test_each_behaviour_starts_with_its_wording(value, text):
    note = ModifiedWriteValuesHtml().note(value)
    assert note is not None and note.startswith(text)


@pytest.mark.parametrize("value", [v for v in ModifiedWriteValues if v.acts_per_bit])
def test_a_per_bit_behaviour_warns_against_a_read_modify_write(value):
    note = ModifiedWriteValuesHtml().note(value)
    assert note is not None and "write the bits you mean directly" in note
    assert "read-modify-write" in note


@pytest.mark.parametrize("value", [v for v in ModifiedWriteValues if not v.acts_per_bit])
def test_a_whole_field_behaviour_needs_no_warning(value):
    note = ModifiedWriteValuesHtml().note(value)
    assert note is not None and "read-modify-write" not in note


def test_no_behaviour_is_no_note():
    assert ModifiedWriteValuesHtml().note(None) is None
