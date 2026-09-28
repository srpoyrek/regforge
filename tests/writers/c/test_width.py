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
    assert "volatile uint8_t R;" in " ".join(_render_with_register(8).split())
    assert "volatile uint16_t R;" in " ".join(_render_with_register(16).split())
    assert "volatile uint32_t R;" in " ".join(_render_with_register(32).split())
    assert "volatile uint64_t R;" in " ".join(_render_with_register(64).split())


def test_bus_width_macro_emitted():
    output = CWriter().render(Device(name="Chip", bus_width=32))
    assert "#define CHIP_BUS_WIDTH 32" in output


def test_unmappable_size_is_refused():
    with pytest.raises(EmitError) as exc:
        _render_with_register(24)
    assert "24" in str(exc.value)
    assert "no C type mapping" in str(exc.value)
