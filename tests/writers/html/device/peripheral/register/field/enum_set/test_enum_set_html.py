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


def test_it_names_the_set_when_the_vendor_named_it():
    named = EnumSet([EnumeratedValue("IN", 0)], name="GPIO_MODE")
    assert "values (GPIO_MODE)" in EnumSetHtml(RenderContext.default()).render(named)


def test_it_names_the_set_beside_the_direction():
    named = EnumSet([EnumeratedValue("IN", 0)], name="GPIO_MODE")
    html = EnumSetHtml(RenderContext.default()).render(named, "read")
    assert "read values (GPIO_MODE)" in html


def test_it_falls_back_to_the_header_enum_name():
    named = EnumSet([EnumeratedValue("IN", 0)], header_enum_name="gpio_mode_t")
    assert "values (gpio_mode_t)" in EnumSetHtml(RenderContext.default()).render(named)


def test_the_set_name_wins_over_the_header_enum_name():
    named = EnumSet([EnumeratedValue("IN", 0)], name="GPIO_MODE", header_enum_name="gpio_mode_t")
    html = EnumSetHtml(RenderContext.default()).render(named)
    assert "(GPIO_MODE)" in html and "gpio_mode_t" not in html


def test_it_spells_patterns_to_the_given_width():
    pattern = EnumSet([EnumeratedValue("BUSY", 0b100, dont_care=0b011)])
    html = EnumSetHtml(RenderContext.default()).render(pattern, bit_width=3)
    assert "0b1xx" in html
