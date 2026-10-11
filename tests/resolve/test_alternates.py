"""alternateRegister resolution: views of one word are merged into sets, primary first."""

from regforge.check import Severity
from regforge.ir import AlternateSet, Cluster, Device, Dim, Peripheral, Register
from regforge.resolve import expand_dim, resolve_alternates


def _alt(register: Register, of: str | None = None) -> AlternateSet:
    """The set the reader makes for ``register``, which declared itself an alternate of ``of``."""
    return AlternateSet((register,), joins=of)


def _device(*sets: AlternateSet, clusters: list[Cluster] | None = None) -> Device:
    return Device(
        name="Chip",
        peripherals=[
            Peripheral("P", 0x0, alternate_sets=list(sets), clusters=list(clusters or []))
        ],
    )


def _names(device: Device) -> list[tuple[str, ...]]:
    return [alternate_set.names for alternate_set in device.peripherals[0].alternate_sets]


def _messages(findings, severity):
    return [f.message for f in findings if f.severity is severity]


def test_pair_is_linked_primary_first():
    device = _device(
        _alt(Register("CCMR1_Output", 0x18, size=32)),
        _alt(Register("CCMR1_Input", 0x18, size=32), of="CCMR1_Output"),
    )
    assert resolve_alternates(device) == []
    assert _names(device) == [("CCMR1_Output", "CCMR1_Input")]


def test_mutual_declarations_are_one_set():
    device = _device(
        _alt(Register("A", 0x0, size=32), of="B"),
        _alt(Register("B", 0x0, size=32), of="A"),
    )
    resolve_alternates(device)
    assert _names(device) == [("A", "B")]  # a cycle: file order decides


def test_chain_is_one_set_rooted_at_the_register_nothing_points_away_from():
    device = _device(
        _alt(Register("A", 0x0, size=32), of="B"),
        _alt(Register("B", 0x0, size=32), of="C"),
        _alt(Register("C", 0x0, size=32)),
    )
    resolve_alternates(device)
    assert _names(device) == [("C", "A", "B")]


def test_self_reference_is_ignored_with_a_warning():
    device = _device(_alt(Register("C", 0x10, size=32), of="C"))
    findings = resolve_alternates(device)
    assert _messages(findings, Severity.WARNING) == [
        "P.C: alternateRegister names itself -- ignored"
    ]
    assert _names(device) == [("C",)]


def test_missing_target_is_an_error_and_the_register_stays_ordinary():
    device = _device(_alt(Register("D", 0x20, size=32), of="NOPE"))
    findings = resolve_alternates(device)
    assert _messages(findings, Severity.ERROR) == [
        "P.D: alternateRegister 'NOPE' -- no register of that name in P; treated as an "
        "ordinary register"
    ]
    assert _names(device) == [("D",)]


def test_target_in_another_peripheral_does_not_count():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral("P", 0x0, registers=[Register("X", 0x0, size=32)]),
            Peripheral(
                "Q",
                0x100,
                alternate_sets=[_alt(Register("Y", 0x0, size=32), of="X")],
            ),
        ],
    )
    errors = _messages(resolve_alternates(device), Severity.ERROR)
    assert errors == [
        "Q.Y: alternateRegister 'X' -- no register of that name in Q; treated as an "
        "ordinary register"
    ]


def test_different_offset_leaves_the_views_unrelated():
    device = _device(
        _alt(Register("A", 0x0, size=32)),
        _alt(Register("B", 0x8, size=32), of="A"),
    )
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == [
        "P.B: alternateRegister 'A' is at offset 0x0, not 0x8 -- an alternate view must "
        "share the offset; left unrelated"
    ]
    assert _names(device) == [("A",), ("B",)]


def test_copies_of_a_template_pair_index_with_index():
    device = _device(
        _alt(Register("DT%s", 0x20, size=32, dim=Dim(2, 8))),
        _alt(Register("DTR%s", 0x20, size=32, dim=Dim(2, 8)), of="DT%s"),
    )
    expand_dim(device)
    assert resolve_alternates(device) == []
    assert _names(device) == [("DT0", "DTR0"), ("DT1", "DTR1")]


def test_copy_count_mismatch_is_a_warning():
    device = _device(
        _alt(Register("DT%s", 0x20, size=32, dim=Dim(2, 8))),
        _alt(Register("DTR%s", 0x20, size=32, dim=Dim(3, 8)), of="DT%s"),
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
        _alt(Register("DT%s", 0x20, size=32, dim=Dim(2, 8))),
        _alt(Register("RAW", 0x20, size=32), of="DT%s"),
    )
    expand_dim(device)
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == [
        "P.RAW: alternateRegister names the template 'DT%s' -- resolved to its first copy, DT0"
    ]
    assert _names(device) == [("DT0", "RAW"), ("DT1",)]


def test_arrays_of_equal_shape_are_linked():
    device = _device(
        _alt(Register("CC[%s]", 0x10, size=32, dim=Dim(4, 4))),
        _alt(Register("CCI[%s]", 0x10, size=32, dim=Dim(4, 4)), of="CC[%s]"),
    )
    expand_dim(device)
    assert resolve_alternates(device) == []
    assert _names(device) == [("CC", "CCI")]


def test_arrays_of_different_shape_are_left_unrelated():
    device = _device(
        _alt(Register("CC[%s]", 0x10, size=32, dim=Dim(4, 4))),
        _alt(Register("CCI[%s]", 0x10, size=32, dim=Dim(2, 4)), of="CC[%s]"),
    )
    expand_dim(device)
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == [
        "P.CCI: alternateRegister 'CC' has a different <dim> shape -- left unrelated"
    ]


def test_array_and_single_register_are_different_shapes():
    device = _device(
        _alt(Register("CC[%s]", 0x10, size=32, dim=Dim(4, 4))),
        _alt(Register("X", 0x10, size=32), of="CC[%s]"),
    )
    expand_dim(device)
    warnings = _messages(resolve_alternates(device), Severity.WARNING)
    assert warnings == ["P.X: alternateRegister 'CC' has a different <dim> shape -- left unrelated"]


def test_views_inside_a_cluster_are_linked_per_cluster():
    cluster = Cluster(
        "CH",
        0x10,
        alternate_sets=[
            _alt(Register("XFER_Mem", 0xC, size=32)),
            _alt(Register("XFER_Periph", 0xC, size=32), of="XFER_Mem"),
        ],
    )
    device = _device(_alt(Register("XFER_Mem", 0x0, size=32)), clusters=[cluster])
    assert resolve_alternates(device) == []
    assert _names(device) == [("XFER_Mem",)]  # the peripheral's own is alone
    assert [s.names for s in cluster.alternate_sets] == [("XFER_Mem", "XFER_Periph")]


def test_a_merged_set_sits_where_its_first_view_stood():
    device = _device(
        _alt(Register("A", 0x0, size=32)),
        _alt(Register("B", 0x4, size=32)),
        _alt(Register("A2", 0x0, size=32), of="A"),
    )
    resolve_alternates(device)
    assert _names(device) == [("A", "A2"), ("B",)]


def test_resolving_twice_changes_nothing():
    device = _device(
        _alt(Register("A", 0x0, size=32)),
        _alt(Register("A2", 0x0, size=32), of="A"),
    )
    resolve_alternates(device)
    assert resolve_alternates(device) == []
    assert _names(device) == [("A", "A2")]


def test_a_resolved_set_declares_nothing_any_more():
    device = _device(
        _alt(Register("A", 0x0, size=32)),
        _alt(Register("A2", 0x0, size=32), of="A"),
    )
    resolve_alternates(device)
    assert all(
        alternate_set.joins is None for alternate_set in device.peripherals[0].alternate_sets
    )
