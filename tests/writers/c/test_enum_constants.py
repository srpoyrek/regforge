"""Enumerated values in the C header: a constant for each plain number, none for the rest."""

from regforge.ir import Device, EnumeratedValue, EnumSet, Field, Peripheral, Register
from regforge.resolve import expand_dim, resolve_defaults, resolve_derived
from regforge.writers.c import CWriter


def _header(values):
    field = Field("MODE", 0, 3, enum_sets=[EnumSet(values)])
    register = Register("R", 0x0, size=32, fields=[field])
    device = Device(name="D", peripherals=[Peripheral("P", 0x40000000, registers=[register])])
    expand_dim(device)
    resolve_derived(device)
    resolve_defaults(device)
    return CWriter().render(device)


def test_a_plain_number_gets_a_constant():
    assert "_MODE_OFF (0U)" in _header([EnumeratedValue("OFF", 0), EnumeratedValue("ON", 1)])


def test_a_catch_all_entry_gets_no_constant():
    header = _header([EnumeratedValue("OFF", 0), EnumeratedValue("OTHERS", None, is_default=True)])
    assert "_MODE_OFF (0U)" in header
    assert "_MODE_OTHERS" not in header and "None" not in header


def test_a_pattern_gets_no_constant():
    header = _header([EnumeratedValue("OFF", 0), EnumeratedValue("BUSY", 0b100, dont_care=0b011)])
    assert "_MODE_OFF (0U)" in header and "_MODE_BUSY" not in header
