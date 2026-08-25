"""Peripheral family grouping: one type per family, divergent members split."""

from regforge.families import group_families
from regforge.ir import AddressBlock, Device, Peripheral, Register
from regforge.layout import asserted_struct_size
from regforge.resolve import resolve_defaults, resolve_derived


def _resolved(*peripherals: Peripheral) -> Device:
    device = Device(name="Chip", peripherals=list(peripherals))
    resolve_defaults(device)
    resolve_derived(device)
    return device


def test_clean_derive_is_one_family_two_instances():
    device = _resolved(
        Peripheral(name="UART0", base_address=0x4000, registers=[Register("DR", 0x0, size=32)]),
        Peripheral(name="UART1", base_address=0x5000, derived_from="UART0"),
    )
    families = group_families(device)
    assert len(families) == 1
    assert families[0].type_source.name == "UART0"  # type named after the root
    assert [p.name for p in families[0].instances] == ["UART0", "UART1"]


def test_derived_chain_is_one_family():
    device = _resolved(
        Peripheral(name="U0", base_address=0x0, registers=[Register("DR", 0x0, size=32)]),
        Peripheral(name="U1", base_address=0x1000, derived_from="U0"),
        Peripheral(name="U2", base_address=0x2000, derived_from="U1"),
    )
    families = group_families(device)
    assert len(families) == 1
    assert [p.name for p in families[0].instances] == ["U0", "U1", "U2"]


def test_divergent_derive_splits_into_two_families():
    # UART1 declares its own, larger register set -> layout diverges from UART0.
    device = _resolved(
        Peripheral(name="UART0", base_address=0x4000, registers=[Register("DR", 0x0, size=32)]),
        Peripheral(
            name="UART1",
            base_address=0x5000,
            derived_from="UART0",
            registers=[Register("DR", 0x0, size=32), Register("EXTRA", 0x4, size=32)],
        ),
    )
    families = group_families(device)
    assert len(families) == 2
    assert {f.type_source.name for f in families} == {"UART0", "UART1"}
    assert all(len(f.instances) == 1 for f in families)  # neither shares a type


def test_groupname_merges_peripherals_without_derivedfrom():
    # STM32 style: GPIOA/GPIOB share a groupName, no derivedFrom, identical layout.
    device = _resolved(
        Peripheral(
            name="GPIOA",
            base_address=0x0,
            group_name="GPIO",
            registers=[Register("MODER", 0x0, size=32)],
        ),
        Peripheral(
            name="GPIOB",
            base_address=0x400,
            group_name="GPIO",
            registers=[Register("MODER", 0x0, size=32)],
        ),
    )
    families = group_families(device)
    assert len(families) == 1
    assert families[0].name == "GPIO"  # type named after the group
    assert [p.name for p in families[0].instances] == ["GPIOA", "GPIOB"]


def test_groupname_names_a_derived_family():
    device = _resolved(
        Peripheral(
            name="UART0",
            base_address=0x4000,
            group_name="UART",
            registers=[Register("DR", 0x0, size=32)],
        ),
        Peripheral(name="UART1", base_address=0x5000, derived_from="UART0"),
    )
    families = group_families(device)
    assert len(families) == 1
    assert families[0].name == "UART"  # groupName names the type, not the root


def test_divergent_group_largest_subgroup_keeps_name():
    # STM32 timer trap: TIM2/TIM3 identical, TIM1 advanced (extra RCR), all "TIM".
    device = _resolved(
        Peripheral(
            name="TIM1",
            base_address=0x0,
            group_name="TIM",
            registers=[Register("CR1", 0x0, size=32), Register("RCR", 0x4, size=32)],
        ),
        Peripheral(
            name="TIM2",
            base_address=0x400,
            group_name="TIM",
            registers=[Register("CR1", 0x0, size=32)],
        ),
        Peripheral(
            name="TIM3",
            base_address=0x800,
            group_name="TIM",
            registers=[Register("CR1", 0x0, size=32)],
        ),
    )
    families = group_families(device)
    assert len(families) == 2
    main = next(f for f in families if f.name == "TIM")
    assert [p.name for p in main.instances] == ["TIM2", "TIM3"]  # largest keeps the name
    assert main.note and "split 2 ways" in main.note and "RCR" in main.note
    outlier = next(f for f in families if f.name == "TIM1")
    assert [p.name for p in outlier.instances] == ["TIM1"]


def test_unrelated_peripherals_are_separate_families():
    device = _resolved(
        Peripheral(name="GPIOA", base_address=0x0, registers=[Register("MODER", 0x0, size=32)]),
        Peripheral(name="TIM1", base_address=0x1000, registers=[Register("CR1", 0x0, size=32)]),
    )
    families = group_families(device)
    assert len(families) == 2
    assert {f.type_source.name for f in families} == {"GPIOA", "TIM1"}
    assert all(len(f.instances) == 1 for f in families)


def test_identical_footprints_still_share_one_type():
    # Same registers and the same blocks: nothing about the struct differs.
    device = _resolved(
        Peripheral(
            name="SPI0",
            base_address=0x8000,
            group_name="SPI",
            registers=[Register("CR", 0x0, size=32)],
            address_blocks=[AddressBlock(0x0, 0x400, "registers")],
        ),
        Peripheral(
            name="SPI1",
            base_address=0x8400,
            group_name="SPI",
            registers=[Register("CR", 0x0, size=32)],
            address_blocks=[AddressBlock(0x0, 0x400, "registers")],
        ),
    )
    families = group_families(device)
    assert len(families) == 1
    assert [p.name for p in families[0].instances] == ["SPI0", "SPI1"]


def test_differing_footprints_split_the_family():
    # Identical registers, different block sizes. Merging these would emit one
    # struct sized from SPI0 and point SPI1 at 0x400 bytes it does not own.
    device = _resolved(
        Peripheral(
            name="SPI0",
            base_address=0x8000,
            group_name="SPI",
            registers=[Register("CR", 0x0, size=32)],
            address_blocks=[AddressBlock(0x0, 0x400, "registers")],
        ),
        Peripheral(
            name="SPI1",
            base_address=0x8400,
            group_name="SPI",
            registers=[Register("CR", 0x0, size=32)],
            address_blocks=[AddressBlock(0x0, 0x100, "registers")],
        ),
    )
    families = group_families(device)
    assert len(families) == 2
    sizes = {
        family.type_source.name: asserted_struct_size(family.type_source, 8) for family in families
    }
    assert sizes == {"SPI0": 0x400, "SPI1": 0x100}  # each sized from its own block
    assert "first differs at addressBlock" in (families[0].note or "")


def test_buffer_window_alone_splits_the_family():
    # Same registers, same registers block; one instance adds a FIFO window, so
    # its struct carries a BUFFER member the other must not inherit.
    device = _resolved(
        Peripheral(
            name="UART0",
            base_address=0x4000,
            group_name="UART",
            registers=[Register("DR", 0x0, size=32)],
            address_blocks=[
                AddressBlock(0x0, 0x4, "registers"),
                AddressBlock(0x4, 0x20, "buffer"),
            ],
        ),
        Peripheral(
            name="UART1",
            base_address=0x4400,
            group_name="UART",
            registers=[Register("DR", 0x0, size=32)],
            address_blocks=[AddressBlock(0x0, 0x4, "registers")],
        ),
    )
    assert len(group_families(device)) == 2
