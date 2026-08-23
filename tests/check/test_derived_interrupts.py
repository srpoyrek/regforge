"""Linter: interrupt mistakes on derivedFrom peripherals (per-instance rule)."""

from regforge.check import Severity, check_derived_interrupts
from regforge.ir import Device, Interrupt, Peripheral


def _device(*peripherals: Peripheral) -> Device:
    return Device(name="C", peripherals=list(peripherals))


def test_omission_warns_and_names_the_base_vector():
    # ADC1 derivedFrom ADC0 but declares no interrupt; ADC0 has vector 27.
    device = _device(
        Peripheral(name="ADC0", base_address=0x0, interrupts=[Interrupt("ADC0", 27)]),
        Peripheral(name="ADC1", base_address=0x400, derived_from="ADC0"),
    )
    findings = check_derived_interrupts(device)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "ADC1" in findings[0].message
    assert "27" in findings[0].message


def test_copy_pasted_base_vector_warns():
    # The derived peripheral reuses the base's vector number verbatim.
    device = _device(
        Peripheral(name="TIMR0", base_address=0x0, interrupts=[Interrupt("TIMR0", 7)]),
        Peripheral(
            name="TIMR1",
            base_address=0x400,
            derived_from="TIMR0",
            interrupts=[Interrupt("TIMR1", 7)],
        ),
    )
    findings = check_derived_interrupts(device)
    assert len(findings) == 1
    assert "TIMR1" in findings[0].message
    assert "identical" in findings[0].message


def test_own_distinct_vector_is_clean():
    device = _device(
        Peripheral(name="UART0", base_address=0x0, interrupts=[Interrupt("UART0", 20)]),
        Peripheral(
            name="UART1",
            base_address=0x400,
            derived_from="UART0",
            interrupts=[Interrupt("UART1", 21)],
        ),
    )
    assert check_derived_interrupts(device) == []


def test_base_without_interrupt_is_clean():
    # Nothing to inherit -> no finding even when the derived declares none.
    device = _device(
        Peripheral(name="WDT0", base_address=0x0),
        Peripheral(name="WDT1", base_address=0x400, derived_from="WDT0"),
    )
    assert check_derived_interrupts(device) == []


def test_fixture_flags_only_the_adc1_omission(demo_device):
    findings = check_derived_interrupts(demo_device)
    # UART1 has its own distinct vector; WDT1's base has no vector -> both clean.
    assert len(findings) == 1
    assert "ADC1" in findings[0].message
