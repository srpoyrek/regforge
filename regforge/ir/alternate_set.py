"""An alternate set: the container of one word, holding one view or several."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import Field, Register


@dataclass(frozen=True)
class AlternateSet:
    """One word of a peripheral or cluster, holding one view or several.

    A register that has no alternates is a set of one view. Registers that are different
    layouts over the same bits are a set of two or more. Like a C ``union``, the views
    overlay one word, and writing through one changes what the others read. Unlike a
    union, each view stays a full :class:`~regforge.ir.Register` with its own fields,
    access, reset value and side effects. The C writer emits a set of several views as a
    union; a test double keeps one integer per word and reads and writes it through the
    views, see :meth:`read` and :meth:`write`.

    The reader stores every register in a set of its own. ``resolve_alternates`` then
    merges the sets whose views the file declared to be alternates of one another.

    Attributes:
        views: The registers in the set, the primary view first.
        joins: What the file said about a set of one view that has not been merged yet:
            the name of the register it declared itself an alternate of (SVD
            ``<alternateRegister>``), as written. ``None`` when it declared none, and
            after ``resolve_alternates`` has acted on it.
    """

    views: tuple[Register, ...]
    joins: str | None = None

    def __post_init__(self) -> None:
        if not self.views:
            raise ValueError("an alternate set needs at least one view")

    @property
    def is_alternate(self) -> bool:
        """Whether the word has more than one view, so it is a union of layouts."""
        return len(self.views) > 1

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
