"""The canonical fixture (minimal.svd) exercises features end-to-end.

test_golden diffs the whole output byte-for-byte; these name the specific
features the enriched fixture is there to demonstrate, so a regression points
at the feature rather than "the golden changed".
"""

from regforge.writers.c import CWriter


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


def test_fixture_divergent_groupname_is_split(demo_device):
    output = CWriter().render(demo_device)
    # TIM1 (advanced, has RCR) diverges from TIM2/TIM3 (general) under groupName
    # "TIM": the largest identical subgroup keeps the name, the outlier splits off
    # (so DC_TIM2->RCR is a compile error, not a reserved-address write).
    assert output.count("} dc_tim_t;") == 1
    assert output.count("} dc_tim1_t;") == 1
    assert "static dc_tim_t *const DC_TIM2" in output  # majority keeps the name
    assert "static dc_tim_t *const DC_TIM3" in output
    assert "static dc_tim1_t *const DC_TIM1" in output  # outlier gets its own
    assert "split 2 ways" in output  # the split is recorded as a note
    assert "first differs at RCR" in output


def test_fixture_derivedfrom_without_groupname_uses_root_name(demo_device):
    output = CWriter().render(demo_device)
    # ADC0 + ADC1 (derivedFrom, NO groupName) -> merge, type named after the root.
    assert output.count("} dc_adc0_t;") == 1
    assert "static dc_adc0_t *const DC_ADC0" in output
    assert "static dc_adc0_t *const DC_ADC1" in output


def test_fixture_derived_override_is_split(demo_device):
    output = CWriter().render(demo_device)
    # WDT1 derivesFrom WDT0 but adds RELOAD -> "same type" would be a lie -> split.
    assert "} dc_wdt0_t;" in output
    assert "} dc_wdt1_t;" in output
    assert "static dc_wdt0_t *const DC_WDT0" in output
    assert "static dc_wdt1_t *const DC_WDT1" in output


def test_fixture_preserves_vendor_extensions_without_emitting(demo_device):
    assert demo_device.vendor_extensions_xml is not None
    assert "calibrated" in demo_device.vendor_extensions_xml
    assert "calibrated" not in CWriter().render(demo_device)  # opaque, never emitted
