"""FieldHtml: the block of one field, a row of its register's field table."""

from regforge.ir import (
    Access,
    Dim,
    EnumeratedValue,
    EnumSet,
    EnumUsage,
    Field,
    ModifiedWriteValues,
    Register,
)
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device.peripheral.register.field.field import FieldHtml


def _render(register, field):
    return FieldHtml(RenderContext.default()).render(register, field)


def test_it_shows_bits_name_access_reset_and_description():
    mode = Field("MODE", 1, 2, description="Pin mode", access=Access.READ_WRITE)
    html = _render(Register("R", 0x0, size=8, reset_value=0b100), mode)
    for text in ("[2:1]", "MODE", "RW", "0x2", "Pin mode"):
        assert text in html


def test_it_lists_the_enumerated_values():
    mode = Field("MODE", 0, 2, enum_sets=[EnumSet([EnumeratedValue("IN", 0)])])
    assert "<b>IN</b>" in _render(Register("R", 0x0, size=8), mode)


def test_it_names_the_direction_when_a_field_has_a_read_and_a_write_set():
    both = [
        EnumSet([EnumeratedValue("IDLE", 0)], usage=EnumUsage.READ),
        EnumSet([EnumeratedValue("STOP", 0)], usage=EnumUsage.WRITE),
    ]
    html = _render(Register("R", 0x0, size=8), Field("CMD", 0, 1, enum_sets=both))
    assert "read values" in html and "write values" in html


def test_it_warns_about_a_write_one_to_clear_field():
    flag = Field("OVF", 0, 1, modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR)
    html = _render(Register("R", 0x0, size=8), flag)
    assert "writing 1 clears the bit" in html and 'class="notes"' in html


def test_it_says_when_a_field_is_one_copy_of_an_array():
    od = Field("OD", 0, 1, dim=Dim(4, 2, array=True))
    assert "array of 4, 0x2 bits apart" in _render(Register("R", 0x0, size=8), od)


def test_it_escapes_the_description():
    html = _render(Register("R", 0x0, size=8), Field("F", 0, 1, description="<script>x</script>"))
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_the_bits_label_spells_a_range_or_a_single_bit():
    renderer = FieldHtml(RenderContext.default())
    assert renderer.bits_label(Field("MODE", 1, 2)) == "[2:1]"
    assert renderer.bits_label(Field("EN", 3, 1)) == "[3]"
