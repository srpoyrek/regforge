"""alternateGroup: a label on the register; only a name another register shares renames it."""

from regforge.ir import AlternateSet, Cluster, Device, Dim, Peripheral, Register
from regforge.resolve import expand_dim, resolve_alternates, resolve_derived


def _alt(register: Register, of: str | None = None) -> AlternateSet:
    """The set the reader makes for ``register``, which declared itself an alternate of ``of``."""
    return AlternateSet((register,), joins=of)


def _device(*registers: Register, clusters: list[Cluster] | None = None) -> Device:
    return Device(
        name="Chip",
        peripherals=[
            Peripheral("P", 0x0, registers=list(registers), clusters=list(clusters or []))
        ],
    )


def _names(device: Device) -> list[str]:
    return [register.name for register in device.peripherals[0].registers]


def _sets(device: Device) -> list[tuple[str, ...]]:
    return [alternate_set.names for alternate_set in device.peripherals[0].alternate_sets]


def test_a_group_whose_name_nothing_shares_is_only_a_label():
    # A Fujitsu-style file: every register carries a group, none reuses a name.
    tmcr = Register("PWM_TMCR", 0x0, size=32, alternate_group="PWM")
    ctrl = Register("PWM_CTRL", 0x4, size=32, alternate_group="PWM")
    device = _device(tmcr, ctrl)
    assert resolve_alternates(device) == []
    assert _names(device) == ["PWM_TMCR", "PWM_CTRL"]
    assert tmcr.alternate_group == "PWM"
    assert _sets(device) == [("PWM_TMCR",), ("PWM_CTRL",)]


def test_no_link_to_a_register_that_does_not_exist_is_invented():
    device = _device(Register("TMCR", 0x0, size=32, alternate_group="PWM"))
    assert resolve_alternates(device) == []  # no "no register of that name" error


def test_a_name_reused_in_another_group_is_renamed_and_linked_to_the_plain_register():
    plain = Register("DR", 0x4, size=32)
    cal = Register("DR", 0x4, size=32, alternate_group="Cal")
    device = _device(plain, cal)
    assert resolve_alternates(device) == []
    assert _names(device) == ["DR", "DR_Cal"]
    assert _sets(device) == [("DR", "DR_Cal")]


def test_the_group_stays_on_the_register_after_the_rename():
    cal = Register("DR", 0x4, size=32, alternate_group="Cal")
    resolve_alternates(_device(Register("DR", 0x4, size=32), cal))
    assert cal.name == "DR_Cal" and cal.alternate_group == "Cal"


def test_three_views_of_one_name_are_one_set_with_the_plain_register_first():
    plain = Register("DR", 0x4, size=32)
    cal = Register("DR", 0x4, size=32, alternate_group="Cal")
    raw = Register("DR", 0x4, size=32, alternate_group="Raw")
    device = _device(cal, raw, plain)
    assert resolve_alternates(device) == []
    assert _names(device) == ["DR", "DR_Cal", "DR_Raw"]
    assert _sets(device) == [("DR", "DR_Cal", "DR_Raw")]


def test_when_every_register_of_the_name_is_grouped_the_first_is_the_primary():
    a = Register("CTRL", 0x0, size=32, alternate_group="A")
    b = Register("CTRL", 0x0, size=32, alternate_group="B")
    device = _device(a, b)
    assert resolve_alternates(device) == []
    assert _names(device) == ["CTRL_A", "CTRL_B"]
    assert _sets(device) == [("CTRL_A", "CTRL_B")]


def test_an_explicit_alternate_register_beside_the_group_is_kept_as_written():
    plain = Register("DR", 0x4, size=32)
    raw = Register("DR", 0x4, size=32, alternate_group="Raw")
    device = Device(
        name="Chip",
        peripherals=[Peripheral("P", 0x0, alternate_sets=[_alt(plain), _alt(raw, of="DR")])],
    )
    assert resolve_alternates(device) == []
    assert raw.name == "DR_Raw"
    assert _sets(device) == [("DR", "DR_Raw")]


def test_the_same_name_at_another_offset_is_renamed_but_not_linked():
    # Two different registers that happen to share a name: no view, and no finding.
    spi = Register("CTRL", 0x0, size=32, alternate_group="SPI")
    i2c = Register("CTRL", 0x10, size=32, alternate_group="I2C")
    device = _device(spi, i2c)
    assert resolve_alternates(device) == []
    assert _names(device) == ["CTRL_SPI", "CTRL_I2C"]
    assert _sets(device) == [("CTRL_SPI",), ("CTRL_I2C",)]


def test_the_same_name_with_another_shape_is_renamed_but_not_linked():
    plain = Register("DR", 0x4, size=32)
    many = Register("DR", 0x4, size=32, alternate_group="Cal", dim=Dim(count=2, increment=4))
    device = _device(plain, many)
    assert resolve_alternates(device) == []
    assert _names(device) == ["DR", "DR_Cal"]
    assert _sets(device) == [("DR",), ("DR_Cal",)]


def test_a_name_in_another_peripheral_is_not_a_collision():
    other = Peripheral("Q", 0x100, registers=[Register("DR", 0x4, size=32)])
    mine = Peripheral("P", 0x0, registers=[Register("DR", 0x4, size=32, alternate_group="Cal")])
    device = Device(name="Chip", peripherals=[mine, other])
    assert resolve_alternates(device) == []
    assert mine.registers[0].name == "DR"


def test_a_collision_inside_a_cluster_is_renamed_and_linked_there():
    plain = Register("DR", 0x4, size=32)
    cal = Register("DR", 0x4, size=32, alternate_group="Cal")
    cluster = Cluster("CH", 0x10, registers=[plain, cal])
    device = _device(clusters=[cluster])
    assert resolve_alternates(device) == []
    assert cal.name == "DR_Cal"
    assert [s.names for s in cluster.alternate_sets] == [("DR", "DR_Cal")]


def test_two_plain_registers_of_one_name_are_left_for_the_layout_to_refuse():
    first, second = Register("DR", 0x0, size=32), Register("DR", 0x4, size=32)
    device = _device(first, second)
    assert resolve_alternates(device) == []
    assert _names(device) == ["DR", "DR"]


def test_the_copies_of_a_template_pair_with_the_copies_of_the_plain_one():
    plain = Register("R%s", 0x0, size=32, dim=Dim(count=2, increment=4))
    cal = Register("R%s", 0x0, size=32, dim=Dim(count=2, increment=4), alternate_group="Cal")
    device = _device(plain, cal)
    expand_dim(device)
    assert resolve_alternates(device) == []
    assert _names(device) == ["R0", "R0_Cal", "R1", "R1_Cal"]
    assert _sets(device) == [("R0", "R0_Cal"), ("R1", "R1_Cal")]


def test_a_derived_peripherals_registers_are_renamed_in_their_own_block():
    base = Peripheral(
        "ADC0",
        0x0,
        registers=[
            Register("DR", 0x4, size=32),
            Register("DR", 0x4, size=32, alternate_group="Cal"),
        ],
    )
    copy_of = Peripheral("ADC1", 0x100, derived_from="ADC0")
    device = Device(name="Chip", peripherals=[base, copy_of])
    resolve_derived(device)
    assert resolve_alternates(device) == []
    assert [r.name for r in copy_of.registers] == ["DR", "DR_Cal"]
    assert [s.names for s in copy_of.alternate_sets] == [("DR", "DR_Cal")]


def test_a_register_derived_from_a_grouped_one_finds_it_by_the_name_it_was_declared_with():
    # Fujitsu: TIMER2LOAD derives from TIMER1LOAD, which sits in a group and is not renamed.
    base = Register("TIMER1LOAD", 0x0, size=32, alternate_group="DualTimer1")
    derived = Register("TIMER2LOAD", 0x20, derived_from="TIMER1LOAD", alternate_group="DualTimer2")
    device = _device(base, derived)
    assert resolve_derived(device) == []
    assert derived.size == 32
    assert resolve_alternates(device) == []
    assert _names(device) == ["TIMER1LOAD", "TIMER2LOAD"]
