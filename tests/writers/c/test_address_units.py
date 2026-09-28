"""C writer: addressUnitBits guard — refuse non-byte-addressable devices."""

import pytest

from regforge.ir import Device, Peripheral, Register
from regforge.layout import units_to_bytes
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
                registers=[Register(name="R", address_offset=0x14, size=32)],
            )
        ],
    )
    output = CWriter().render(device)
    # At 8 bits/unit the conversion is a no-op: offsets stay as written.
    assert "#define P_BASE (0x00001000UL)" in output
    squashed = " ".join(output.split())  # the constants block is column-aligned
    assert "P_R_OFFSET (0x00000014UL)" in squashed  # the offset, once, as a named constant
    assert "#define P_R (P->R)" in output  # the accessor goes through the typed instance
    # The unit is emitted as a macro and self-checked against the compiler.
    # Tie the expected value to the input so the two can't drift apart.
    assert f"#define CHIP_ADDRESS_UNIT_BITS {unit_bits}" in output
    assert "#include <limits.h>" in output
    assert "REGFORGE_STATIC_ASSERT(cond, tag, msg)" in output  # macro defined
    assert "REGFORGE_STATIC_ASSERT(CHAR_BIT == CHIP_ADDRESS_UNIT_BITS" in output


def test_word_addressable_is_refused():
    with pytest.raises(EmitError) as exc:
        CWriter().render(Device(name="C2000", address_unit_bits=16))
    message = str(exc.value)
    assert "addressUnitBits=16" in message
    assert "not supported" in message


def test_units_to_bytes_is_one_word_addressable_ready_conversion():
    # 8 bits/unit (byte-addressable): a no-op -- base and offsets stay as written.
    assert units_to_bytes(0x14, 8) == 0x14
    assert units_to_bytes(0x40020000, 8) == 0x40020000
    # 16 bits/unit (word-addressable, e.g. TI C2000): units become bytes. The C
    # emitter refuses 16 today, but the math a future emitter will reuse -- the
    # same helper that feeds _BASE, the register offsets, and the struct layout --
    # is already correct.
    assert units_to_bytes(0x14, 16) == 0x28
    assert units_to_bytes(1, 32) == 4
