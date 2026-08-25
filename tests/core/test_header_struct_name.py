"""headerStructName: the vendor's preferred name for the generated struct.

Precedence, one rule: headerStructName -> the derivedFrom/groupName family label
-> the root instance's own name. It names the type only; grouping is still
decided by layout, so a vendor name never merges or splits anything.
"""

from regforge.families import group_families
from regforge.ir import Device, Peripheral, Register
from regforge.resolve import resolve_defaults, resolve_derived


def _resolved(*peripherals: Peripheral) -> Device:
    device = Device(name="Chip", peripherals=list(peripherals))
    resolve_defaults(device)
    resolve_derived(device)
    return device


def _p(name, base, group=None, hsn=None, regs=("A",), derived=None):
    return Peripheral(
        name=name,
        base_address=base,
        group_name=group,
        header_struct_name=hsn,
        derived_from=derived,
        registers=[Register(r, 0x4 * i, size=32) for i, r in enumerate(regs)],
    )


def _names(device: Device) -> list[str]:
    return [family.name for family in group_families(device)]


def test_falls_back_to_the_root_instance_name():
    # No groupName and no vendor name: the type is named after instance zero.
    device = _resolved(
        _p("ADC0", 0x0),
        Peripheral(name="ADC1", base_address=0x100, derived_from="ADC0"),
    )
    assert _names(device) == ["ADC0"]


def test_group_name_beats_the_instance_name():
    device = _resolved(_p("UART0", 0x0, group="UART"), _p("UART1", 0x100, group="UART"))
    assert _names(device) == ["UART"]


def test_vendor_name_beats_the_instance_name():
    # Cypress psoc63: DW0 carries headerStructName=DW and has no groupName.
    device = _resolved(_p("DW0", 0x0, hsn="DW"))
    assert _names(device) == ["DW"]


def test_vendor_name_beats_the_group_name():
    # Infineon XMC: CAN_NODE0 is grouped under CAN because it is a CAN thing,
    # but its struct is a CAN *node*. Naming the type can_t would be wrong.
    device = _resolved(_p("CAN_NODE0", 0x0, group="CAN", hsn="CAN_NODE"))
    assert _names(device) == ["CAN_NODE"]


def test_vendor_name_is_inherited_through_derived_from():
    # nRF relies on this: only SPIM0 carries headerStructName; SPIM1 derives.
    device = _resolved(
        _p("SPIM0", 0x0, group="SPIM", hsn="SPIM", regs=("TASKS_START",)),
        Peripheral(name="SPIM1", base_address=0x1000, group_name="SPIM", derived_from="SPIM0"),
    )
    families = group_families(device)
    assert [f.name for f in families] == ["SPIM"]
    assert [i.name for i in families[0].instances] == ["SPIM0", "SPIM1"]
    assert device.peripherals[1].header_struct_name == "SPIM"  # inherited


def test_declared_vendor_name_is_not_overwritten_by_the_base():
    device = _resolved(
        _p("A0", 0x0, hsn="BASE", regs=("R",)),
        Peripheral(name="A1", base_address=0x100, derived_from="A0", header_struct_name="OWN"),
    )
    assert device.peripherals[1].header_struct_name == "OWN"


def test_vendor_name_does_not_merge_unrelated_peripherals():
    # Two peripherals sharing a vendor name but linked by nothing stay separate
    # types: a shared name is not a claim about layout (the no-heuristics rule).
    device = _resolved(
        _p("A", 0x0, hsn="SHARED", regs=("R",)),
        _p("B", 0x100, hsn="SHARED", regs=("R", "S")),
    )
    families = group_families(device)
    assert len(families) == 2
    assert len({f.name.lower() for f in families}) == 2  # and they must not collide


def test_vendor_name_does_not_split_a_matching_family():
    # Same layout, same group, different vendor names on each member: grouping
    # ignores the name, so they remain one type (named from the root).
    device = _resolved(
        _p("T0", 0x0, group="T", hsn="TEE", regs=("R",)),
        _p("T1", 0x100, group="T", hsn="OTHER", regs=("R",)),
    )
    families = group_families(device)
    assert len(families) == 1
    assert families[0].name == "TEE"  # the root's vendor name wins


def test_split_family_gives_each_subgroup_its_own_vendor_name():
    # XMC's CAN group holds CAN_NODE0 and CAN_MO with different layouts. Each
    # subgroup takes the name its own vendor string asks for.
    device = _resolved(
        _p("CAN_NODE0", 0x0, group="CAN", hsn="CAN_NODE", regs=("NCR",)),
        _p("CAN_MO", 0x100, group="CAN", hsn="CAN_MO_CLUSTER", regs=("MOFCR", "MOFGPR")),
    )
    assert sorted(_names(device)) == ["CAN_MO_CLUSTER", "CAN_NODE"]


def test_namesake_rule_still_applies_without_a_vendor_name():
    # The FPU case must not regress: no headerStructName anywhere, so the
    # peripheral literally named FPU keeps the plain group label.
    device = _resolved(
        _p("FPU_CPACR", 0x0, group="FPU", regs=("CPACR",)),
        _p("FPU", 0x100, group="FPU", regs=("FPCCR", "FPCAR")),
    )
    assert sorted(_names(device)) == ["FPU", "FPU_CPACR"]


def test_every_combination_of_the_three_naming_inputs():
    # The whole precedence as one table: headerStructName -> groupName -> the
    # root instance's own name. A peripheral always has a name, so the other two
    # are what vary.
    cases = [
        # (groupName, headerStructName, expected type name)
        (None, None, "P0"),  # nothing declared -> named after instance zero
        ("GRP", None, "GRP"),  # the family label
        (None, "HSN", "HSN"),  # the vendor's name, no group at all
        ("GRP", "HSN", "HSN"),  # vendor name outranks the family label
        ("", None, "P0"),  # empty group is not a name
        (None, "", "P0"),  # empty vendor name is not a name
        ("", "", "P0"),  # neither is
        ("GRP", "", "GRP"),  # empty vendor name falls through to the group
    ]
    for group, hsn, expected in cases:
        device = _resolved(_p("P0", 0x0, group=group, hsn=hsn))
        assert _names(device) == [expected], f"groupName={group!r} headerStructName={hsn!r}"


def test_every_combination_survives_derived_from():
    # Same table, but the values sit on the base and the family is reached
    # through a derived instance. The chain root decides the name.
    cases = [
        (None, None, "BASE"),
        ("GRP", None, "GRP"),
        (None, "HSN", "HSN"),
        ("GRP", "HSN", "HSN"),
    ]
    for group, hsn, expected in cases:
        device = _resolved(
            _p("BASE", 0x0, group=group, hsn=hsn, regs=("R",)),
            Peripheral(name="DERIVED", base_address=0x100, group_name=group, derived_from="BASE"),
        )
        families = group_families(device)
        assert [f.name for f in families] == [expected], f"group={group!r} hsn={hsn!r}"
        assert [i.name for i in families[0].instances] == ["BASE", "DERIVED"]


def test_group_name_without_vendor_name_on_a_multi_instance_family():
    # The common shape: groupName groups them, no vendor name anywhere, so the
    # label names the type and each instance gets an alias.
    device = _resolved(
        _p("TIM2", 0x0, group="TIM", regs=("CR1",)),
        _p("TIM3", 0x100, group="TIM", regs=("CR1",)),
    )
    families = group_families(device)
    assert families[0].name == "TIM"
    assert [i.name for i in families[0].instances] == ["TIM2", "TIM3"]


def test_instance_name_only_on_a_multi_instance_family():
    # No groupName and no vendor name, linked only by derivedFrom: the root
    # instance names the type, which is the ugliness headerStructName exists
    # to fix.
    device = _resolved(
        _p("ADC0", 0x0, regs=("CR",)),
        Peripheral(name="ADC1", base_address=0x100, derived_from="ADC0"),
    )
    assert _names(device) == ["ADC0"]


def test_vendor_name_on_the_derived_instance_only():
    # The base is silent and the derived declares the name. Grouping follows the
    # chain root, so the root's (absent) name still decides the family name --
    # the derived instance's own string does not rename the shared type.
    device = _resolved(
        _p("A0", 0x0, regs=("R",)),
        Peripheral(name="A1", base_address=0x100, derived_from="A0", header_struct_name="LATE"),
    )
    families = group_families(device)
    assert [f.name for f in families] == ["A0"]
    assert [i.name for i in families[0].instances] == ["A0", "A1"]


def test_group_name_on_derived_differing_from_the_base():
    # Grouping uses the chain root's label, so a derived peripheral relabelling
    # itself does not escape its base's family.
    device = _resolved(
        _p("X0", 0x0, group="XGRP", regs=("R",)),
        Peripheral(name="X1", base_address=0x100, group_name="OTHER", derived_from="X0"),
    )
    families = group_families(device)
    assert [f.name for f in families] == ["XGRP"]
    assert [i.name for i in families[0].instances] == ["X0", "X1"]
