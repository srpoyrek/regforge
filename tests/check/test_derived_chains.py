"""Linter: flag derivedFrom chains deeper than one level (portability hazard)."""

from regforge.check import Severity, check_derived_chains
from regforge.ir import Device, Peripheral, Register


def test_depth_one_is_fine():
    device = Device(
        name="C",
        peripherals=[
            Peripheral(name="U0", base_address=0x0, registers=[Register("R", 0x0, size=32)]),
            Peripheral(name="U1", base_address=0x1000, derived_from="U0"),
        ],
    )
    assert check_derived_chains(device) == []


def test_depth_two_warns():
    device = Device(
        name="C",
        peripherals=[
            Peripheral(name="U0", base_address=0x0, registers=[Register("R", 0x0, size=32)]),
            Peripheral(name="U1", base_address=0x1000, derived_from="U0"),
            Peripheral(name="U2", base_address=0x2000, derived_from="U1"),
        ],
    )
    findings = check_derived_chains(device)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "2 levels deep" in findings[0].message
