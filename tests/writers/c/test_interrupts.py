"""C writer: the device-wide interrupt enum (CMSIS IRQn_Type equivalent).

The enum is emitted from every peripheral's ``<interrupt>`` lines, deduplicated,
sorted by vector number, with no trailing comma (C89-clean). The canonical
fixture stays interrupt-free until the fixture point; these tests drive
in-memory devices so the enum shape is pinned before it reaches the golden.
"""

import re

from regforge.ir import Device, Interrupt, Peripheral, Register
from regforge.resolve import resolve_defaults, resolve_derived
from regforge.writers.c import CWriter


def _render(*peripherals: Peripheral, prefix: str | None = "DC_") -> str:
    device = Device(name="Chip", header_prefix=prefix, peripherals=list(peripherals))
    resolve_defaults(device)
    resolve_derived(device)
    return CWriter().render(device)


def test_enum_lists_interrupts_sorted_by_value():
    output = _render(
        Peripheral(
            name="UART0",
            base_address=0x4000,
            registers=[Register("DR", 0x0, size=32)],
            interrupts=[Interrupt("UART0", 20)],
        ),
        Peripheral(
            name="DMA",
            base_address=0x5000,
            registers=[Register("CR", 0x0, size=32)],
            interrupts=[
                Interrupt("DMA_CH0", 10, description="DMA channel 0"),
                Interrupt("DMA_ERR", 11),
            ],
        ),
    )
    assert "} dc_irqn_e;" in output  # enum types end in _e, not _t
    # Sorted by vector number: the DMA lines (10, 11) precede UART0 (20).
    enum_body = output.split("typedef enum {", 1)[1].split("} dc_irqn_e;", 1)[0]
    members = [line.strip() for line in enum_body.splitlines() if "_IRQn" in line]
    assert members == [
        "DC_DMA_CH0_IRQn = 10,  /* DMA channel 0 */",
        "DC_DMA_ERR_IRQn = 11,",
        "DC_UART0_IRQn   = 20",
    ]


def test_enum_has_no_trailing_comma():
    # C89 under -pedantic-errors rejects a trailing comma; the last member has none.
    output = _render(
        Peripheral(
            name="UART0",
            base_address=0x4000,
            registers=[Register("DR", 0x0, size=32)],
            interrupts=[Interrupt("UART0", 20)],
        ),
    )
    last_member = output.split("} dc_irqn_e;", 1)[0].rstrip().splitlines()[-1]
    assert last_member.strip() == "DC_UART0_IRQn = 20"  # no comma


def test_shared_vector_appears_once():
    # Two peripherals reference the same interrupt name/value (a shared vector);
    # the enum lists it a single time.
    output = _render(
        Peripheral(
            name="TIM1",
            base_address=0x0,
            registers=[Register("CR1", 0x0, size=32)],
            interrupts=[Interrupt("TIM1_BRK_TIM9", 24)],
        ),
        Peripheral(
            name="TIM9",
            base_address=0x400,
            registers=[Register("CR1", 0x0, size=32)],
            interrupts=[Interrupt("TIM1_BRK_TIM9", 24)],
        ),
    )
    # Scope to the enum body: the per-instance _IRQ aliases (I2) also reference
    # the member, so count the enumerator only where it is *defined*.
    enum_body = output.split("typedef enum {", 1)[1].split("} dc_irqn_e;", 1)[0]
    assert len(re.findall(r"DC_TIM1_BRK_TIM9_IRQn", enum_body)) == 1


def test_no_interrupts_emits_no_enum():
    output = _render(
        Peripheral(name="GPIOA", base_address=0x0, registers=[Register("MODER", 0x0, size=32)]),
    )
    assert "irqn_e" not in output
    assert "typedef enum" not in output


def test_per_instance_irq_link_aliases_enum_member():
    output = _render(
        Peripheral(
            name="UART0",
            base_address=0x4000,
            registers=[Register("DR", 0x0, size=32)],
            interrupts=[Interrupt("UART0", 20, description="UART0 global interrupt")],
        ),
    )
    # The instance's IRQ handle sits next to its BASE and aliases the enum member.
    assert "#define DC_UART0_IRQ DC_UART0_IRQn" in output
    uart_block = output.split("#define DC_UART0_BASE", 1)[1]
    assert uart_block.index("DC_UART0_IRQ ") < uart_block.index("UART0_DR")  # adjacent, before regs


def test_multi_irq_peripheral_emits_role_named_links():
    output = _render(
        Peripheral(
            name="DMA",
            base_address=0x5000,
            registers=[Register("CR", 0x0, size=32)],
            interrupts=[Interrupt("DMA_CH0", 10), Interrupt("DMA_ERR", 11)],
        ),
    )
    assert "#define DC_DMA_CH0_IRQ DC_DMA_CH0_IRQn" in output
    assert "#define DC_DMA_ERR_IRQ DC_DMA_ERR_IRQn" in output


def test_peripheral_without_interrupt_emits_no_link():
    output = _render(
        Peripheral(name="GPIOA", base_address=0x0, registers=[Register("MODER", 0x0, size=32)]),
    )
    assert "_IRQ " not in output


def test_empty_prefix_names_the_enum_type():
    output = _render(
        Peripheral(
            name="UART0",
            base_address=0x4000,
            registers=[Register("DR", 0x0, size=32)],
            interrupts=[Interrupt("UART0", 20)],
        ),
        prefix=None,
    )
    assert "} irqn_e;" in output
    assert "UART0_IRQn = 20" in output
