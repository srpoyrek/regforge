"""alternateRegister resolution: views of one word are linked into sets, primary first."""

from regforge.check import Severity
from regforge.ir import Cluster, Device, Dim, Peripheral, Register
from regforge.resolve import expand_dim, resolve_alternates


def _device(*registers: Register, clusters: list[Cluster] | None = None) -> Device:
    return Device(
        name="Chip",
        peripherals=[
            Peripheral("P", 0x0, registers=list(registers), clusters=list(clusters or []))
        ],
    )


def _messages(findings, severity):
    return [f.message for f in findings if f.severity is severity]


def test_pair_is_linked_primary_first():
    device = _device(
        Register("CCMR1_Output", 0x18, size=32),
        Register("CCMR1_Input", 0x18, size=32, alternate_register="CCMR1_Output"),
    )
    assert resolve_alternates(device) == []
    out, inp = device.peripherals[0].registers
    assert out.alternates == ("CCMR1_Output", "CCMR1_Input")
    assert inp.alternates == out.alternates


def test_mutual_declarations_are_one_set():
    device = _device(
        Register("A", 0x0, size=32, alternate_register="B"),
        Register("B", 0x0, size=32, alternate_register="A"),
    )
    resolve_alternates(device)
    a, b = device.peripherals[0].registers
    assert a.alternates == b.alternates == ("A", "B")  # a cycle: file order decides


def test_chain_is_one_set_rooted_at_the_register_nothing_points_away_from():
    device = _device(
        Register("A", 0x0, size=32, alternate_register="B"),
        Register("B", 0x0, size=32, alternate_register="C"),
        Register("C", 0x0, size=32),
    )
    resolve_alternates(device)
    assert [r.alternates for r in device.peripherals[0].registers] == [("C", "A", "B")] * 3


def test_self_reference_is_ignored_with_a_warning():
    device = _device(Register("C", 0x10, size=32, alternate_register="C"))
    findings = resolve_alternates(device)
    assert _messages(findings, Severity.WARNING) == [
        "P.C: alternateRegister names itself -- ignored"
    ]
    assert device.peripherals[0].registers[0].alternates == ()


def test_missing_target_is_an_error_and_the_register_stays_ordinary():
    device = _device(Register("D", 0x20, size=32, alternate_register="NOPE"))
    findings = resolve_alternates(device)
    assert _messages(findings, Severity.ERROR) == [
        "P.D: alternateRegister 'NOPE' -- no register of that name in P; treated as an "
        "ordinary register"
    ]
    assert device.peripherals[0].registers[0].alternates == ()


def test_target_in_another_peripheral_does_not_count():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral("P", 0x0, registers=[Register("X", 0x0, size=32)]),
            Peripheral("Q", 0x100, registers=[Register("Y", 0x0, size=32, alternate_register="X")]),
        ],
    )
    errors = _messages(resolve_alternates(device), Severity.ERROR)
    assert errors == [
        "Q.Y: alternateRegister 'X' -- no register of that name in Q; treated as an "
        "ordinary register"
    ]


def test_different_offset_leaves_the_views_unrelated():
    device = _device(
        Register("A", 0x0, size=32),
        Register("B", 0x8, size=32, alternate_register="A"),
    )
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == [
        "P.B: alternateRegister 'A' is at offset 0x0, not 0x8 -- an alternate view must "
        "share the offset; left unrelated"
    ]
    assert all(r.alternates == () for r in device.peripherals[0].registers)


def test_copies_of_a_template_pair_index_with_index():
    device = _device(
        Register("DT%s", 0x20, size=32, dim=Dim(2, 8)),
        Register("DTR%s", 0x20, size=32, dim=Dim(2, 8), alternate_register="DT%s"),
    )
    expand_dim(device)
    assert resolve_alternates(device) == []
    by_name = {r.name: r for r in device.peripherals[0].registers}
    assert by_name["DT0"].alternates == by_name["DTR0"].alternates == ("DT0", "DTR0")
    assert by_name["DT1"].alternates == by_name["DTR1"].alternates == ("DT1", "DTR1")


def test_copy_count_mismatch_is_a_warning():
    device = _device(
        Register("DT%s", 0x20, size=32, dim=Dim(2, 8)),
        Register("DTR%s", 0x20, size=32, dim=Dim(3, 8), alternate_register="DT%s"),
    )
    expand_dim(device)
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == [
        "P.DTR0: alternateRegister 'DT%s' expands to 2 copies, not 3 -- left unrelated",
        "P.DTR1: alternateRegister 'DT%s' expands to 2 copies, not 3 -- left unrelated",
        "P.DTR2: alternateRegister 'DT%s' expands to 2 copies, not 3 -- left unrelated",
    ]


def test_plain_register_naming_a_template_resolves_to_its_first_copy():
    device = _device(
        Register("DT%s", 0x20, size=32, dim=Dim(2, 8)),
        Register("RAW", 0x20, size=32, alternate_register="DT%s"),
    )
    expand_dim(device)
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == [
        "P.RAW: alternateRegister names the template 'DT%s' -- resolved to its first copy, DT0"
    ]
    by_name = {r.name: r for r in device.peripherals[0].registers}
    assert by_name["RAW"].alternates == ("DT0", "RAW")


def test_arrays_of_equal_shape_are_linked():
    device = _device(
        Register("CC[%s]", 0x10, size=32, dim=Dim(4, 4)),
        Register("CCI[%s]", 0x10, size=32, dim=Dim(4, 4), alternate_register="CC[%s]"),
    )
    expand_dim(device)
    assert resolve_alternates(device) == []
    cc, cci = device.peripherals[0].registers
    assert cc.alternates == cci.alternates == ("CC", "CCI")


def test_arrays_of_different_shape_are_left_unrelated():
    device = _device(
        Register("CC[%s]", 0x10, size=32, dim=Dim(4, 4)),
        Register("CCI[%s]", 0x10, size=32, dim=Dim(2, 4), alternate_register="CC[%s]"),
    )
    expand_dim(device)
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == [
        "P.CCI: alternateRegister 'CC' has a different <dim> shape -- left unrelated"
    ]


def test_array_and_single_register_are_different_shapes():
    device = _device(
        Register("CC[%s]", 0x10, size=32, dim=Dim(4, 4)),
        Register("X", 0x10, size=32, alternate_register="CC[%s]"),
    )
    expand_dim(device)
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == ["P.X: alternateRegister 'CC' has a different <dim> shape -- left unrelated"]


def test_views_inside_a_cluster_are_linked_per_cluster():
    cluster = Cluster(
        "CH",
        0x10,
        registers=[
            Register("XFER_Mem", 0xC, size=32),
            Register("XFER_Periph", 0xC, size=32, alternate_register="XFER_Mem"),
        ],
    )
    device = _device(Register("XFER_Mem", 0x0, size=32), clusters=[cluster])
    assert resolve_alternates(device) == []
    assert device.peripherals[0].registers[0].alternates == ()  # the peripheral's own is alone
    assert [r.alternates for r in cluster.registers] == [("XFER_Mem", "XFER_Periph")] * 2
