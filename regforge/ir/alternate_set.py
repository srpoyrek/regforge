"""An alternate set: registers that are different views of one word."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import Field, Register


@dataclass(frozen=True)
class AlternateSet:
    """Two or more registers at one offset: different layouts over the same bits.

    Like a C ``union``, the views overlay one word, and writing through one changes
    what the others read. Unlike a union, each view stays a full
    :class:`~regforge.ir.Register` with its own fields, access, reset value and side
    effects. The C writer emits the set as a union; a test double keeps one integer per
    word and reads and writes it through the views, see :meth:`read` and :meth:`write`.

    A derived view built by :func:`alternate_sets`; the IR never stores one.

    Attributes:
        views: The registers in the set, the primary view first.
    """

    views: tuple[Register, ...]

    def __post_init__(self) -> None:
        if not self.views:
            raise ValueError("an alternate set needs at least one view")

    @property
    def primary(self) -> Register:
        """The first view, the one the others are alternates of."""
        return self.views[0]

    @property
    def names(self) -> tuple[str, ...]:
        """The views' names, the primary first."""
        return tuple(view.name for view in self.views)

    @property
    def address_offset(self) -> int:
        """The offset every view shares."""
        return self.primary.address_offset

    @property
    def width(self) -> int:
        """The word's width in bits: the widest view's size."""
        sizes = [view.size for view in self.views]
        if any(size is None for size in sizes):
            raise ValueError(f"{self.primary.name}: a view's size is unresolved")
        return max(size for size in sizes if size is not None)

    def view_named(self, name: str) -> Register | None:
        """The view called ``name``, or ``None`` if the set has none."""
        return next((view for view in self.views if view.name == name), None)

    def owners(self, position: int) -> dict[str, Field | None]:
        """For each view, by name, the field that covers bit ``position`` of the word.

        ``None`` for a view that leaves the bit unclaimed or is too narrow to reach it.
        """
        return {
            view.name: view.field_at(position) if position < (view.size or 0) else None
            for view in self.views
        }

    def _field(self, view: str, field: str) -> Field:
        found = self.view_named(view)
        if found is None:
            raise KeyError(f"{self.primary.name}: no view called {view!r}")
        target = found.field_named(field)
        if target is None:
            raise KeyError(f"{view}: no field called {field!r}")
        return target

    def read(self, word: int, view: str, field: str) -> int:
        """The number the named field of the named view holds in ``word``."""
        return self._field(view, field).extract(word)

    def write(self, word: int, view: str, field: str, value: int) -> int:
        """``word`` after writing ``value`` into the named field of the named view.

        The other views see the change, because they share the word.
        """
        return self._field(view, field).insert(word, value)


def alternate_sets(registers: list[Register]) -> list[AlternateSet]:
    """The alternate sets among ``registers``, in the order their primaries appear.

    Run it after ``resolve_alternates``, which links the views: each linked register's
    ``alternates`` names the whole set, the primary first. A register that is the only
    view of its word belongs to no set.
    """
    by_name = {register.name: register for register in registers}
    sets = []
    for register in registers:
        if len(register.alternates) > 1 and register.alternates[0] == register.name:
            views = tuple(by_name[name] for name in register.alternates if name in by_name)
            sets.append(AlternateSet(views))
    return sets
