"""The flat list of registers that a peripheral or cluster presents over its alternate sets."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, overload

from regforge.ir.device.peripheral.alternate_set import AlternateSet

if TYPE_CHECKING:
    from regforge.ir import Register

#: What the descriptor reads as on the class, so a dataclass can use it as a default.
_ON_CLASS: Final[tuple[()]] = ()


class RegistersOf:
    """The ``registers`` of a container whose registers are stored in alternate sets.

    A :class:`~regforge.ir.Peripheral` or :class:`~regforge.ir.Cluster` keeps its
    registers in ``alternate_sets``, each set holding the one view of a plain register or
    the several views of one word. ``registers`` is that storage read flat, the views of
    every set in order, so code that walks registers does not care how they are grouped.

    Reading gives a fresh list. Assigning to ``registers``, or passing ``registers=`` to
    the constructor, replaces the sets with one set of one view per register. To change
    the grouping, assign ``alternate_sets``.
    """

    @overload
    def __get__(self, obj: None, owner: type) -> tuple[()]: ...
    @overload
    def __get__(self, obj: object, owner: type) -> list[Register]: ...
    def __get__(self, obj: object | None, owner: type) -> list[Register] | tuple[()]:
        if obj is None:
            return _ON_CLASS
        sets: list[AlternateSet] = obj.__dict__["alternate_sets"]
        return [view for alternate_set in sets for view in alternate_set.views]

    def __set__(self, obj: object, value: Sequence[Register]) -> None:
        if isinstance(value, RegistersOf) or value is _ON_CLASS:
            return  # the constructor's default: no registers were passed
        obj.__dict__["alternate_sets"] = [AlternateSet((register,)) for register in value]
