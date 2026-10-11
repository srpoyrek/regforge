"""A single bit of a register: the smallest element of the hardware map.

A register is N bits at one address. A :class:`~regforge.ir.Field` is a named group
of adjacent bits inside it, recorded only as a position (``bit_offset``,
``bit_width``); the bits themselves are stored nowhere. :func:`bits` is the view
that makes them explicit, so a bit can be asked which field groups it and what it
holds after reset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import Field, Register


@dataclass(frozen=True)
class Bit:
    """One bit of a :class:`~regforge.ir.Register`.

    A derived view built by :func:`bits`; the IR never stores one. A bit has no
    attributes of its own: it is a position, plus the two things the register
    says about that position. It holds no link back to its register, as no other
    IR node points up at its parent; the register is the one you called
    :func:`bits` on. A claiming field's access is ``bit.field.access``.

    Attributes:
        position: Zero-based index within the register; 0 is the least-significant bit.
        field: The field that groups this bit, or ``None`` for a bit no field names.
        reset: The bit's value after reset, 0 or 1; ``None`` when the register
            declares no reset value or its reset mask leaves this bit undefined.
    """

    position: int
    field: Field | None = None
    reset: int | None = None

    @property
    def is_claimed(self) -> bool:
        """Whether a field names this bit."""
        return self.field is not None


def _reset_bit(register: Register, position: int) -> int | None:
    """The bit's value after reset, or ``None`` when the register does not define it."""
    if register.reset_value is None:
        return None
    if register.reset_mask is not None and not (register.reset_mask >> position) & 1:
        return None
    return (register.reset_value >> position) & 1


def claims(register: Register) -> dict[int, list[Field]]:
    """Every field that covers each bit position of ``register``, in declaration order.

    A position maps to the distinct fields that claim it; a field array claims the bits
    of every copy, but is listed once per position. Positions past the register's width
    are included, since it is the caller who knows the width. More than one field on a
    position is a collision, which :class:`~regforge.resolution.BitResolution` reports.
    """
    found: dict[int, list[Field]] = {}
    for field in register.fields:
        if field.dim is None:
            starts = [field.bit_offset]
        else:
            starts = [
                field.bit_offset + element * field.dim.stride for element in range(field.dim.length)
            ]
        for start in starts:
            for position in range(start, start + field.bit_width):
                owners = found.setdefault(position, [])
                if not any(owner is field for owner in owners):
                    owners.append(field)
    return found


def bits(register: Register) -> list[Bit]:
    """Every bit of ``register``, least-significant first.

    Needs the register's ``size``, so run it after defaults resolution; a
    register whose size is still unresolved raises ``ValueError``. Fields are
    expected to be expanded: one that still carries a ``dim`` is read as an
    array, a copy every ``dim.stride`` bits, and every copy claims its bits. A
    field bit past the register's width belongs to no bit of this register. When
    two fields cover one bit the first declared keeps it; reporting that overlap
    is :class:`~regforge.resolution.BitResolution`'s job, not this view's.

    Example: an 8-bit ``CTRL`` with ``EN`` at bit 0 and ``MODE`` at bits [2:1]
    yields eight bits whose fields are ``EN``, ``MODE``, ``MODE``, then five
    unclaimed.
    """
    if register.size is None:
        raise ValueError(f"{register.name}: size is unresolved, so its bits are unknown")
    claimed = claims(register)
    return [
        Bit(
            position,
            claimed[position][0] if position in claimed else None,
            _reset_bit(register, position),
        )
        for position in range(register.size)
    ]
