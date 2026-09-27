"""C writer: register, field and peripheral arrays.

A ``NAME[%s]`` register or field is one array member with indexed macros; a
``NAME%s`` template is ordinary copies, spelled as if written out by hand.
"""

import re

import pytest

from regforge.ir import Device, Dim, EnumeratedValue, Field, Peripheral, Register
from regforge.resolve import expand_dim, resolve_defaults, resolve_derived
from regforge.writers.base import EmitError
from regforge.writers.c import CWriter


def _squash(text: str) -> str:
    return re.sub(r" +", " ", text)


def _render(*peripherals: Peripheral, prefix: str = "DC_") -> str:
    device = Device(name="Chip", header_prefix=prefix, peripherals=list(peripherals))
    expand_dim(device)
    resolve_derived(device)
    resolve_defaults(device)
    return CWriter().render(device)


def test_array_register_is_one_member_with_count_and_indexed_macro():
    output = _render(
        Peripheral(
            "PWM",
            0x40015000,
            registers=[
                Register("CTRL", 0x0, size=32),
                Register(
                    "CC[%s]",
                    0x10,
                    size=32,
                    dim=Dim(4, 4),
                    reset_value=0,
                    description="Capture/compare",
                    fields=[Field("V", 0, 16)],
                ),
            ],
        )
    )
    squashed = _squash(output)
    assert "volatile uint32_t CC[4];" in squashed
    assert (
        'REGFORGE_STATIC_ASSERT(offsetof(dc_pwm_t, CC) == 0x10, DC_PWM_CC_offset, "PWM.CC offset");'
        in output
    )
    assert "/* PWM.CC[4] - Capture/compare */" in output
    assert "#define DC_PWM_CC_COUNT (4U)" in output
    assert (
        "#define DC_PWM_CC(i) (*(volatile uint32_t *)"
        "(DC_PWM_BASE + 0x00000010UL + (i) * 0x00000004UL))" in output
    )
    assert output.count("DC_PWM_CC_RESET_VALUE") == 1  # once per array, not per element
    assert "#define DC_PWM_CC_V_Pos (0U)" in output  # fields once, index-free


def test_separate_copies_are_ordinary_registers():
    output = _render(
        Peripheral("PWM", 0x0, registers=[Register("DT%s", 0x20, size=32, dim=Dim(2, 8))])
    )
    squashed = _squash(output)
    assert "volatile uint32_t DT0;" in squashed and "volatile uint32_t DT1;" in squashed
    assert "uint8_t RESERVED1[4];" in squashed  # the hole between the copies is padding
    assert "#define DC_PWM_DT0 (*(volatile uint32_t *)(DC_PWM_BASE + 0x00000020UL))" in output
    assert "#define DC_PWM_DT1 (*(volatile uint32_t *)(DC_PWM_BASE + 0x00000028UL))" in output
    assert "_COUNT" not in output


def test_non_contiguous_array_is_refused_by_name():
    with pytest.raises(EmitError, match=r"P\.DATA\[4\].*not a packed array"):
        _render(
            Peripheral("P", 0x0, registers=[Register("DATA[%s]", 0x10, size=32, dim=Dim(4, 8))])
        )


def test_field_array_emits_indexed_position_and_mask():
    output = _render(
        Peripheral(
            "GPIOA",
            0x0,
            registers=[
                Register(
                    "ODR",
                    0x0,
                    size=32,
                    fields=[
                        Field("OD[%s]", 0, 1, dim=Dim(16, 1), enums=[EnumeratedValue("LOW", 0)])
                    ],
                )
            ],
        )
    )
    assert "#define DC_GPIOA_ODR_OD_COUNT (16U)" in output
    assert "#define DC_GPIOA_ODR_OD_Pos(i) (0U + (i) * 1U)" in output
    assert "#define DC_GPIOA_ODR_OD_Msk(i) (0x00000001UL << ((i) * 1U))" in output
    assert "#define DC_GPIOA_ODR_OD_LOW (0U)" in output  # enumerated values once


def test_field_copies_are_ordinary_fields():
    output = _render(
        Peripheral(
            "GPIOA",
            0x0,
            registers=[
                Register("MODER", 0x0, size=32, fields=[Field("MODE%s", 0, 2, dim=Dim(2, 2))])
            ],
        )
    )
    assert "#define DC_GPIOA_MODER_MODE0_Pos (0U)" in output
    assert "#define DC_GPIOA_MODER_MODE1_Pos (2U)" in output
    assert "#define DC_GPIOA_MODER_MODE1_Msk (0x0000000CUL)" in output


def test_peripheral_array_is_one_type_with_n_instances():
    output = _render(
        Peripheral(
            "UART%s", 0x40000000, dim=Dim(4, 0x400), registers=[Register("DR", 0x0, size=32)]
        )
    )
    assert output.count("} dc_uart_t;") == 1
    assert "(family: UART0, UART1, UART2, UART3)" in output
    for index in range(4):
        base = 0x40000000 + index * 0x400
        assert f"#define DC_UART{index}_BASE (0x{base:08X}UL)" in output
        assert f"typedef dc_uart_t dc_uart{index}_t;" in output
        assert (
            f"static dc_uart_t *const DC_UART{index} = (dc_uart_t *)DC_UART{index}_BASE;" in output
        )


def test_unexpanded_template_is_refused():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral("UART%s", 0x0, dim=Dim(2, 0x400), registers=[Register("DR", 0x0, size=32)])
        ],
    )
    with pytest.raises(EmitError, match="%s placeholder"):
        CWriter().render(device)
