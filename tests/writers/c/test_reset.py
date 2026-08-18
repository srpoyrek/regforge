"""C writer: reset value is always emitted; reset mask only when partial.

A full-width reset mask (all bits defined) carries no information, so emitting
it for every register would be pure noise. A partial mask is the only correct
reset check for that register -- ``(reg & MASK) == (RESET & MASK)``.
"""

from regforge.ir import Device, Peripheral, Register
from regforge.writers.c import CWriter


def _render(**register_kwargs):
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="P",
                base_address=0,
                registers=[Register(name="R", address_offset=0, size=32, **register_kwargs)],
            )
        ],
    )
    return CWriter().render(device)


def test_reset_value_emitted():
    assert "#define P_R_RESET_VALUE (0x0000ABCDUL)" in _render(reset_value=0xABCD)


def test_reset_value_absent_not_emitted():
    assert "RESET_VALUE" not in _render(reset_value=None)


def test_partial_reset_mask_emitted():
    output = _render(reset_value=0, reset_mask=0x0000FFFF)
    assert "#define P_R_RESET_MASK (0x0000FFFFUL)" in output


def test_full_reset_mask_suppressed():
    # A full 32-bit mask says "all bits defined" -- no information, so no macro.
    assert "RESET_MASK" not in _render(reset_value=0, reset_mask=0xFFFFFFFF)


def test_absent_reset_mask_not_emitted():
    assert "RESET_MASK" not in _render(reset_value=0, reset_mask=None)
