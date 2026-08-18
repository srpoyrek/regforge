"""C writer: addressUnitBits guard — refuse non-byte-addressable devices."""

import pytest

from regforge.ir import Device, Peripheral, Register
from regforge.writers.base import EmitError
from regforge.writers.c import CWriter


def test_byte_addressable_emits_byte_offsets():
    unit_bits = 8
    device = Device(
        name="Chip",
        address_unit_bits=unit_bits,
        peripherals=[
            Peripheral(
                name="P",
                base_address=0x1000,
                registers=[Register(name="R", address_offset=0x14)],
            )
        ],
    )
    output = CWriter().render(device)
    # At 8 bits/unit the conversion is a no-op: offsets stay as written.
    assert "#define P_BASE (0x00001000UL)" in output
    assert "P_BASE + 0x00000014UL" in output
    # The unit is emitted as a macro and self-checked against the compiler.
    # Tie the expected value to the input so the two can't drift apart.
    assert f"#define CHIP_ADDRESS_UNIT_BITS {unit_bits}" in output
    assert "#include <limits.h>" in output
    assert "_Static_assert(CHAR_BIT == CHIP_ADDRESS_UNIT_BITS" in output


def test_word_addressable_is_refused():
    with pytest.raises(EmitError) as exc:
        CWriter().render(Device(name="C2000", address_unit_bits=16))
    message = str(exc.value)
    assert "addressUnitBits=16" in message
    assert "not supported" in message
