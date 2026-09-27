"""dim expansion: a template becomes its copies, or stays one array element.

Runs first, before derivedFrom and defaults. Only copies and renames; the
stride is never compared here, because a register may still lack its size.
"""

from regforge.ir import (
    AddressBlock,
    Cluster,
    Device,
    Dim,
    EnumeratedValue,
    Field,
    Interrupt,
    Peripheral,
    Register,
)
from regforge.resolve import expand_dim, resolve_derived


def _device(*peripherals: Peripheral) -> Device:
    return Device(name="Chip", peripherals=list(peripherals))


def _uart_template(**overrides) -> Peripheral:
    kwargs = dict(
        name="UART%s",
        base_address=0x40000000,
        dim=Dim(count=4, increment=0x400),
        registers=[Register("DR", 0x0), Register("SR", 0x4)],
        address_blocks=[AddressBlock(0, 0x400, "registers")],
    )
    kwargs.update(overrides)
    return Peripheral(**kwargs)


# --- peripherals ---


def test_peripheral_copies_replace_the_template_in_place():
    device = _device(Peripheral("A", 0x0), _uart_template(), Peripheral("Z", 0x9000))
    expand_dim(device)
    assert [p.name for p in device.peripherals] == ["A", "UART0", "UART1", "UART2", "UART3", "Z"]
    assert [p.base_address for p in device.peripherals[1:5]] == [
        0x40000000,
        0x40000400,
        0x40000800,
        0x40000C00,
    ]
    assert all(p.dim is None for p in device.peripherals)


def test_peripheral_copies_are_deep_and_complete():
    device = _device(_uart_template())
    expand_dim(device)
    uart0, uart1 = device.peripherals[:2]
    assert [r.name for r in uart1.registers] == ["DR", "SR"]
    assert uart1.registers[0] is not uart0.registers[0]  # editing one copy leaves the rest alone
    assert [(b.offset, b.size) for b in uart1.address_blocks] == [(0, 0x400)]


def test_peripheral_copies_form_one_family_through_the_pattern_stem():
    device = _device(_uart_template())
    expand_dim(device)
    assert {p.group_name for p in device.peripherals} == {"UART"}


def test_declared_group_name_is_kept():
    device = _device(_uart_template(group_name="SERIAL"))
    expand_dim(device)
    assert {p.group_name for p in device.peripherals} == {"SERIAL"}


def test_stem_drops_a_dangling_underscore():
    device = _device(_uart_template(name="PORT_%s"))
    expand_dim(device)
    assert device.peripherals[0].name == "PORT_0"
    assert device.peripherals[0].group_name == "PORT"


def test_dim_index_labels_name_the_copies():
    device = _device(Peripheral("GPIO%s", 0x50000000, dim=Dim(3, 0x1000, index=["A", "B", "C"])))
    expand_dim(device)
    assert [(p.name, p.base_address) for p in device.peripherals] == [
        ("GPIOA", 0x50000000),
        ("GPIOB", 0x50001000),
        ("GPIOC", 0x50002000),
    ]


def test_array_notation_on_a_peripheral_means_copies_and_warns():
    device = _device(_uart_template(name="UART[%s]", dim=Dim(2, 0x400)))
    warnings = expand_dim(device)
    assert [p.name for p in device.peripherals] == ["UART0", "UART1"]
    assert any("not an array" in w for w in warnings)


def test_interrupts_are_copied_with_the_label_and_reported():
    device = _device(
        _uart_template(dim=Dim(2, 0x400), interrupts=[Interrupt("UART%s", 20, "UART %s interrupt")])
    )
    warnings = expand_dim(device)
    assert [(i.name, i.value) for p in device.peripherals for i in p.interrupts] == [
        ("UART0", 20),
        ("UART1", 20),
    ]
    assert device.peripherals[0].interrupts[0].description == "UART %s interrupt"  # untouched
    assert any("cannot shift a vector number" in w for w in warnings)


def test_description_placeholder_is_left_alone():
    # The spec substitutes %s in name (and displayName) only.
    device = _device(_uart_template(dim=Dim(2, 0x400), description="UART instance %s"))
    expand_dim(device)
    assert device.peripherals[1].description == "UART instance %s"


# --- registers ---


def _with_registers(*registers: Register) -> Device:
    return _device(Peripheral("P", 0x0, registers=list(registers)))


def test_register_copies_are_named_and_placed_along_the_stride():
    device = _with_registers(
        Register("CR", 0x0),
        Register(
            "DATA%s",
            0x10,
            dim=Dim(8, 4),
            fields=[Field("V", 0, 8, enums=[EnumeratedValue("ZERO", 0)])],
        ),
    )
    expand_dim(device)
    registers = device.peripherals[0].registers
    assert [r.name for r in registers] == ["CR"] + [f"DATA{i}" for i in range(8)]
    assert [r.address_offset for r in registers[1:]] == [0x10 + 4 * i for i in range(8)]
    assert all(r.dim is None for r in registers)
    assert registers[1].fields[0] is not registers[2].fields[0]  # fields deep-copied
    assert registers[8].fields[0].enums[0].name == "ZERO"


def test_array_register_stays_one_element_with_a_bare_name():
    device = _with_registers(Register("DATA[%s]", 0x10, dim=Dim(8, 4)))
    expand_dim(device)
    (register,) = device.peripherals[0].registers
    assert register.name == "DATA"
    assert (register.dim.count, register.dim.increment) == (8, 4)  # kept for layout/writers


def test_dim_index_on_an_array_is_ignored_and_reported():
    device = _with_registers(Register("DATA[%s]", 0x10, dim=Dim(2, 4, index=["A", "B"])))
    warnings = expand_dim(device)
    assert device.peripherals[0].registers[0].dim.index is None
    assert any("DATA[%s]: dimIndex ignored" in w for w in warnings)


def test_register_size_is_not_needed_to_expand():
    # Sizes arrive in defaults resolution; expansion must not depend on them.
    device = _with_registers(Register("DATA%s", 0x10, dim=Dim(2, 4)))
    assert expand_dim(device) == []
    assert [r.size for r in device.peripherals[0].registers] == [None, None]


# --- fields ---


def test_field_copies_step_by_bits():
    device = _with_registers(
        Register("MODER", 0x0, fields=[Field("MODE%s", 0, 2, dim=Dim(16, 2))]),
    )
    expand_dim(device)
    fields = device.peripherals[0].registers[0].fields
    assert [f.name for f in fields][:3] == ["MODE0", "MODE1", "MODE2"]
    assert [f.bit_offset for f in fields] == [2 * i for i in range(16)]
    assert all(f.bit_width == 2 and f.dim is None for f in fields)


def test_array_field_stays_one_element():
    device = _with_registers(Register("ODR", 0x0, fields=[Field("OD[%s]", 0, 1, dim=Dim(16, 1))]))
    expand_dim(device)
    (field_,) = device.peripherals[0].registers[0].fields
    assert (field_.name, field_.dim.count, field_.dim.increment) == ("OD", 16, 1)


# --- clusters ---


def test_cluster_copies_share_a_type_named_after_the_stem():
    device = _device(
        Peripheral(
            "DMA",
            0x0,
            clusters=[
                Cluster("CH%s", 0x10, dim=Dim(3, 0x10), registers=[Register("CTRL", 0x0)]),
            ],
        )
    )
    expand_dim(device)
    clusters = device.peripherals[0].clusters
    assert [(c.name, c.address_offset) for c in clusters] == [
        ("CH0", 0x10),
        ("CH1", 0x20),
        ("CH2", 0x30),
    ]
    assert {c.header_struct_name for c in clusters} == {"CH"}  # one dma_ch_t for all three
    assert clusters[0].registers[0] is not clusters[1].registers[0]


def test_array_cluster_stays_one_element_and_its_contents_expand():
    device = _device(
        Peripheral(
            "DMA",
            0x0,
            clusters=[
                Cluster(
                    "CH[%s]",
                    0x10,
                    dim=Dim(4, 0x10),
                    registers=[Register("BUF%s", 0x0, dim=Dim(2, 4))],
                    clusters=[Cluster("SUB%s", 0x8, dim=Dim(2, 4))],
                ),
            ],
        )
    )
    expand_dim(device)
    (cluster,) = device.peripherals[0].clusters
    assert cluster.name == "CH" and cluster.dim.count == 4
    assert [r.name for r in cluster.registers] == ["BUF0", "BUF1"]  # expanded inside
    assert [c.name for c in cluster.clusters] == ["SUB0", "SUB1"]


# --- interplay with derivedFrom, and idempotence ---


def test_derived_from_can_name_an_expanded_copy():
    device = _device(
        _uart_template(dim=Dim(2, 0x400)),
        Peripheral("UART_DBG", 0x40001000, derived_from="UART1"),
    )
    expand_dim(device)
    warnings = resolve_derived(device)
    assert warnings == []
    assert [r.name for r in device.peripherals[2].registers] == ["DR", "SR"]


def test_a_derived_template_is_split_into_shells_before_the_copy():
    device = _device(
        Peripheral("UART0", 0x40000000, registers=[Register("DR", 0x0)]),
        Peripheral("UARTX%s", 0x40001000, dim=Dim(2, 0x400), derived_from="UART0"),
    )
    expand_dim(device)
    resolve_derived(device)
    shells = device.peripherals[1:]
    assert [p.name for p in shells] == ["UARTX0", "UARTX1"]
    assert all(p.derived_from == "UART0" for p in shells)
    assert all([r.name for r in p.registers] == ["DR"] for p in shells)


def test_expansion_is_idempotent():
    device = _device(
        _uart_template(),
        Peripheral(
            "P",
            0x0,
            registers=[
                Register("DATA[%s]", 0x10, dim=Dim(8, 4)),
                Register("R%s", 0x40, dim=Dim(2, 4)),
            ],
        ),
    )
    expand_dim(device)
    first = [(p.name, [r.name for r in p.registers]) for p in device.peripherals]
    expand_dim(device)
    second = [(p.name, [r.name for r in p.registers]) for p in device.peripherals]
    assert first == second


def test_plain_device_is_untouched():
    device = _device(Peripheral("P", 0x0, registers=[Register("R", 0x0)]))
    assert expand_dim(device) == []
    assert [r.name for r in device.peripherals[0].registers] == ["R"]
