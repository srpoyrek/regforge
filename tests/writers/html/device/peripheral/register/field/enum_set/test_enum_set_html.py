"""EnumSetHtml: the block of one enumerated set."""

from regforge.ir import EnumeratedValue, EnumSet
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device.peripheral.register.field.enum_set.enum_set import EnumSetHtml


def _set():
    return EnumSet([EnumeratedValue("IN", 0), EnumeratedValue("OUT", 1)])


def test_it_lists_every_value_in_order():
    html = EnumSetHtml(RenderContext.default()).render(_set())
    assert html.index("IN") < html.index("OUT")
    assert html.count("<li>") == 2


def test_it_names_the_direction_when_given_one():
    html = EnumSetHtml(RenderContext.default()).render(_set(), "write")
    assert "write values" in html


def test_it_names_no_direction_by_default():
    assert "values</li>" not in EnumSetHtml(RenderContext.default()).render(_set())


def test_it_spells_patterns_to_the_given_width():
    pattern = EnumSet([EnumeratedValue("BUSY", 0b100, dont_care=0b011)])
    html = EnumSetHtml(RenderContext.default()).render(pattern, bit_width=3)
    assert "0b1xx" in html
