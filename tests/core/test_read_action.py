"""ReadAction: the side effect of reading a register or field."""

from regforge.ir import ReadAction


def test_values_are_spelled_as_in_svd():
    assert [r.value for r in ReadAction] == ["clear", "set", "modify", "modifyExternal"]


def test_each_value_maps_back_to_its_member():
    assert ReadAction("clear") is ReadAction.CLEAR
    assert ReadAction("modifyExternal") is ReadAction.MODIFY_EXTERNAL


def test_clear_and_set_say_what_they_do():
    assert ReadAction.CLEAR.clears_value and not ReadAction.CLEAR.sets_value
    assert ReadAction.SET.sets_value and not ReadAction.SET.clears_value


def test_only_modify_external_comes_from_outside():
    assert [r for r in ReadAction if r.is_external] == [ReadAction.MODIFY_EXTERNAL]


def test_value_after_read_is_fixed_only_for_clear_and_set():
    assert ReadAction.CLEAR.value_after_read(4) == 0
    assert ReadAction.SET.value_after_read(4) == 0b1111
    assert ReadAction.MODIFY.value_after_read(4) is None
    assert ReadAction.MODIFY_EXTERNAL.value_after_read(4) is None
