"""Every emitted type name must be unique.

A family becomes one C typedef and an instance alias becomes another. Two of
either sharing a name is a redefinition the compiler rejects, and the build
breaks in the user's project naming neither peripheral. These cases come from
real vendor files: STM32's FPU beside FPU_CPACR, Nuvoton's GPIO beside a GPIO
group, Infineon's CAN beside CAN_MO0..63.
"""

from regforge.families import group_families
from regforge.ir import Device, Peripheral, Register
from regforge.resolve import resolve_defaults, resolve_derived
from regforge.writers.c import _alias_map


def _resolved(*peripherals: Peripheral) -> Device:
    device = Device(name="Chip", peripherals=list(peripherals))
    resolve_defaults(device)
    resolve_derived(device)
    return device


def _emitted(device: Device) -> list[str]:
    """Every type name the C writer would emit, in order."""
    families = group_families(device)
    aliases = _alias_map(families)
    names: list[str] = []
    for family in families:
        names.append(family.name.lower())
        names.extend(instance.name.lower() for instance in aliases[id(family)])
    return names


def _assert_unique(device: Device) -> list[str]:
    names = _emitted(device)
    assert len(names) == len(set(names)), f"duplicate type name in {names}"
    return names


def _p(name, offset, group=None, regs=("A",), derived=None):
    return Peripheral(
        name=name,
        base_address=offset,
        group_name=group,
        derived_from=derived,
        registers=[Register(r, 0x4 * i, size=32) for i, r in enumerate(regs)],
    )


def test_split_group_gives_the_plain_name_to_its_namesake():
    # STM32F7: FPU and FPU_CPACR both groupName=FPU with different layouts.
    # The peripheral actually called FPU must own fpu_t.
    device = _resolved(
        _p("FPU_CPACR", 0x0, group="FPU", regs=("CPACR",)),
        _p("FPU", 0x100, group="FPU", regs=("FPCCR", "FPCAR", "FPDSCR")),
    )
    names = _assert_unique(device)
    assert "fpu" in names and "fpu_cpacr" in names


def test_namesake_wins_regardless_of_declaration_order():
    # The bug was order-dependent: equal-sized subgroups tie, so file order
    # decided who got the plain name. Both orders must now agree.
    first = _resolved(
        _p("FPU", 0x0, group="FPU", regs=("FPCCR",)),
        _p("FPU_CPACR", 0x100, group="FPU", regs=("CPACR", "EXTRA")),
    )
    second = _resolved(
        _p("FPU_CPACR", 0x100, group="FPU", regs=("CPACR", "EXTRA")),
        _p("FPU", 0x0, group="FPU", regs=("FPCCR",)),
    )
    assert sorted(_assert_unique(first)) == sorted(_assert_unique(second)) == ["fpu", "fpu_cpacr"]


def test_namesake_wins_even_when_it_is_the_smaller_subgroup():
    # Infineon XMC4100: one CAN peripheral against CAN_MO0..3. The lone CAN
    # still owns can_t; the 4-member subgroup is named after its own root.
    device = _resolved(
        _p("CAN_MO0", 0x0, group="CAN", regs=("MOFCR", "MOFGPR")),
        _p("CAN_MO1", 0x10, group="CAN", regs=("MOFCR", "MOFGPR")),
        _p("CAN_MO2", 0x20, group="CAN", regs=("MOFCR", "MOFGPR")),
        _p("CAN", 0x100, group="CAN", regs=("CLC",)),
    )
    names = _assert_unique(device)
    assert "can" in names and "can_mo0" in names


def test_no_namesake_keeps_the_largest_subgroup_rule():
    # minimal.svd's TIM case: no peripheral is called plain TIM, so the largest
    # identical subgroup keeps the group name and the outlier is named after
    # itself. This is the pre-existing behaviour and must not drift.
    device = _resolved(
        _p("TIM1", 0x0, group="TIM", regs=("CR1", "ARR", "RCR")),
        _p("TIM2", 0x100, group="TIM", regs=("CR1", "ARR")),
        _p("TIM3", 0x200, group="TIM", regs=("CR1", "ARR")),
    )
    names = _assert_unique(device)
    assert "tim" in names and "tim1" in names


def test_alias_yields_to_a_family_that_owns_the_name():
    # Nuvoton M051: a peripheral literally named GPIO sits in the GPIO_GCR
    # group, while a separate GPIO group covers GP0/GP1. The alias for that
    # instance would redefine the group's type, so it is not emitted.
    device = _resolved(
        _p("GP0", 0x0, group="GPIO", regs=("PMD",)),
        _p("GP1", 0x40, group="GPIO", regs=("PMD",)),
        _p("GPIO", 0x100, group="GPIO_GCR", regs=("DBNCECON", "OTHER")),
    )
    names = _assert_unique(device)
    assert "gpio" in names  # owned by the GP0/GP1 group
    assert "gpio_gcr" in names  # the lone peripheral's own family
    assert names.count("gpio") == 1


def test_two_aliases_cannot_claim_one_name():
    # Distinct families whose instances share a name: only the first alias can
    # take it. (A device really shipping this has a vendor bug; regforge must
    # still emit compilable C.)
    device = _resolved(
        _p("A0", 0x0, group="FAM1", regs=("R",)),
        _p("SHARED", 0x40, group="FAM1", regs=("R",)),
        _p("B0", 0x100, group="FAM2", regs=("R", "S")),
        _p("SHARED2", 0x140, group="FAM2", regs=("R", "S")),
    )
    _assert_unique(device)


def test_derived_instances_do_not_collide_with_their_base_type():
    # UART1 derivedFrom UART0 shares uart_t; each instance still gets its own
    # alias and none of the three names repeat.
    device = _resolved(
        _p("UART0", 0x0, group="UART", regs=("DR", "SR")),
        Peripheral(name="UART1", base_address=0x100, group_name="UART", derived_from="UART0"),
    )
    names = _assert_unique(device)
    assert names == ["uart", "uart0", "uart1"]


def test_singleton_named_like_its_group_emits_one_name():
    # groupName equals the only instance's name: the family is that name and no
    # self-alias is emitted (a typedef redefinition is illegal before C11).
    device = _resolved(_p("WDT", 0x0, group="WDT", regs=("CR",)))
    assert _assert_unique(device) == ["wdt"]


def test_case_differences_still_count_as_a_collision():
    # The writer lowercases names into the type spelling, so GPIO and gpio are
    # one C identifier and must not both be emitted.
    device = _resolved(
        _p("gpio", 0x0, group="GRP", regs=("R",)),
        _p("GPIO", 0x100, group="GRP2", regs=("R", "S")),
    )
    _assert_unique(device)


def test_ungrouped_peripherals_named_after_another_family():
    # A standalone peripheral whose name matches a group's name: one of them
    # must give way rather than both emitting the same typedef.
    device = _resolved(
        _p("SPI0", 0x0, group="SPI", regs=("CR",)),
        _p("SPI1", 0x40, group="SPI", regs=("CR",)),
        _p("SPI", 0x100, regs=("DIFFERENT", "REGS")),
    )
    _assert_unique(device)
