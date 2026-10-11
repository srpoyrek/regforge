"""check_alternate_registers: views of one word must agree where a register has one truth."""

from regforge.check import Severity, check_alternate_registers
from regforge.ir import AlternateSet, Device, Peripheral, Register
from regforge.resolve import resolve_alternates


def _alt(register: Register, of: str | None = None) -> AlternateSet:
    """The set the reader makes for ``register``, which declared itself an alternate of ``of``."""
    return AlternateSet((register,), joins=of)


def _findings(*sets: AlternateSet):
    device = Device(name="Chip", peripherals=[Peripheral("P", 0x0, alternate_sets=list(sets))])
    resolve_alternates(device)
    return check_alternate_registers(device)


def test_views_that_reset_differently_are_a_warning():
    findings = _findings(
        _alt(Register("A_Out", 0x0, size=32, reset_value=0x0)),
        _alt(Register("A_In", 0x0, size=32, reset_value=0xFF), of="A_Out"),
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
            _alt(Register("A_Out", 0x0, size=32, reset_value=0x5)),
            _alt(Register("A_In", 0x0, size=32, reset_value=0x5), of="A_Out"),
            _alt(Register("A_Raw", 0x0, size=32), of="A_Out"),
        )
        == []
    )


def test_prefix_collision_with_a_sibling_is_reported():
    findings = _findings(
        _alt(Register("CCR", 0x14, size=32)),
        _alt(Register("CCR_X", 0x18, size=32)),
        _alt(Register("CCR_Y", 0x18, size=32), of="CCR_X"),
    )
    assert [f.message for f in findings] == [
        "P.CCR_X: the common prefix 'CCR' is already a member of the block -- the union is "
        "named CCR_X and its views keep their full names"
    ]


def test_plain_fallback_naming_is_not_a_finding():
    assert (
        _findings(
            _alt(Register("DR", 0x4, size=32)),
            _alt(Register("RXD", 0x4, size=32), of="DR"),
        )
        == []
    )
