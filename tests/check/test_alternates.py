"""check_alternate_registers: views of one word must agree where a register has one truth."""

from regforge.check import Severity, check_alternate_registers
from regforge.ir import Device, Peripheral, Register
from regforge.resolve import resolve_alternates


def _findings(*registers: Register):
    device = Device(name="Chip", peripherals=[Peripheral("P", 0x0, registers=list(registers))])
    resolve_alternates(device)
    return check_alternate_registers(device)


def test_views_that_reset_differently_are_a_warning():
    findings = _findings(
        Register("A_Out", 0x0, size=32, reset_value=0x0),
        Register("A_In", 0x0, size=32, reset_value=0xFF, alternate_register="A_Out"),
    )
    assert [(f.severity, f.message) for f in findings] == [
        (
            Severity.WARNING,
            "P.A_Out: alternate views disagree on resetValue (A_Out=0x0, A_In=0xFF) -- one "
            "register has one reset",
        )
    ]


def test_views_with_one_reset_or_none_are_silent():
    assert (
        _findings(
            Register("A_Out", 0x0, size=32, reset_value=0x5),
            Register("A_In", 0x0, size=32, reset_value=0x5, alternate_register="A_Out"),
            Register("A_Raw", 0x0, size=32, alternate_register="A_Out"),
        )
        == []
    )


def test_prefix_collision_with_a_sibling_is_reported():
    findings = _findings(
        Register("CCR", 0x14, size=32),
        Register("CCR_X", 0x18, size=32),
        Register("CCR_Y", 0x18, size=32, alternate_register="CCR_X"),
    )
    assert [f.message for f in findings] == [
        "P.CCR_X: the common prefix 'CCR' is already a member of the block -- the union is "
        "named CCR_X and its views keep their full names"
    ]


def test_plain_fallback_naming_is_not_a_finding():
    assert (
        _findings(
            Register("DR", 0x4, size=32),
            Register("RXD", 0x4, size=32, alternate_register="DR"),
        )
        == []
    )
