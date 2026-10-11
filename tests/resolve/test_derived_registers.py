"""Register derivedFrom: a derived register inherits what it leaves unsaid from its base."""

from regforge.ir import Access, AlternateSet, Cluster, Device, Dim, Field, Peripheral, Register
from regforge.resolve import expand_dim, resolve_defaults, resolve_derived


def _base():
    return Register(
        "CTRL",
        0x0,
        size=16,
        reset_value=0x5,
        reset_mask=0xFF,
        access=Access.READ_ONLY,
        description="Control",
        display_name="Control register",
        fields=[Field("EN", 0, 1), Field("MODE", 1, 3)],
    )


def _device(*registers, clusters=()):
    return Device(
        name="Chip",
        peripherals=[
            Peripheral("P", 0x1000, registers=list(registers), clusters=list(clusters)),
        ],
    )


def test_a_derived_register_takes_what_it_leaves_unsaid():
    derived = Register("CTRL2", 0x4, derived_from="CTRL")
    device = _device(_base(), derived)
    assert resolve_derived(device) == []
    assert (derived.size, derived.reset_value, derived.reset_mask) == (16, 0x5, 0xFF)
    assert derived.access is Access.READ_ONLY
    assert derived.description == "Control" and derived.display_name == "Control register"
    assert [f.name for f in derived.fields] == ["EN", "MODE"]


def test_a_derived_register_keeps_its_own_name_offset_and_values():
    derived = Register("CTRL2", 0x4, size=8, description="Second", derived_from="CTRL")
    resolve_derived(_device(_base(), derived))
    assert (derived.name, derived.address_offset) == ("CTRL2", 0x4)
    assert derived.size == 8 and derived.description == "Second"


def test_the_fields_are_copies_not_the_bases_own():
    base, derived = _base(), Register("CTRL2", 0x4, derived_from="CTRL")
    resolve_derived(_device(base, derived))
    assert derived.fields[0] is not base.fields[0]
    derived.fields[0].name = "CHANGED"
    assert base.fields[0].name == "EN"


def test_a_field_of_its_own_replaces_the_one_of_the_same_name_and_others_are_added():
    own = [Field("MODE", 1, 2), Field("EXTRA", 8, 1)]
    derived = Register("CTRL2", 0x4, fields=own, derived_from="CTRL")
    resolve_derived(_device(_base(), derived))
    assert [f.name for f in derived.fields] == ["EN", "MODE", "EXTRA"]
    assert derived.fields[1] is own[0] and derived.fields[1].bit_width == 2


def test_the_dim_and_the_alternate_declaration_are_not_inherited():
    base = _base()
    base.dim = Dim(count=2, increment=4, array=True)
    derived = Register("CTRL2", 0x4, derived_from="CTRL")
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                "P",
                0x1000,
                alternate_sets=[AlternateSet((base,), joins="OTHER"), AlternateSet((derived,))],
            )
        ],
    )
    resolve_derived(device)
    assert derived.dim is None
    assert [s.joins for s in device.peripherals[0].alternate_sets] == ["OTHER", None]


def test_a_chain_inherits_through_its_root_even_out_of_order():
    last = Register("C", 0x8, derived_from="B")
    middle = Register("B", 0x4, derived_from="A")
    first = _base()
    first.name = "A"
    resolve_derived(_device(last, middle, first))
    assert last.size == 16 and [f.name for f in last.fields] == ["EN", "MODE"]


def test_values_the_base_left_to_its_defaults_resolve_under_the_derived_registers_own():
    # The base states no size: it takes its peripheral's. The derived register sits in a
    # cluster with another default, and resolves under that one, as a copy of a peripheral does.
    base = Register("R", 0x0)
    derived = Register("R2", 0x0, derived_from="R")
    cluster = Cluster("C", 0x10, registers=[derived], default_size=8)
    device = _device(base, clusters=[cluster])
    device.peripherals[0].default_size = 32
    resolve_derived(device)
    resolve_defaults(device)
    assert base.size == 32 and derived.size == 8


def test_a_path_names_the_peripheral_then_the_register():
    uart = Peripheral("UART", 0x0, registers=[_base()])
    user = Register("MINE", 0x0, derived_from="UART.CTRL")
    device = Device(name="Chip", peripherals=[uart, Peripheral("X", 0x100, registers=[user])])
    assert resolve_derived(device) == []
    assert user.size == 16 and [f.name for f in user.fields] == ["EN", "MODE"]


def test_a_path_may_go_through_clusters():
    inner = Cluster("CH", 0x10, registers=[_base()])
    user = Register("MINE", 0x0, derived_from="P.CH.CTRL")
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral("P", 0x0, clusters=[inner]),
            Peripheral("X", 0x100, registers=[user]),
        ],
    )
    assert resolve_derived(device) == []
    assert user.size == 16


def test_a_path_from_the_peripheral_works_inside_a_cluster_too():
    user = Register("MINE", 0x0, derived_from="CTRL")
    cluster = Cluster("CH", 0x10, registers=[user])
    resolve_derived(_device(_base(), clusters=[cluster]))
    assert user.size == 16  # CTRL sits in the peripheral, not in the cluster


def test_a_bare_name_is_read_in_the_registers_own_cluster_first():
    near, far = _base(), _base()
    near.size, far.size = 8, 64
    user = Register("MINE", 0x0, derived_from="CTRL")
    cluster = Cluster("CH", 0x10, registers=[near, user])
    resolve_derived(_device(far, clusters=[cluster]))
    assert user.size == 8


def test_an_unknown_base_is_reported_and_nothing_is_inherited():
    user = Register("MINE", 0x0, derived_from="NOPE")
    warnings = resolve_derived(_device(user))
    assert warnings == ["P.MINE: derivedFrom 'NOPE' -- no such register; nothing inherited"]
    assert user.size is None and user.fields == []


def test_a_register_that_derives_from_itself_is_reported():
    user = Register("MINE", 0x0, derived_from="MINE")
    warnings = resolve_derived(_device(user))
    assert warnings == ["P.MINE: derivedFrom names itself -- nothing inherited"]


def test_a_cycle_is_reported_once_and_does_not_hang():
    a = Register("A", 0x0, size=8, derived_from="B")
    b = Register("B", 0x4, derived_from="A")
    warnings = resolve_derived(_device(a, b))
    assert len(warnings) == 1 and "cycle" in warnings[0]


def _pmux():
    """The SAM D shape: PMUX1_%s derives from PMUX0_%s, both templates of 4 copies."""
    base = Register(
        "PMUX0_%s",
        0x30,
        size=8,
        fields=[Field("PMUXE", 0, 4), Field("PMUXO", 4, 4)],
        dim=Dim(count=4, increment=1),
    )
    derived = Register("PMUX1_%s", 0xB0, derived_from="PMUX0_%s", dim=Dim(count=4, increment=1))
    return _device(base, derived)


def test_a_template_copy_takes_the_copy_of_the_same_index():
    device = _pmux()
    expand_dim(device)
    assert resolve_derived(device) == []
    copies = [r for r in device.peripherals[0].registers if r.name.startswith("PMUX1_")]
    assert [r.name for r in copies] == ["PMUX1_0", "PMUX1_1", "PMUX1_2", "PMUX1_3"]
    assert all(r.size == 8 and [f.name for f in r.fields] == ["PMUXE", "PMUXO"] for r in copies)
    assert copies[2].derived_from == "PMUX0_2"


def test_a_plain_register_naming_a_template_takes_its_first_copy_with_a_warning():
    device = _pmux()
    user = Register("MINE", 0x0, derived_from="PMUX0_%s")
    device.peripherals[0].alternate_sets.append(AlternateSet((user,)))
    expand_dim(device)
    warnings = resolve_derived(device)
    assert warnings == [
        "P.MINE: derivedFrom names the template 'PMUX0_%s' -- resolved to its first copy, PMUX0_0"
    ]
    assert user.size == 8 and user.derived_from == "PMUX0_0"


def test_a_template_with_a_different_number_of_copies_takes_the_first_and_says_so():
    device = _pmux()
    device.peripherals[0].registers[1].dim = Dim(count=2, increment=1)
    expand_dim(device)
    warnings = resolve_derived(device)
    assert len(warnings) == 2 and all("has 4 copies, not 2" in w for w in warnings)
    copies = [r for r in device.peripherals[0].registers if r.name.startswith("PMUX1_")]
    assert all(r.size == 8 for r in copies)


def test_a_path_may_name_a_template_in_another_peripheral():
    port = _pmux().peripherals[0]
    port.name = "PORT"
    user = Register("MINE", 0x0, derived_from="PORT.PMUX0_%s")
    device = Device(name="Chip", peripherals=[port, Peripheral("X", 0x100, registers=[user])])
    expand_dim(device)
    assert len(resolve_derived(device)) == 1  # the template warning, nothing else
    assert user.size == 8


def test_an_array_is_named_with_its_brackets_or_without():
    array = _base()
    array.name = "CC[%s]"
    array.dim = Dim(count=2, increment=4)
    user = Register("MINE", 0x40, derived_from="CC[%s]")
    plain = Register("OTHER", 0x44, derived_from="CC")
    device = _device(array, user, plain)
    expand_dim(device)
    assert resolve_derived(device) == []
    assert user.size == 16 and plain.size == 16
