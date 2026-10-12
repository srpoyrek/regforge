"""RegisterHtml: the block of one register."""

from regforge.ir import (
    Access,
    DataType,
    Field,
    ModifiedWriteValues,
    Peripheral,
    Protection,
    ReadAction,
    Register,
)
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device_facts import DeviceFacts
from regforge.writers.html.placement import PlacedRegister
from regforge.writers.html.register import RegisterHtml

FACTS = DeviceFacts(bus_width=32, address_digits=8, offset_digits=4)


def _renderer():
    return RegisterHtml(RenderContext.default())


def _ctrl():
    return Register(
        "CTRL",
        0x0,
        size=8,
        access=Access.READ_WRITE,
        reset_value=0x01,
        description="Control register",
        display_name="Control",
        fields=[Field("EN", 0, 1), Field("MODE", 1, 2)],
    )


def _placed(register=None, note=None):
    return PlacedRegister(register or _ctrl(), "CTRL", 0x10, note)


def _peripheral():
    return Peripheral("P", 0x40000000)


def test_it_shows_where_the_register_is():
    html = _renderer().render(_peripheral(), _placed(), FACTS)
    assert 'id="P.CTRL"' in html
    assert "0x0010" in html and "0x40000010" in html


def test_it_shows_size_access_reset_name_and_description():
    html = _renderer().render(_peripheral(), _placed(), FACTS)
    for text in ("8 bits", "RW", "0x01", "Control register", "<small>Control</small>"):
        assert text in html


def test_it_contains_the_bit_map_and_the_field_table():
    html = _renderer().render(_peripheral(), _placed(), FACTS)
    assert 'class="bitmap"' in html and "<th>Field</th>" in html
    table = html.split("<th>Field</th>")[1]
    assert table.index("<td>EN</td>") < table.index("<td>MODE</td>")  # declaration order


def test_it_says_which_registers_share_its_address():
    placed = PlacedRegister(_ctrl(), "CTRL", 0x10, None, ("CTRL_ALT",))
    html = _renderer().render(_peripheral(), placed, FACTS)
    assert "Shares this address with CTRL_ALT" in html


def test_it_notes_what_reading_and_writing_do():
    register = _ctrl()
    register.read_action = ReadAction.CLEAR
    register.modified_write_values = ModifiedWriteValues.ONE_TO_CLEAR
    register.protection = Protection.SECURE
    register.data_type = DataType.UINT32
    html = _renderer().render(_peripheral(), _placed(register), FACTS)
    for text in ("a read clears it", "writing 1 clears the bit", "secure access only", "uint32_t"):
        assert text in html


def test_the_data_type_is_in_the_header_line_and_not_a_note():
    register = _ctrl()
    register.data_type = DataType.INT32
    html = _renderer().render(_peripheral(), _placed(register), FACTS)
    assert '<span>Type <b class="mono">int32_t</b></span>' in html
    assert "accessed as" not in html


def test_a_register_without_a_data_type_has_no_type_in_its_header():
    html = _renderer().render(_peripheral(), _placed(), FACTS)
    assert "<span>Type" not in html


def test_a_write_once_access_is_written_out():
    register = _ctrl()
    register.access = Access.READ_WRITE_ONCE
    html = _renderer().render(_peripheral(), _placed(register), FACTS)
    assert "RW (write once)" in html and "can be written only once after reset" in html


def test_it_notes_the_cluster_array_it_sits_in():
    html = _renderer().render(_peripheral(), _placed(note="array of 4, 0x10 units apart"), FACTS)
    assert "array of 4, 0x10 units apart" in html


def test_the_row_links_to_the_block():
    row = _renderer().row(_peripheral(), _placed(), FACTS)
    assert 'href="#P.CTRL"' in row and "Control register" in row and "0x0010" in row


def test_offset_and_address_use_the_devices_digits():
    facts = DeviceFacts(bus_width=16, address_digits=4, offset_digits=2)
    html = _renderer().render(Peripheral("P", 0x2000), _placed(), facts)
    assert "0x10" in html and "0x2010" in html
    assert "0x10" in _renderer().row(Peripheral("P", 0x2000), _placed(), facts)
