"""C writer: register base type keyed on size; guard on unmappable sizes."""

import pytest

from regforge.ir import Device, Peripheral, Register
from regforge.writers.base import EmitError
from regforge.writers.c import CWriter


def _render_with_register(size):
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="P",
                base_address=0,
                registers=[Register(name="R", address_offset=0, size=size)],
            )
        ],
    )
    return CWriter().render(device)


def test_type_selected_from_size():
    assert "volatile uint8_t *" in _render_with_register(8)
    assert "volatile uint16_t *" in _render_with_register(16)
    assert "volatile uint32_t *" in _render_with_register(32)
    assert "volatile uint64_t *" in _render_with_register(64)


def test_bus_width_macro_emitted():
    output = CWriter().render(Device(name="Chip", bus_width=32))
    assert "#define CHIP_BUS_WIDTH 32" in output


def test_unmappable_size_is_refused():
    with pytest.raises(EmitError) as exc:
        _render_with_register(24)
    assert "24" in str(exc.value)
    assert "no C type mapping" in str(exc.value)
