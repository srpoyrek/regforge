"""derivedFrom resolution: a derived peripheral inherits its base's registers."""

from regforge.ir import Device, Interrupt, Peripheral, Register
from regforge.resolve import resolve_defaults, resolve_derived


def test_resolve_derived_copies_base_registers():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="UART0",
                base_address=0x4000,
                registers=[
                    Register(name="DR", address_offset=0x0, size=32),
                    Register(name="SR", address_offset=0x4, size=32),
                ],
            ),
            Peripheral(name="UART1", base_address=0x5000, derived_from="UART0"),
        ],
    )
    resolve_defaults(device)
    resolve_derived(device)

    uart1 = device.peripherals[1]
    assert [r.name for r in uart1.registers] == ["DR", "SR"]  # inherited from UART0
    assert uart1.base_address == 0x5000  # its own base address is kept
    # Deep copy -- editing the derived copy must not touch the base.
    assert uart1.registers[0] is not device.peripherals[0].registers[0]


def test_resolve_derived_chain_inherits_through_root():
    # UART2 -> UART1 -> UART0: each link inherits the full set even out of order.
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(name="UART2", base_address=0x6000, derived_from="UART1"),
            Peripheral(name="UART1", base_address=0x5000, derived_from="UART0"),
            Peripheral(
                name="UART0",
                base_address=0x4000,
                registers=[Register(name="DR", address_offset=0x0, size=32)],
            ),
        ],
    )
    resolve_defaults(device)
    resolve_derived(device)
    assert [r.name for r in device.peripherals[0].registers] == ["DR"]  # UART2, via chain


def test_resolve_derived_does_not_inherit_interrupts():
    # Interrupts are per-instance: registers copy down, the base's vector does not.
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="ADC0",
                base_address=0x4000,
                registers=[Register(name="CR", address_offset=0x0, size=32)],
                interrupts=[Interrupt("ADC0", 27)],
            ),
            Peripheral(name="ADC1", base_address=0x5000, derived_from="ADC0"),
        ],
    )
    resolve_defaults(device)
    resolve_derived(device)
    adc1 = device.peripherals[1]
    assert [r.name for r in adc1.registers] == ["CR"]  # registers inherited
    assert adc1.interrupts == []  # base's vector NOT inherited


def test_resolve_derived_keeps_only_its_own_interrupts():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="UART0",
                base_address=0x4000,
                registers=[Register(name="DR", address_offset=0x0, size=32)],
                interrupts=[Interrupt("UART0", 20)],
            ),
            Peripheral(
                name="UART1",
                base_address=0x5000,
                derived_from="UART0",
                interrupts=[Interrupt("UART1", 21)],
            ),
        ],
    )
    resolve_defaults(device)
    resolve_derived(device)
    uart1 = device.peripherals[1]
    assert [r.name for r in uart1.registers] == ["DR"]  # registers inherited
    assert [(i.name, i.value) for i in uart1.interrupts] == [("UART1", 21)]  # its own only


def test_resolve_derived_unknown_base_warns_and_leaves_empty():
    device = Device(
        name="Chip",
        peripherals=[Peripheral(name="UART1", base_address=0x5000, derived_from="NOPE")],
    )
    warnings = resolve_derived(device)
    assert device.peripherals[0].registers == []
    assert any("no such peripheral" in w for w in warnings)
