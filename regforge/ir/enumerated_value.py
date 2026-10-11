"""An enumerated value: a name for one number a field's bits can hold.

A :class:`~regforge.ir.Field` is a group of bits; an enumerated value says what one
of the numbers those bits can hold means. It names the field's value as a whole,
never a single bit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnumeratedValue:
    """A named constant that a :class:`Field` may hold.

    Attributes:
        name: Identifier of the value, e.g. ``"OUTPUT"``.
        value: The numeric value written to the field.
        description: Optional human-readable description.
    """

    name: str
    value: int
    description: str | None = None
