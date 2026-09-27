"""derivedFrom resolution: a derived peripheral inherits its base's registers.

The pass runs before defaults resolution, so what it copies is raw and the
copies resolve under the derived peripheral's own chain afterwards.
"""

from regforge.ir import Access, AddressBlock, Cluster, Device, Interrupt, Peripheral, Register
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
    resolve_derived(device)
    resolve_defaults(device)

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
    resolve_derived(device)
    resolve_defaults(device)
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
    resolve_derived(device)
    resolve_defaults(device)
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
    resolve_derived(device)
    resolve_defaults(device)
    uart1 = device.peripherals[1]
    assert [r.name for r in uart1.registers] == ["DR"]  # registers inherited
    assert [(i.name, i.value) for i in uart1.interrupts] == [("UART1", 21)]  # its own only


def test_resolve_derived_inherits_address_block():
    # The footprint is identical for every instance of a type, so it IS inherited.
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="UART0",
                base_address=0x4000,
                registers=[Register("DR", 0x0, size=32)],
                address_blocks=[AddressBlock(0, 0x8, "registers")],
            ),
            Peripheral(name="UART1", base_address=0x5000, derived_from="UART0"),
        ],
    )
    resolve_derived(device)
    resolve_defaults(device)
    uart1 = device.peripherals[1]
    assert [(b.offset, b.size, b.usage) for b in uart1.address_blocks] == [(0, 0x8, "registers")]


def test_resolve_derived_unknown_base_warns_and_leaves_empty():
    device = Device(
        name="Chip",
        peripherals=[Peripheral(name="UART1", base_address=0x5000, derived_from="NOPE")],
    )
    warnings = resolve_derived(device)
    assert device.peripherals[0].registers == []
    assert any("no such peripheral" in w for w in warnings)


def _uart_pair(*, base_access=None, derived_access=None):
    return Device(
        name="Chip",
        default_access=Access.READ_WRITE,
        peripherals=[
            Peripheral(
                name="UART0",
                base_address=0x4000,
                default_access=base_access,
                registers=[Register(name="SR", address_offset=0x0, size=32)],  # no own access
            ),
            Peripheral(
                name="UART1",
                base_address=0x5000,
                derived_from="UART0",
                default_access=derived_access,
            ),
        ],
    )


def test_derived_inherits_the_base_peripheral_defaults():
    # UART0 says read-only at peripheral level and SR is silent. The copy in
    # UART1 must resolve the same way, not fall through to the device default.
    device = _uart_pair(base_access=Access.READ_ONLY)
    resolve_derived(device)
    resolve_defaults(device)
    assert device.peripherals[1].default_access is Access.READ_ONLY  # handed down
    assert device.peripherals[1].registers[0].access is Access.READ_ONLY


def test_derived_own_default_beats_the_base():
    # The derived peripheral overrides at its level: its copies follow it, the
    # base's registers keep the base's value.
    device = _uart_pair(base_access=Access.READ_ONLY, derived_access=Access.WRITE_ONLY)
    resolve_derived(device)
    resolve_defaults(device)
    assert device.peripherals[0].registers[0].access is Access.READ_ONLY
    assert device.peripherals[1].registers[0].access is Access.WRITE_ONLY


def test_resolve_derived_copies_clusters():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="DMA0",
                base_address=0x4000,
                clusters=[
                    Cluster("CH", 0x10, registers=[Register("CTRL", 0x0, size=32)]),
                ],
            ),
            Peripheral(name="DMA1", base_address=0x5000, derived_from="DMA0"),
        ],
    )
    resolve_derived(device)
    dma1 = device.peripherals[1]
    assert [c.name for c in dma1.clusters] == ["CH"]
    assert dma1.clusters[0] is not device.peripherals[0].clusters[0]  # a deep copy
    assert [r.name for r in dma1.clusters[0].registers] == ["CTRL"]


def test_derived_with_its_own_clusters_is_left_alone():
    # Declaring clusters (like declaring registers) is an override, not a shell.
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="DMA0",
                base_address=0x4000,
                registers=[Register("CFG", 0x0, size=32)],
            ),
            Peripheral(
                name="DMA1",
                base_address=0x5000,
                derived_from="DMA0",
                clusters=[Cluster("OWN", 0x0)],
            ),
        ],
    )
    resolve_derived(device)
    assert device.peripherals[1].registers == []
    assert [c.name for c in device.peripherals[1].clusters] == ["OWN"]


def test_cluster_derived_from_is_reported_not_resolved():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="DMA",
                base_address=0x4000,
                clusters=[
                    Cluster("CH0", 0x10, registers=[Register("CTRL", 0x0, size=32)]),
                    Cluster("CH1", 0x20, derived_from="CH0"),
                ],
            )
        ],
    )
    warnings = resolve_derived(device)
    assert device.peripherals[0].clusters[1].registers == []  # emitted as written
    assert any("DMA.CH1: derivedFrom 'CH0' on a cluster" in w for w in warnings)
