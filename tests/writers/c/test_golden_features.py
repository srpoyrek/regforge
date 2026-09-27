"""The canonical fixture (minimal.svd) exercises features end-to-end.

test_golden diffs the whole output byte-for-byte; these name the specific
features the enriched fixture is there to demonstrate, so a regression points
at the feature rather than "the golden changed".
"""

import re

from regforge.writers.c import CWriter


def _squash(text: str) -> str:
    return re.sub(r" +", " ", text)


def test_fixture_honors_header_prefix(demo_device):
    assert demo_device.header_prefix == "DC_"
    output = CWriter().render(demo_device)
    assert "#define DC_GPIOA_BASE" in output  # hardware identifiers prefixed
    assert "#define DEMOMCU_BUS_WIDTH" in output  # metadata not double-prefixed


def test_fixture_emits_reset_mask_only_where_partial(demo_device):
    output = CWriter().render(demo_device)
    assert "#define DC_GPIOA_ODR_RESET_MASK (0x0000FFFFUL)" in output  # ODR: partial
    assert "DC_GPIOA_MODER_RESET_MASK" not in output  # MODER: no mask -> suppressed


def test_fixture_marks_read_only_register_const(demo_device):
    output = CWriter().render(demo_device)
    # IDR is <access>read-only</access>: the struct member and flat macro are const,
    # so writing it (IDR = x) is a compile error -- while ODR (read-write) is not.
    assert "volatile const uint32_t IDR;" in output
    assert "#define DC_GPIOA_IDR (*(volatile const uint32_t *)" in output
    assert "volatile const uint32_t ODR;" not in output  # ODR stays writable


def test_fixture_derived_family_shares_one_type(demo_device):
    output = CWriter().render(demo_device)
    # UART0 + UART1 (derivedFrom, groupName "UART") -> ONE dc_uart_t, two instances.
    assert output.count("} dc_uart_t;") == 1
    assert "static dc_uart_t *const DC_UART0" in output
    assert "static dc_uart_t *const DC_UART1" in output
    assert "#define DC_UART1_DR" in output  # UART1 inherited UART0's registers


def test_fixture_groupname_only_family_merges(demo_device):
    output = CWriter().render(demo_device)
    # SPI0/SPI1 share groupName "SPI" (no derivedFrom), identical layout -> one type.
    assert output.count("} dc_spi_t;") == 1
    assert "static dc_spi_t *const DC_SPI0" in output
    assert "static dc_spi_t *const DC_SPI1" in output


def test_lint_fixture_divergent_groupname_is_split(lint_demo_device):
    output = CWriter().render(lint_demo_device)
    # TIMER_ADV (has RCR) diverges from TMR0 under groupName "TMR": the largest
    # identical subgroup keeps the name and the outlier splits off, so
    # LD_TMR0->RCR is a compile error rather than a reserved-address write.
    assert output.count("} ld_tmr_t;") == 1
    assert output.count("} ld_timer_adv_t;") == 1
    assert "static ld_tmr_t *const LD_TMR0" in output  # majority keeps the name
    assert "static ld_timer_adv_t *const LD_TIMER_ADV" in output  # outlier, own type
    assert "split 2 ways" in output  # the split is recorded as a note
    assert "first differs at RCR" in output


def test_lint_fixture_namesake_keeps_the_plain_group_name(lint_demo_device):
    output = CWriter().render(lint_demo_device)
    # FPU and FPU_CPACR share groupName "FPU" with different layouts. The
    # peripheral literally called FPU takes ld_fpu_t; without that rule the
    # outlier is named after itself -- which IS the group name -- and both
    # typedefs collide (a redefinition the compiler rejects).
    assert output.count("} ld_fpu_t;") == 1
    assert output.count("} ld_fpu_cpacr_t;") == 1
    assert "static ld_fpu_t *const LD_FPU" in output
    assert "static ld_fpu_cpacr_t *const LD_FPU_CPACR" in output


def test_clean_fixture_timer_group_does_not_diverge(demo_device):
    # TIM1 carries its own groupName on the clean chip, so the TIM label covers
    # only the identical TIM2/TIM3 and no groupName divergence is reported.
    # (WDT0/WDT1 still split -- a derivedFrom override, which is warning-free
    # because no groupName claims the two are one type.)
    output = CWriter().render(demo_device)
    assert "family TIM:" not in output
    assert output.count("} dc_tim_t;") == 1
    assert output.count("} dc_tim1_t;") == 1


def test_fixture_derivedfrom_without_groupname_merges(demo_device):
    output = CWriter().render(demo_device)
    # ADC0 + ADC1 (derivedFrom, NO groupName) -> one merged type, two instances.
    # The type is named from ADC0's headerStructName; the bare root-name
    # fallback (no vendor name either) is covered in test_header_struct_name.
    assert output.count("} dc_adc_t;") == 1
    assert "static dc_adc_t *const DC_ADC0" in output
    assert "static dc_adc_t *const DC_ADC1" in output


def test_fixture_derived_override_is_split(demo_device):
    output = CWriter().render(demo_device)
    # WDT1 derivesFrom WDT0 but adds RELOAD -> "same type" would be a lie -> split.
    assert "} dc_wdt0_t;" in output
    assert "} dc_wdt1_t;" in output
    assert "static dc_wdt0_t *const DC_WDT0" in output
    assert "static dc_wdt1_t *const DC_WDT1" in output


def test_fixture_emits_irqn_enum_sorted_no_trailing_comma(demo_device):
    output = CWriter().render(demo_device)
    # One device-wide enum from every peripheral's <interrupt>, sorted by value.
    assert "} dc_irqn_e;" in output  # enum types end in _e, not _t
    enum_body = output.split("typedef enum {", 1)[1].split("} dc_irqn_e;", 1)[0]
    members = [line.strip() for line in enum_body.splitlines() if "_IRQn" in line]
    # UART0=20, UART1=21 (a derived peripheral's own vector), TIM1 dual-IRQ (25, 26).
    assert members == [
        "DC_UART0_IRQn    = 20,  /* UART0 global interrupt */",
        "DC_UART1_IRQn    = 21,  /* UART1 global interrupt */",
        "DC_TIM1_UP_IRQn  = 25,  /* TIM1 update */",
        "DC_TIM1_BRK_IRQn = 26,  /* TIM1 break */",
        "DC_ADC0_IRQn     = 27,  /* ADC0 conversion complete */",
        "DC_ADC1_IRQn     = 28,  /* ADC1 conversion complete */",
        "DC_SPI0_IRQn     = 30,  /* SPI0 interrupt */",
        "DC_SPI1_IRQn     = 30  /* SPI1 interrupt */",  # shared vector, last -> no comma
    ]
    assert not members[-1].endswith(",")  # C89 -pedantic-errors rejects trailing comma


def test_fixture_emits_per_instance_irq_links(demo_device):
    output = CWriter().render(demo_device)
    # Each instance carries its own IRQ handle(s), aliasing the enum member.
    assert "#define DC_UART0_IRQ DC_UART0_IRQn" in output
    assert "#define DC_UART1_IRQ DC_UART1_IRQn" in output  # derived instance, own vector
    assert "#define DC_TIM1_UP_IRQ DC_TIM1_UP_IRQn" in output  # multi-IRQ, role-named
    assert "#define DC_TIM1_BRK_IRQ DC_TIM1_BRK_IRQn" in output


def test_fixture_emits_cortex_m_nvic_helpers(demo_device):
    output = CWriter().render(demo_device)
    # CM0PLUS is detected as Cortex-M -> capability macro + the typed NVIC API.
    assert "#define DEMOMCU_HAS_NVIC 1" in output
    assert "#define DC_NVIC_ISER ((volatile uint32_t *)0xE000E100UL)" in output
    assert "REGFORGE_INLINE void dc_nvic_enable(dc_irqn_e irq)" in output
    assert "REGFORGE_INLINE void dc_nvic_set_priority(dc_irqn_e irq, uint8_t priority)" in output
    assert "assert((uint32_t)irq < DEMOMCU_NUM_IRQS)" in output  # bounds vs the count
    # set_priority routes through the renamed, prefix-namespaced shift helper.
    assert "REGFORGE_INLINE uint8_t dc_irq_prio(uint8_t priority)" in output
    assert "(uint32_t)dc_irq_prio(priority)" in output


def test_fixture_asserts_struct_size_from_address_block(demo_device):
    output = CWriter().render(demo_device)
    # GPIOA block (0x20) exceeds the last register end (0x18) -> padded + asserted.
    assert "RESERVED1[8];" in output  # trailing pad to 0x20
    assert (
        "REGFORGE_STATIC_ASSERT(sizeof(dc_gpioa_t) == 0x20, DC_GPIOA_SIZE, "
        '"GPIOA struct size vs addressBlock");' in output
    )
    # UART registers block (0x8) exactly fits the registers; its buffer window
    # (0x8..0x28) is a member too, so the contract reaches 0x28.
    assert (
        "REGFORGE_STATIC_ASSERT(sizeof(dc_uart_t) == 0x28, DC_UART_SIZE, "
        '"UART struct size vs addressBlock");' in output
    )


def test_fixture_buffer_block_emits_one_raw_window(demo_device):
    output = CWriter().render(demo_device)
    # The vendor names no registers for a buffer block, so none are invented:
    # one array, typed from the device bus width (32 bits -> 0x20 bytes / 8).
    assert "volatile uint32_t       BUFFER0[8];" in output
    # Its position is locked as tightly as a register's.
    assert (
        "REGFORGE_STATIC_ASSERT(offsetof(dc_uart_t, BUFFER0) == 0x08, "
        'DC_UART_BUFFER0_offset, "UART.BUFFER0 offset");' in output
    )
    # It is a window, not padding -- no RESERVED member covers that range.
    assert "RESERVED0[32];" not in output


def test_lint_fixture_derived_peripheral_does_not_inherit_interrupt(lint_demo_device):
    output = CWriter().render(lint_demo_device)
    # ADCA has vector 40; ADCB (derivedFrom ADCA) declares none -> no inherited IRQ.
    assert "#define LD_ADCA_IRQ LD_ADCA_IRQn" in output
    assert "LD_ADCB_IRQ" not in output  # interrupts are per-instance, never inherited
    assert "LD_ADCB_IRQn" not in output


def test_clean_fixture_derived_peripheral_declares_its_own(demo_device):
    # On the clean chip ADC1 carries its own vector, so both instances link one.
    output = CWriter().render(demo_device)
    assert "#define DC_ADC0_IRQ DC_ADC0_IRQn" in output
    assert "#define DC_ADC1_IRQ DC_ADC1_IRQn" in output


def test_fixture_surfaces_shared_irq_at_both_sites(demo_device):
    output = CWriter().render(demo_device)
    lines = output.splitlines()
    # SPI0 and SPI1 share vector 30: the enum lists both (legal duplicate values)...
    assert "DC_SPI0_IRQn     = 30" in output
    assert "DC_SPI1_IRQn     = 30" in output
    # ...and each instance site names the OTHER peripheral + the demux warning.
    spi0 = next(ln for ln in lines if ln.startswith("#define DC_SPI0_IRQ "))
    spi1 = next(ln for ln in lines if ln.startswith("#define DC_SPI1_IRQ "))
    assert "vector 30 -- shared with DC_SPI1; demux in ISR" in spi0
    assert "vector 30 -- shared with DC_SPI0; demux in ISR" in spi1
    # A non-shared vector carries no shared-with note.
    uart0 = next(ln for ln in lines if ln.startswith("#define DC_UART0_IRQ "))
    assert "shared with" not in uart0


def test_fixture_preserves_vendor_extensions_without_emitting(demo_device):
    assert demo_device.vendor_extensions_xml is not None
    assert "calibrated" in demo_device.vendor_extensions_xml
    assert "calibrated" not in CWriter().render(demo_device)  # opaque, never emitted


def test_shared_type_gets_per_instance_aliases(demo_device):
    output = CWriter().render(demo_device)
    # TIM2 and TIM3 share dc_tim_t, but each is nameable in its own right so a
    # signature never has to know about the family grouping.
    assert "typedef dc_tim_t dc_tim2_t;" in output
    assert "typedef dc_tim_t dc_tim3_t;" in output
    assert "typedef dc_uart_t dc_uart0_t;" in output
    assert "typedef dc_uart_t dc_uart1_t;" in output


def test_no_self_alias_is_emitted(demo_device):
    output = CWriter().render(demo_device)
    # The instance the type is already named after must NOT be re-aliased:
    # redefining a typedef is an error before C11, and the headers build as C89.
    assert "typedef dc_gpioa_t dc_gpioa_t;" not in output  # singleton family
    assert "typedef dc_crc_t dc_crc_t;" not in output  # groupName equals the instance
    assert "typedef dc_adc_t dc_adc0_t;" in output  # a differing name still gets one


def test_fixture_honors_header_struct_name(demo_device):
    output = CWriter().render(demo_device)
    # ADC0/ADC1 have no groupName, so without the vendor's headerStructName the
    # type would be named after instance zero (dc_adc0_t). ADC1 inherits the
    # name through derivedFrom, and both instances still get their own alias.
    assert demo_device.peripherals[8].header_struct_name == "ADC"
    assert output.count("} dc_adc_t;") == 1
    assert "} dc_adc0_t;" not in output
    assert "typedef dc_adc_t dc_adc0_t;" in output
    assert "typedef dc_adc_t dc_adc1_t;" in output
    assert "static dc_adc_t *const DC_ADC0" in output
    assert "static dc_adc_t *const DC_ADC1" in output


def test_fixture_peripheral_array_is_one_family_with_labelled_instances(demo_device):
    # PWM%s with dimIndex A,B: two instances 0x100 apart, one dc_pwm_t between them.
    assert [p.name for p in demo_device.peripherals[-3:]] == ["PWMA", "PWMB", "DMA"]
    output = CWriter().render(demo_device)
    assert output.count("} dc_pwm_t;") == 1
    assert "(family: PWMA, PWMB)" in output
    assert "#define DC_PWMA_BASE (0x40015000UL)" in output
    assert "#define DC_PWMB_BASE (0x40015100UL)" in output
    assert "typedef dc_pwm_t dc_pwma_t;" in output and "typedef dc_pwm_t dc_pwmb_t;" in output


def test_fixture_register_array_and_separate_copies(demo_device):
    output = CWriter().render(demo_device)
    squashed = _squash(output)
    assert "volatile uint32_t CC[4];" in squashed  # CC[%s]: one packed array member
    assert "#define DC_PWMA_CC_COUNT (4U)" in output
    assert (
        "#define DC_PWMA_CC(i) (*(volatile uint32_t *)"
        "(DC_PWMA_BASE + 0x00000010UL + (i) * 0x00000004UL))" in output
    )
    assert output.count("DC_PWMA_CC_RESET_VALUE") == 1  # once per array
    assert "volatile uint32_t DT0;" in squashed and "volatile uint32_t DT1;" in squashed  # DT%s
    assert "#define DC_PWMB_DT1 (*(volatile uint32_t *)(DC_PWMB_BASE + 0x00000028UL))" in output


def test_fixture_field_array_and_separate_copies(demo_device):
    output = CWriter().render(demo_device)
    # MODE%s expanded to MODE0/MODE1, each with the enumerated values.
    assert "#define DC_GPIOA_MODER_MODE1_Pos (2U)" in output
    assert "#define DC_GPIOA_MODER_MODE1_ANALOG (3U)" in output
    # OD[%s] stays one field with indexed position/mask macros.
    assert "#define DC_GPIOA_ODR_OD_COUNT (16U)" in output
    assert "#define DC_GPIOA_ODR_OD_Pos(i) (0U + (i) * 1U)" in output
    assert "#define DC_GPIOA_ODR_OD_Msk(i) (0x00000001UL << ((i) * 1U))" in output


def test_fixture_cluster_array_and_single_cluster(demo_device):
    output = CWriter().render(demo_device)
    squashed = _squash(output)
    # Nested types come before the struct that uses them.
    assert output.index("} dc_dma_ch_t;") < output.index("} dc_dma_t;")
    assert output.index("} dc_dma_stat_t;") < output.index("} dc_dma_t;")
    assert (
        "REGFORGE_STATIC_ASSERT(sizeof(dc_dma_ch_t) == 0x10, DC_DMA_CH_SIZE, "
        '"DMA.CH element size vs dimIncrement");' in output
    )
    assert "DC_DMA_STAT_SIZE" not in output  # a single cluster has no stride to assert
    assert "dc_dma_ch_t CH[4];" in squashed and "dc_dma_stat_t STAT;" in squashed
    assert (
        "#define DC_DMA_CH_DST(i) (*(volatile uint32_t *)"
        "(DC_DMA_BASE + 0x00000018UL + (i) * 0x00000010UL))" in output
    )
    assert "#define DC_DMA_CH_CTRL_EN_Pos (0U)" in output
    assert (
        "#define DC_DMA_STAT_ERR (*(volatile const uint32_t *)(DC_DMA_BASE + 0x00000054UL))"
        in output
    )
