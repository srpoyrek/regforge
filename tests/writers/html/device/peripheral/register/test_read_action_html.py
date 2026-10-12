"""ReadActionHtml: what a read does, worded for a reader of the register."""

import pytest

from regforge.ir import ReadAction
from regforge.writers.html.device.peripheral.register.read_action import ReadActionHtml

TEXT = {
    ReadAction.CLEAR: "a read clears it",
    ReadAction.SET: "a read sets it",
    ReadAction.MODIFY: "a read modifies it",
    ReadAction.MODIFY_EXTERNAL: "a read changes it from outside, as a FIFO pop does",
}


def test_every_action_has_its_wording():
    assert set(TEXT) == set(ReadAction)


@pytest.mark.parametrize(("action", "text"), list(TEXT.items()))
def test_each_action_is_worded_and_told_not_to_be_read_for_a_look(action, text):
    assert ReadActionHtml().note(action) == f"{text}; do not read it just to look"


def test_no_action_is_no_note():
    assert ReadActionHtml().note(None) is None
