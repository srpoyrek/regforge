"""EnumValueHtml: the block of one enumerated value."""

from regforge.ir import EnumeratedValue
from regforge.writers.html.context import RenderContext
from regforge.writers.html.enumerated_value import EnumValueHtml


def _render(value):
    return EnumValueHtml(RenderContext.default()).render(value)


def test_it_shows_the_number_the_name_and_the_description():
    html = _render(EnumeratedValue("OUT", 1, "Drive high"))
    assert "0x1" in html and "<b>OUT</b>" in html and "Drive high" in html


def test_it_leaves_out_a_missing_description():
    assert "&ndash;" not in _render(EnumeratedValue("OUT", 1))


def test_it_escapes_markup_in_the_text():
    html = _render(EnumeratedValue("A<B", 1, "x & <y>"))
    assert "A&lt;B" in html and "x &amp; &lt;y&gt;" in html
    assert "<y>" not in html


def test_a_catch_all_entry_reads_as_other_values():
    html = _render(EnumeratedValue("others", None, "Prohibited", is_default=True))
    assert "other values" in html and "<b>others</b>" in html and "Prohibited" in html


def test_a_pattern_is_spelled_in_binary_to_the_fields_width():
    pattern = EnumeratedValue("BUSY", 0b0100, dont_care=0b0011)
    html = EnumValueHtml(RenderContext.default()).render(pattern, 4)
    assert "0b01xx" in html
