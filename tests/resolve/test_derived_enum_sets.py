"""Enumerated-set derivedFrom: a derived set is a copy of the set it names."""

from regforge.ir import (
    Cluster,
    Device,
    Dim,
    EnumeratedValue,
    EnumSet,
    EnumUsage,
    Field,
    Peripheral,
    Register,
)
from regforge.resolve import expand_dim, resolve_derived


def _modes():
    return EnumSet(
        values=[EnumeratedValue("OFF", 0), EnumeratedValue("ON", 1)],
        name="MODES",
        header_enum_name="mode_t",
        usage=EnumUsage.READ,
    )


def _device(*registers, clusters=(), name="P"):
    peripheral = Peripheral(name, 0x1000, registers=list(registers), clusters=list(clusters))
    return Device(name="Chip", peripherals=[peripheral])


def _reg(name, *fields):
    return Register(name, 0x0, size=32, fields=list(fields))


def _field(name, *sets):
    return Field(name, 0, 1, enum_sets=list(sets))


def test_a_derived_set_is_a_copy_of_the_one_it_names():
    copy_of = EnumSet(derived_from="MODES")
    device = _device(_reg("R", _field("A", _modes()), _field("B", copy_of)))
    assert resolve_derived(device) == []
    assert [(v.name, v.value) for v in copy_of.values] == [("OFF", 0), ("ON", 1)]
    assert copy_of.usage is EnumUsage.READ and copy_of.header_enum_name == "mode_t"


def test_the_entries_are_copies_not_the_bases_own():
    base, copy_of = _modes(), EnumSet(derived_from="MODES")
    resolve_derived(_device(_reg("R", _field("A", base), _field("B", copy_of))))
    assert copy_of.values[0] is not base.values[0]
    copy_of.values[0].name = "CHANGED"
    assert base.values[0].name == "OFF"


def test_a_derived_set_keeps_its_own_name_and_values():
    own = EnumSet(values=[EnumeratedValue("ONLY", 3)], name="MINE", derived_from="MODES")
    resolve_derived(_device(_reg("R", _field("A", _modes()), _field("B", own))))
    assert own.name == "MINE" and [v.name for v in own.values] == ["ONLY"]


def test_a_usage_the_derived_set_states_itself_is_kept():
    own = EnumSet(usage=EnumUsage.WRITE, derived_from="MODES")
    resolve_derived(_device(_reg("R", _field("A", _modes()), _field("B", own))))
    assert own.usage is EnumUsage.WRITE and len(own.values) == 2


def test_a_catch_all_entry_is_copied_too():
    base = EnumSet(
        values=[EnumeratedValue("ZERO", 0), EnumeratedValue("REST", None, is_default=True)]
    )
    base.name = "MODES"
    copy_of = EnumSet(derived_from="MODES")
    resolve_derived(_device(_reg("R", _field("A", base), _field("B", copy_of))))
    assert copy_of.default_entry is not None and copy_of.default_entry.name == "REST"


def test_a_path_names_the_field_the_register_and_the_peripheral():
    for written in ("MODES", "A.MODES", "R.A.MODES", "P.R.A.MODES"):
        copy_of = EnumSet(derived_from=written)
        device = _device(_reg("R", _field("A", _modes())), _reg("Q", _field("B", copy_of)))
        assert resolve_derived(device) == [], written
        assert len(copy_of.values) == 2, written


def test_a_path_may_go_through_clusters():
    copy_of = EnumSet(derived_from="CH.R.A.MODES")
    cluster = Cluster("CH", 0x10, registers=[_reg("R", _field("A", _modes()))])
    device = _device(_reg("Q", _field("B", copy_of)), clusters=[cluster])
    assert resolve_derived(device) == []
    assert len(copy_of.values) == 2


def test_a_path_may_start_in_another_peripheral():
    copy_of = EnumSet(derived_from="UART.R.A.MODES")
    uart = Peripheral("UART", 0x0, registers=[_reg("R", _field("A", _modes()))])
    user = Peripheral("X", 0x100, registers=[_reg("Q", _field("B", copy_of))])
    assert resolve_derived(Device(name="Chip", peripherals=[uart, user])) == []
    assert len(copy_of.values) == 2


def test_the_nearest_set_of_that_name_is_used():
    # MODES is declared twice. The register's own wins over the one in the register before.
    far, near = _modes(), _modes()
    far.values = [EnumeratedValue("FAR", 9)]
    copy_of = EnumSet(derived_from="MODES")
    device = _device(
        _reg("First", _field("A", far)),
        _reg("Second", _field("B", near), _field("C", copy_of)),
    )
    assert resolve_derived(device) == []
    assert [v.name for v in copy_of.values] == ["OFF", "ON"]


def test_a_set_in_the_same_peripheral_beats_one_in_another():
    elsewhere = _modes()
    elsewhere.values = [EnumeratedValue("ELSEWHERE", 7)]
    copy_of = EnumSet(derived_from="MODES")
    here = Peripheral(
        "HERE", 0x0, registers=[_reg("R", _field("A", _modes()), _field("B", copy_of))]
    )
    other = Peripheral("OTHER", 0x100, registers=[_reg("R", _field("A", elsewhere))])
    resolve_derived(Device(name="Chip", peripherals=[other, here]))
    assert [v.name for v in copy_of.values] == ["OFF", "ON"]


def test_two_equally_near_sets_are_reported_and_the_first_is_used():
    first, second = _modes(), _modes()
    second.values = [EnumeratedValue("SECOND", 5)]
    copy_of = EnumSet(derived_from="MODES")
    device = _device(_reg("R", _field("A", first), _field("B", second), _field("C", copy_of)))
    warnings = resolve_derived(device)
    assert warnings == [
        "P.R.C: derivedFrom 'MODES' names 2 equally near sets -- used the first, in P.R.A"
    ]
    assert [v.name for v in copy_of.values] == ["OFF", "ON"]


def test_an_unknown_base_is_reported_and_nothing_is_inherited():
    copy_of = EnumSet(derived_from="NOPE")
    warnings = resolve_derived(_device(_reg("R", _field("A", copy_of))))
    assert warnings == ["P.R.A: derivedFrom 'NOPE' -- no such enumeratedValues; nothing inherited"]
    assert copy_of.values == []


def test_a_set_cannot_be_its_own_base():
    own = EnumSet(name="MODES", derived_from="MODES")
    warnings = resolve_derived(_device(_reg("R", _field("A", own))))
    assert len(warnings) == 1 and "no such enumeratedValues" in warnings[0]


def test_a_cycle_is_reported_once_and_does_not_hang():
    a = EnumSet(name="A_SET", derived_from="B_SET")
    b = EnumSet(name="B_SET", derived_from="A_SET")
    warnings = resolve_derived(_device(_reg("R", _field("A", a), _field("B", b))))
    assert len(warnings) == 1 and "is a cycle" in warnings[0]


def test_a_chain_inherits_through_its_root_even_out_of_order():
    last = EnumSet(name="C_SET", derived_from="B_SET")
    middle = EnumSet(name="B_SET", derived_from="MODES")
    device = _device(_reg("R", _field("X", last), _field("Y", middle), _field("Z", _modes())))
    assert resolve_derived(device) == []
    assert len(last.values) == 2


def test_a_copied_peripheral_resolves_within_itself():
    # UART1 is a copy of UART0; its derived set must find UART1's own base, not UART0's.
    copy_of = EnumSet(derived_from="MODES")
    uart0 = Peripheral(
        "UART0", 0x0, registers=[_reg("R", _field("A", _modes()), _field("B", copy_of))]
    )
    uart1 = Peripheral("UART1", 0x100, derived_from="UART0")
    device = Device(name="Chip", peripherals=[uart0, uart1])
    assert resolve_derived(device) == []
    copied = uart1.registers[0].fields[1].enum_sets[0]
    assert (
        copied.values
        and copied.values[0] is not uart0.registers[0].fields[0].enum_sets[0].values[0]
    )
    assert copied is not copy_of


def test_a_template_in_the_path_means_any_of_its_copies():
    base_register = Register(
        "CH%s", 0x0, size=32, fields=[_field("A", _modes())], dim=Dim(count=2, increment=4)
    )
    copy_of = EnumSet(derived_from="CH%s.A.MODES")
    user = _reg("Q", _field("B", copy_of))
    device = _device(base_register, user)
    expand_dim(device)
    assert resolve_derived(device) == [
        "P.Q.B: derivedFrom 'CH%s.A.MODES' names 2 equally near sets -- used the first, in P.CH0.A"
    ]
    assert len(copy_of.values) == 2


def test_the_field_then_reports_the_derived_names_and_numbers():
    copy_of = EnumSet(derived_from="MODES", usage=EnumUsage.READ)
    field_ = _field("B", copy_of)
    resolve_derived(_device(_reg("R", _field("A", _modes()), field_)))
    assert field_.enum_name(1) == "ON" and field_.enum_value("OFF", EnumUsage.READ) == 0
