"""Linter: flag a groupName covering peripherals with different layouts."""

from regforge.check import Severity, check_group_divergence
from regforge.ir import AddressBlock, Device, Peripheral, Register


def test_identical_group_no_warning():
    device = Device(
        name="C",
        peripherals=[
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
        ],
    )
    assert check_group_divergence(device) == []


def test_divergent_group_warns_naming_register():
    device = Device(
        name="C",
        peripherals=[
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
        ],
    )
    findings = check_group_divergence(device)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "TIM" in findings[0].message
    assert "RCR" in findings[0].message


def test_divergent_footprint_warns_naming_the_address_block():
    # Identical registers, different declared footprints: the struct each needs
    # differs in size, so the group is not one type even though the registers match.
    device = Device(
        name="C",
        peripherals=[
            Peripheral(
                name="SPI0",
                base_address=0x0,
                group_name="SPI",
                registers=[Register("CR", 0x0, size=32)],
                address_blocks=[AddressBlock(0x0, 0x400, "registers")],
            ),
            Peripheral(
                name="SPI1",
                base_address=0x400,
                group_name="SPI",
                registers=[Register("CR", 0x0, size=32)],
                address_blocks=[AddressBlock(0x0, 0x100, "registers")],
            ),
        ],
    )
    findings = check_group_divergence(device)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert "first differs at addressBlock" in findings[0].message
