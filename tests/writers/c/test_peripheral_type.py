"""C writer, Layer 2 (name + baseAddress): a distinct type + typed instance.

Each peripheral becomes its own C struct type with a typed handle at its base,
so passing the wrong peripheral to a function is a compile error -- and the
handle is a real symbol, not a cast-macro like CMSIS emits.
"""

import pytest

from regforge.ir import Device, Peripheral, Register
from regforge.writers.base import EmitError
from regforge.writers.c import CWriter


def test_emits_struct_type_and_typed_instance(demo_device):
    output = CWriter().render(demo_device)
    # A distinct struct type per peripheral; the _t name is fully lower-case.
    assert "} dc_gpioa_t;" in output
    assert "volatile uint32_t MODER;" in output
    assert "volatile uint32_t ODR;" in output
    # Reserved padding fills 0x04..0x14 so ODR sits at its true offset.
    assert "uint8_t RESERVED0[16];" in output
    # The instance is a typed, non-redefinable symbol -- not a cast-macro.
    assert (
        "REGFORGE_MAYBE_UNUSED static dc_gpioa_t *const DC_GPIOA = (dc_gpioa_t *)DC_GPIOA_BASE;"
        in output
    )
    # The base-address define is kept for constant-expression contexts.
    assert "#define DC_GPIOA_BASE" in output


def test_distinct_type_per_peripheral():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="GPIOA",
                base_address=0x4000,
                registers=[Register(name="MODER", address_offset=0, size=32)],
            ),
            Peripheral(
                name="TIM1",
                base_address=0x5000,
                registers=[Register(name="CR1", address_offset=0, size=32)],
            ),
        ],
    )
    output = CWriter().render(device)
    # Two peripherals -> two distinct C types, so mixing them cannot compile.
    assert "} gpioa_t;" in output
    assert "} tim1_t;" in output
    assert "static gpioa_t *const GPIOA " in output
    assert "static tim1_t *const TIM1 " in output


def test_overlapping_registers_are_refused():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="P",
                base_address=0x0,
                registers=[
                    Register(name="A", address_offset=0x0, size=32),  # 0x0..0x4
                    Register(name="B", address_offset=0x2, size=32),  # overlaps A
                ],
            )
        ],
    )
    with pytest.raises(EmitError) as exc:
        CWriter().render(device)
    assert "overlaps" in str(exc.value)
