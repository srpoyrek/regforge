"""BitMapHtml: the block of a register's bit map."""

from regforge.ir import Dim, Field, Register
from regforge.writers.html.bit_map import BitMapHtml
from regforge.writers.html.context import RenderContext


def _render(register):
    return BitMapHtml(RenderContext.default()).render(register)


def _ctrl():
    # 8 bits, reset 0x01: EN is bit 0, MODE is bits [2:1], bits 7..3 are unclaimed.
    return Register(
        "CTRL",
        0x0,
        size=8,
        reset_value=0x01,
        fields=[Field("EN", 0, 1), Field("MODE", 1, 2)],
    )


def test_adjacent_bits_of_one_field_are_one_cell():
    html = _render(_ctrl())
    assert '<td colspan="2" class="field">MODE</td>' in html
    assert '<td colspan="1" class="field">EN</td>' in html


def test_unclaimed_bits_are_one_reserved_cell():
    assert '<td colspan="5" class="reserved"></td>' in _render(_ctrl())


def test_the_bit_numbers_run_from_the_top_down():
    html = _render(_ctrl())
    assert (
        "<td>7</td><td>6</td><td>5</td><td>4</td><td>3</td><td>2</td><td>1</td><td>0</td>" in html
    )


def test_the_reset_row_shows_each_bit():
    html = _render(_ctrl())
    assert '<tr class="resets"><td>0</td><td>0</td><td>0</td><td>0</td>' in html
    assert "<td>1</td></tr>" in html


def test_a_register_with_no_reset_shows_en_dashes():
    register = Register("R", 0x0, size=4, fields=[Field("A", 0, 4)])
    assert "<td>–</td>" in _render(register)


def test_a_wide_register_wraps_onto_more_rows():
    html = _render(Register("WIDE", 0x0, size=64, fields=[Field("ALL", 0, 64)]))
    assert html.count('class="numbers"') == 2


def test_each_copy_of_an_array_field_is_its_own_cell():
    register = Register("ODR", 0x0, size=4, fields=[Field("OD", 0, 1, dim=Dim(4, 1, array=True))])
    html = _render(register)
    assert "OD[0]" in html and "OD[3]" in html


def test_an_unresolved_size_gives_no_map():
    assert _render(Register("R", 0x0)) == ""
