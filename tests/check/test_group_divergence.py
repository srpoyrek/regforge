"""Linter: flag a groupName covering peripherals with different layouts."""

from regforge.check import Severity, check_group_divergence
from regforge.ir import Device, Peripheral, Register


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
