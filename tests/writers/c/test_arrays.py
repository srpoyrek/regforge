"""C writer: register, field and peripheral arrays.

A ``NAME[%s]`` register or field is one array member with indexed macros; a
``NAME%s`` template is ordinary copies, spelled as if written out by hand.
"""

import re

import pytest

from regforge.ir import (
    AddressBlock,
    Cluster,
    Device,
    Dim,
    EnumeratedValue,
    Field,
    Peripheral,
    Register,
)
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
    assert "volatile uint32_t CC[DC_PWM_CC_COUNT];" in squashed  # the bound is the constant
    assert (
        "REGFORGE_STATIC_ASSERT(offsetof(dc_pwm_t, CC) == DC_PWM_CC_OFFSET, "
        'DC_PWM_CC_OFFSET_CHECK, "PWM.CC offset");' in output
    )
    assert "/* PWM.CC[4] - Capture/compare */" in output
    assert "#define DC_PWM_CC_COUNT (4U)" in squashed  # the family constant, aligned
    assert (  # the member holds exactly its elements
        "REGFORGE_STATIC_ASSERT(sizeof(((dc_pwm_t *)0)->CC) == "
        'DC_PWM_CC_COUNT * DC_PWM_CC_STRIDE, DC_PWM_CC_ARRAY_CHECK, "PWM.CC array size");' in output
    )
    assert "#define DC_PWM_CC(cc_index) (DC_PWM->CC[(cc_index)])" in output  # via the type
    assert (  # the last element is placed outright, so CC[k] is stated, not inferred
        "REGFORGE_STATIC_ASSERT(offsetof(dc_pwm_t, CC) + (DC_PWM_CC_COUNT - 1U) * "
        "sizeof(((dc_pwm_t *)0)->CC[0]) == DC_PWM_CC_OFFSET + (DC_PWM_CC_COUNT - 1U) * "
        'DC_PWM_CC_STRIDE, DC_PWM_CC_LAST_CHECK, "PWM.CC[3] offset via the struct");' in output
    )
    assert output.count("DC_PWM_CC_RESET_VALUE") == 1  # once per array, not per element
    assert "#define DC_PWM_CC_V_Pos (0U)" in output  # fields once, index-free


def test_separate_copies_are_ordinary_registers():
    output = _render(
        Peripheral("PWM", 0x0, registers=[Register("DT%s", 0x20, size=32, dim=Dim(2, 8))])
    )
    squashed = _squash(output)
    assert "volatile uint32_t DT0;" in squashed and "volatile uint32_t DT1;" in squashed
    assert "uint8_t RESERVED1[DC_PWM_RESERVED1_SIZE];" in squashed  # the hole between copies
    assert "#define DC_PWM_RESERVED1_SIZE (0x00000004UL)" in squashed
    assert "#define DC_PWM_DT0 (DC_PWM->DT0)" in output
    assert "#define DC_PWM_DT1 (DC_PWM->DT1)" in output
    assert "_COUNT" not in output


def test_overlapping_array_elements_are_refused_by_name():
    with pytest.raises(EmitError, match=r"P\.DATA\[4\].*elements overlap"):
        _render(
            Peripheral("P", 0x0, registers=[Register("DATA[%s]", 0x10, size=32, dim=Dim(4, 2))])
        )


def test_unpacked_array_is_flat_members_with_an_indexed_macro():
    output = _render(
        Peripheral(
            "PWMX",
            0x0,
            address_blocks=[AddressBlock(0, 0x20, "registers")],
            registers=[Register("CH[%s]", 0x0, size=32, dim=Dim(4, 8))],
        )
    )
    squashed = _squash(output)
    assert "CH[DC_PWMX_CH_COUNT];" not in squashed  # a C array cannot hold the holes
    assert "volatile uint32_t CH0;" in squashed and "volatile uint32_t CH3;" in squashed
    assert "uint8_t RESERVED0[DC_PWMX_RESERVED0_SIZE];" in squashed  # the hole after CH0
    assert (
        "REGFORGE_STATIC_ASSERT(offsetof(dc_pwmx_t, CH1) == "
        "DC_PWMX_CH_OFFSET + 1U * DC_PWMX_CH_STRIDE, DC_PWMX_CH1_OFFSET_CHECK, "
        '"PWMX.CH1 offset");' in output
    )
    assert (
        "#define DC_PWMX_CH_COUNT (4U)" in squashed
    )  # the indexed macro still steps by the stride
    assert (
        "#define DC_PWMX_CH(ch_index) (*(volatile uint32_t *)"
        "(DC_PWMX_BASE + DC_PWMX_CH_OFFSET + (ch_index) * DC_PWMX_CH_STRIDE))" in output
    )


def test_field_past_the_register_width_is_refused():
    with pytest.raises(EmitError, match=r"P\.R\.F: bits 30\.\.33 run past the 32-bit"):
        _render(
            Peripheral(
                "P", 0x0, registers=[Register("R", 0x0, size=32, fields=[Field("F", 30, 4)])]
            )
        )


def test_address_past_32_bits_is_refused():
    with pytest.raises(EmitError, match="HI: reaches 0x100000004, past the 32-bit"):
        _render(Peripheral("HI", 0xFFFFFFF0, registers=[Register("R", 0x10, size=32)]))


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
    assert "#define DC_GPIOA_ODR_OD_Pos(od_index) (0U + (od_index) * 1U)" in output
    assert "#define DC_GPIOA_ODR_OD_Msk(od_index) (0x00000001UL << ((od_index) * 1U))" in output
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
        assert f"#define DC_UART{index} ((dc_uart_t *)(uintptr_t)DC_UART{index}_BASE)" in output


def test_unexpanded_template_is_refused():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral("UART%s", 0x0, dim=Dim(2, 0x400), registers=[Register("DR", 0x0, size=32)])
        ],
    )
    with pytest.raises(EmitError, match="%s placeholder"):
        CWriter().render(device)


def test_dim_array_index_names_become_index_constants():
    names = [EnumeratedValue("RX", 0, "receive"), EnumeratedValue("TX", 1)]
    output = _render(
        Peripheral(
            "DMA",
            0x0,
            registers=[Register("BUF[%s]", 0x0, size=32, dim=Dim(2, 4, array_index=names))],
            clusters=[
                Cluster(
                    "CH[%s]",
                    0x10,
                    dim=Dim(2, 0x10, array_index=names),
                    registers=[Register("CTRL", 0x0, size=32)],
                )
            ],
        )
    )
    assert "/* DMA.BUF[2] index names (dimArrayIndex) */" in output
    assert "#define DC_DMA_BUF_RX (0U)  /* receive */" in output
    assert "#define DC_DMA_BUF_TX (1U)" in output
    assert "/* DMA.CH[2] index names (dimArrayIndex) */" in output
    assert "#define DC_DMA_CH_TX (1U)" in output
    assert "#define DC_DMA_CH_CTRL(ch_index)" in output  # the accessors are untouched
