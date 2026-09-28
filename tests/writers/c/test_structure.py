"""The generated file follows the fixed block order of docs/rules/structure.md."""

from regforge.writers.c import CWriter


def _ordered(text: str, markers: list[str]) -> None:
    positions = [text.index(marker) for marker in markers]  # every marker must exist
    out_of_order = [
        (markers[i], markers[i + 1])
        for i in range(len(markers) - 1)
        if positions[i] > positions[i + 1]
    ]
    assert not out_of_order, f"blocks out of order: {out_of_order}"


def test_top_of_file_blocks_come_in_the_fixed_order(golden_header_path):
    header = golden_header_path.read_text(encoding="utf-8")
    _ordered(
        header,
        [
            " * DemoMCU register definitions.",
            " * Source:  minimal.svd",
            " * MISRA C:2012: every required rule holds",  # a paragraph of the banner
            "#ifndef REGFORGE_DEMOMCU_H",
            "#include <stdint.h>",
            "/* Compiler compatibility */",
            "/* Device */",
            "#define DEMOMCU_SVD_VERSION",
            "#define DEMOMCU_SVD_SHA256",
            "#define DEMOMCU_ADDRESS_UNIT_BITS",
            "REGFORGE_STATIC_ASSERT(CHAR_BIT == DEMOMCU_ADDRESS_UNIT_BITS",
            "#define DEMOMCU_BUS_WIDTH",
            "/* CPU */",
            "#define DEMOMCU_CPU_CORE",
            "#define DEMOMCU_CPU_REVISION",
            "#define DEMOMCU_HAS_FPU",
            "#define DEMOMCU_HAS_MPU",
            "#define DEMOMCU_HAS_VTOR",
            "#define DEMOMCU_HAS_NVIC",
            '#error "DemoMCU is little-endian',
            '#error "Building with FPU codegen',
            "#define DEMOMCU_NUM_IRQS",
            "/* Interrupts */",
            "} dc_irqn_e;",
            "/* NVIC */",
            "#define DEMOMCU_NVIC_PRIO_BITS",
            "#define DEMOMCU_NVIC_PRIO_FIELD_MASK",
            "#define DEMOMCU_IRQ_PRIO_LEVELS",
            "REGFORGE_INLINE uint8_t dc_irq_prio(uint8_t priority)",
            "#define DEMOMCU_NVIC_IRQ_WORD_SHIFT",
            "#define DEMOMCU_NVIC_IPR_SLOT_MASK",
            "#define DC_NVIC_ISER ",
            "REGFORGE_INLINE void dc_nvic_enable(",
            "REGFORGE_INLINE uint8_t dc_nvic_get_priority(",
            "/* Peripherals */",
            "#endif /* REGFORGE_DEMOMCU_H */",
        ],
    )
    # The MISRA statement lives in the banner only, never loose between blocks.
    assert header.count("MISRA C:2012") == 1
    # Every NVIC fact sits in the NVIC block, none in the CPU block.
    cpu_block = header[header.index("/* CPU */") : header.index("/* Interrupts */")]
    assert "NVIC_PRIO" not in cpu_block and "irq_prio" not in cpu_block
    assert "NVIC_IRQ_WORD_SHIFT" not in cpu_block


def test_a_peripheral_section_comes_in_the_fixed_order(golden_header_path):
    header = golden_header_path.read_text(encoding="utf-8")
    section = header[header.index("/* TIM1 -- Advanced timer */") : header.index("/* TIM -- ")]
    _ordered(
        section,
        [
            "/* Layout constants:",
            "#define DC_TIM1_CR1_OFFSET",
            "#define DC_TIM1_SIZE",
            "typedef struct {",
            "} dc_tim1_t;",
            "REGFORGE_STATIC_ASSERT(offsetof(dc_tim1_t, CR1)",
            "REGFORGE_STATIC_ASSERT(sizeof(((dc_tim1_t *)0)->CCMR1)",
            "REGFORGE_STATIC_ASSERT(sizeof(dc_tim1_t) == DC_TIM1_SIZE",
            "/* TIM1 @ 0x40010000 */",
            "#define DC_TIM1_BASE",
            "static dc_tim1_t *const DC_TIM1",
            "#define DC_TIM1_UP_IRQ ",
            "#define DC_TIM1_CR1 (",
            "#define DC_TIM1_CCMR1_OUTPUT (",
            "#define DC_TIM1_CCMR1_OUTPUT_OC1M_Pos",
            "#define DC_TIM1_CCMR1_INPUT (",
        ],
    )


def test_cluster_types_precede_the_struct_that_uses_them(demo_device):
    output = CWriter().render(demo_device)
    _ordered(
        output,
        [
            "#define DC_DMA_CFG_OFFSET",
            "} dc_dma_ch_t;",
            "REGFORGE_STATIC_ASSERT(sizeof(dc_dma_ch_t) == DC_DMA_CH_STRIDE",
            "} dc_dma_stat_t;",
            "} dc_dma_t;",
            "REGFORGE_STATIC_ASSERT(sizeof(dc_dma_t) == DC_DMA_SIZE",
            "/* DMA @ 0x40016000 */",
            "#define DC_DMA_CH_CTRL(ch_index)",
        ],
    )


def test_blocks_with_nothing_to_hold_are_omitted():
    from regforge.ir import Device, Peripheral, Register

    output = CWriter().render(
        Device(
            name="Bare", peripherals=[Peripheral("P", 0x0, registers=[Register("R", 0, size=32)])]
        )
    )
    assert "/* CPU */" not in output and "/* Interrupts */" not in output
    assert "/* NVIC */" not in output and "#include <assert.h>" not in output
    assert "BARE_SVD_VERSION" not in output and "BARE_SVD_SHA256" not in output
    assert output.index("/* Device */") < output.index("#define BARE_ADDRESS_UNIT_BITS")
