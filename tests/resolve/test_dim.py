"""dim expansion: a template becomes its copies, or stays one array element.

Runs first, before derivedFrom and defaults. Only copies and renames; the
stride is never compared here, because a register may still lack its size.
"""

from regforge.check import Severity
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
    findings = expand_dim(device)
    assert [p.name for p in device.peripherals] == ["UART0", "UART1"]
    assert any("not an array" in f.message for f in findings)


def test_labelled_interrupts_go_to_every_copy():
    device = _device(
        _uart_template(dim=Dim(2, 0x400), interrupts=[Interrupt("UART%s", 20, "UART %s interrupt")])
    )
    findings = expand_dim(device)
    assert [(i.name, i.value) for p in device.peripherals for i in p.interrupts] == [
        ("UART0", 20),
        ("UART1", 20),
    ]
    assert device.peripherals[0].interrupts[0].description == "UART %s interrupt"  # untouched
    assert findings == []  # a labelled interrupt is per copy; sharing is marked in the header


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
    findings = expand_dim(device)
    assert device.peripherals[0].registers[0].dim.index is None
    assert any("DATA[%s]: dimIndex ignored" in f.message for f in findings)


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


def test_missing_placeholder_appends_the_index_and_warns():
    device = _device(
        _uart_template(name="UART", dim=Dim(4, 0x400)),
        Peripheral("P", 0x0, registers=[Register("DATA", 0x10, dim=Dim(2, 4))]),
        Peripheral("G", 0x1000, registers=[Register("R", 0x0, dim=Dim(2, 4, index=["A", "B"]))]),
    )
    findings = expand_dim(device)
    assert [p.name for p in device.peripherals[:4]] == ["UART0", "UART1", "UART2", "UART3"]
    assert {p.group_name for p in device.peripherals[:4]} == {"UART"}  # still one family
    assert [r.name for r in device.peripherals[4].registers] == ["DATA0", "DATA1"]
    assert [r.name for r in device.peripherals[5].registers] == ["RA", "RB"]  # labels appended
    assert any(
        "UART: <dim> on a name without a %s" in f.message and "UART0..UART3" in f.message
        for f in findings
    )
    assert any("P.DATA: <dim> on a name without a %s" in f.message for f in findings)


def test_array_flag_marks_kept_elements():
    device = _with_registers(
        Register("DATA[%s]", 0x10, dim=Dim(8, 4)), Register("D%s", 0x40, dim=Dim(2, 4))
    )
    expand_dim(device)
    array, *copies = device.peripherals[0].registers
    assert array.dim.array is True  # what tells a second expansion to leave it alone
    assert all(c.dim is None for c in copies)


# --- the placeholder and label edge cases ---


def _messages(findings, severity=None):
    return [f.message for f in findings if severity is None or f.severity is severity]


def test_two_placeholders_take_the_same_label_and_warn():
    device = _with_registers(Register("PORT%s_PIN%s", 0x0, dim=Dim(2, 4)))
    findings = expand_dim(device)
    assert [r.name for r in device.peripherals[0].registers] == ["PORT0_PIN0", "PORT1_PIN1"]
    assert any("2 %s placeholders" in m and "PORT0_PIN0" in m for m in _messages(findings))


def test_label_count_mismatch_trusts_dim():
    device = _with_registers(
        Register("A%s", 0x0, dim=Dim(4, 4, index=["0", "1", "2"])),  # one short
        Register("B%s", 0x20, dim=Dim(2, 4, index=["X", "Y", "Z"])),  # one over
    )
    findings = expand_dim(device)
    names = [r.name for r in device.peripherals[0].registers]
    assert names == ["A0", "A1", "A2", "A3", "BX", "BY"]  # padded with the index; extra dropped
    warnings = _messages(findings, Severity.WARNING)
    assert any(
        "P.A%s: dimIndex gives 3 label(s) for <dim> 4" in m and "missing" in m for m in warnings
    )
    assert any(
        "P.B%s: dimIndex gives 3 label(s) for <dim> 2" in m and "dropped" in m for m in warnings
    )


def test_labels_that_are_not_identifier_tails_are_cleaned():
    device = _with_registers(
        Register("V%s", 0x0, dim=Dim(3, 4, index=["1.5", "a b", "$"])),
    )
    findings = expand_dim(device)
    assert [r.name for r in device.peripherals[0].registers] == ["V1_5", "Va_b", "V2"]
    warnings = _messages(findings, Severity.WARNING)
    assert any("'1.5' is not an identifier -- using '1_5'" in m for m in warnings)
    assert any(
        "'$' is not an identifier -- using '2'" in m for m in warnings
    )  # nothing left: the index


def test_repeated_labels_are_an_error_and_fall_back_to_the_index():
    device = _device(Peripheral("UART%s", 0x0, dim=Dim(3, 0x400, index=["0", "0", "1"])))
    findings = expand_dim(device)
    assert [p.name for p in device.peripherals] == ["UART0", "UART1", "UART2"]
    errors = _messages(findings, Severity.ERROR)
    assert errors == [
        "UART%s: dimIndex labels repeat (0,0,1) -- two copies cannot share a name; "
        "falling back to 0..2"
    ]


def test_dim_name_names_the_type_below_header_struct_name_above_group_name():
    device = _device(
        Peripheral("UART%s", 0x0, dim=Dim(2, 0x400, name="Uart"), group_name="SERIAL"),
        Peripheral("SPI%s", 0x2000, dim=Dim(2, 0x400, name="Spi"), header_struct_name="SPIM"),
        Peripheral(
            "DMA",
            0x4000,
            clusters=[
                Cluster(
                    "CH[%s]", 0x10, dim=Dim(2, 0x10, name="Channel"), registers=[Register("R", 0)]
                ),
                Cluster("Q%s", 0x40, dim=Dim(2, 0x10, name="Queue"), registers=[Register("R", 0)]),
            ],
        ),
    )
    assert expand_dim(device) == []
    uart, spi, dma = device.peripherals[0], device.peripherals[2], device.peripherals[4]
    assert (uart.header_struct_name, uart.group_name) == (
        "Uart",
        "SERIAL",
    )  # dimName outranks group
    assert spi.header_struct_name == "SPIM"  # an explicit headerStructName still wins
    assert dma.clusters[0].header_struct_name == "Channel"  # a kept array takes it too
    assert {c.header_struct_name for c in dma.clusters[1:]} == {"Queue"}  # copies share it


# --- addressing: what a template can fail to be ---


def test_missing_increment_keeps_one_instance_and_errors():
    device = _device(
        Peripheral("UART%s", 0x0, dim=Dim(2, None)),
        Peripheral(
            "P",
            0x100,
            registers=[
                Register("DATA[%s]", 0, dim=Dim(4, None)),
                Register("X%s", 0x40, dim=Dim(2, None)),
            ],
        ),
    )
    findings = expand_dim(device)
    assert [p.name for p in device.peripherals] == ["UART", "P"]
    assert [r.name for r in device.peripherals[1].registers] == ["DATA", "X"]
    assert all(r.dim is None for r in device.peripherals[1].registers)  # not arrays either
    assert device.peripherals[0].dim is None
    assert device.peripherals[0].expanded_from == "UART%s"
    errors = _messages(findings, Severity.ERROR)
    assert len(errors) == 3
    assert any(
        "UART%s: <dim> 2 without <dimIncrement>" in m and "one instance, UART" in m for m in errors
    )


def test_dim_of_one_is_a_single_labelled_copy():
    device = _device(Peripheral("UART%s", 0x0, dim=Dim(1, 0x400)))
    assert expand_dim(device) == []
    assert [p.name for p in device.peripherals] == ["UART0"]


def test_dim_zero_drops_the_element_with_a_warning():
    device = _device(
        Peripheral("GHOST%s", 0x0, dim=Dim(0, 0x100)),
        Peripheral(
            "P",
            0x100,
            registers=[
                Register("R", 0, fields=[Field("F%s", 0, 1, dim=Dim(0, 1))]),
                Register("D[%s]", 0x10, dim=Dim(0, 4)),
            ],
            clusters=[Cluster("C%s", 0x20, dim=Dim(0, 0x10), registers=[Register("X", 0)])],
        ),
    )
    findings = expand_dim(device)
    assert [p.name for p in device.peripherals] == ["P"]
    assert [r.name for r in device.peripherals[0].registers] == ["R"]
    assert device.peripherals[0].registers[0].fields == []
    assert device.peripherals[0].clusters == []
    warnings = _messages(findings, Severity.WARNING)
    assert len(warnings) == 4 and all("<dim> 0 declares nothing -- dropped" in m for m in warnings)
    assert any(m.startswith("GHOST%s:") for m in warnings)
    assert any(m.startswith("P.R.F%s:") for m in warnings)


def test_increment_zero_is_an_error_but_still_expands():
    device = _device(Peripheral("SAME%s", 0x1000, dim=Dim(2, 0)))
    findings = expand_dim(device)
    assert [(p.name, p.base_address) for p in device.peripherals] == [
        ("SAME0", 0x1000),
        ("SAME1", 0x1000),
    ]
    assert _messages(findings, Severity.ERROR) == [
        "SAME%s: <dimIncrement> 0 puts all 2 copies at one address"
    ]


def test_copies_remember_their_template():
    device = _device(
        _uart_template(dim=Dim(2, 0x400)),
        Peripheral(
            "P", 0x9000, registers=[Register("D%s", 0, dim=Dim(2, 4)), Register("PLAIN", 0x10)]
        ),
    )
    expand_dim(device)
    assert [p.expanded_from for p in device.peripherals] == ["UART%s", "UART%s", None]
    assert [r.expanded_from for r in device.peripherals[2].registers] == ["D%s", "D%s", None]


# --- derivedFrom meets dim ---


def test_derived_from_the_template_resolves_to_copy_zero_with_a_warning():
    device = _device(
        _uart_template(dim=Dim(2, 0x400)),
        Peripheral("UART5", 0x9000, derived_from="UART%s"),
    )
    expand_dim(device)
    warnings = resolve_derived(device)
    uart5 = device.peripherals[2]
    assert [r.name for r in uart5.registers] == ["DR", "SR"]
    assert uart5.derived_from == "UART0"  # re-pointed, so the family sees a real base
    assert warnings == [
        "UART5: derivedFrom names the template 'UART%s' -- resolved to its first copy, UART0"
    ]


def test_derived_own_dim_wins_over_the_base_template():
    device = _device(
        _uart_template(dim=Dim(4, 0x400)),
        Peripheral("X%s", 0x8000, dim=Dim(2, 0x800), derived_from="UART%s"),
    )
    assert expand_dim(device) == []
    assert [(p.name, p.base_address) for p in device.peripherals[4:]] == [
        ("X0", 0x8000),
        ("X1", 0x8800),
    ]
    resolve_derived(device)
    assert [r.name for r in device.peripherals[5].registers] == ["DR", "SR"]


def test_derived_inherits_dim_and_labels_but_keeps_its_own_stride():
    device = _device(
        Peripheral(
            "SER%s", 0x0, dim=Dim(3, 0x100, index=["A", "B", "C"]), registers=[Register("CR", 0)]
        ),
        Peripheral("SERX%s", 0x8000, dim=Dim(None, 0x200), derived_from="SER%s"),
    )
    assert expand_dim(device) == []
    assert [(p.name, p.base_address) for p in device.peripherals[3:]] == [
        ("SERXA", 0x8000),
        ("SERXB", 0x8200),
        ("SERXC", 0x8400),
    ]
    warnings = resolve_derived(device)
    assert all([r.name for r in p.registers] == ["CR"] for p in device.peripherals[3:])
    assert len(warnings) == 3  # each copy named the template and was pointed at SERA


def test_inheriting_dim_from_a_base_without_one_is_an_error():
    device = _device(
        Peripheral("UART0", 0x0, registers=[Register("DR", 0)]),
        Peripheral("X%s", 0x8000, dim=Dim(None, 0x200), derived_from="UART0"),
    )
    findings = expand_dim(device)
    assert [p.name for p in device.peripherals] == ["UART0", "X"]
    assert _messages(findings, Severity.ERROR) == [
        "X%s: inherits <dim> from 'UART0', which declares none -- emitted as one instance"
    ]


# --- interrupts, field widths, label order ---


def test_fixed_name_interrupt_stays_on_copy_zero_and_warns():
    device = _device(_uart_template(dim=Dim(3, 0x400), interrupts=[Interrupt("UART_IRQ", 20)]))
    findings = expand_dim(device)
    assert [[i.name for i in p.interrupts] for p in device.peripherals] == [["UART_IRQ"], [], []]
    assert _messages(findings, Severity.WARNING) == [
        "UART%s: interrupt 'UART_IRQ' (vector 20) has no %s -- attached to UART0 only; "
        "UART1, UART2 have no vector of their own"
    ]


def test_field_copies_that_overlap_are_an_error():
    device = _with_registers(Register("MODER", 0x0, fields=[Field("MODE%s", 0, 4, dim=Dim(4, 2))]))
    findings = expand_dim(device)
    fields = device.peripherals[0].registers[0].fields
    assert [f.bit_offset for f in fields] == [0, 2, 4, 6]  # still expanded, as written
    assert _messages(findings, Severity.ERROR) == [
        "P.MODER.MODE%s: increment 2 bit(s) is smaller than the 4-bit field -- the copies overlap"
    ]


def test_copies_follow_the_label_order_as_written():
    # dimIndex order is the copy order: sorting it would move addresses.
    device = _device(Peripheral("GPIO%s", 0x0, dim=Dim(3, 0x100, index=["C", "A", "B"])))
    expand_dim(device)
    assert [(p.name, p.base_address) for p in device.peripherals] == [
        ("GPIOC", 0x0),
        ("GPIOA", 0x100),
        ("GPIOB", 0x200),
    ]
