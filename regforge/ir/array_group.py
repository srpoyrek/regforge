"""An array group: the compact reading of one declared array whose copies were unrolled."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from regforge.ir import Dim
    from regforge.ir.dim_origin import DimOrigin


class _Copy(Protocol):
    """What a peripheral, cluster, register or field offers: a name and an origin."""

    name: str
    origin: DimOrigin | None


T = TypeVar("T", bound=_Copy)


@dataclass(frozen=True)
class ArrayGroup(Generic[T]):
    """The unrolled copies of one ``<dim>`` declaration, read as the single array it was.

    The elaborated tree holds ``DATA0`` to ``DATA3`` as four elements; this is the same
    thing as the vendor wrote it, ``DATA%s`` times four. A derived view built by
    :func:`array_groups` and :func:`compact`; the IR never stores one.

    Attributes:
        template: The template's name as written, ``"DATA%s"``.
        dim: The array's recipe: count, step and labels.
        copies: The copies, in the order they sit in the parent.
    """

    template: str
    dim: Dim
    copies: tuple[T, ...]

    @property
    def count(self) -> int:
        """How many copies were found."""
        return len(self.copies)

    @property
    def names(self) -> tuple[str, ...]:
        """The copies' names, in order."""
        return tuple(copy.name for copy in self.copies)


def array_groups(elements: Sequence[T]) -> list[ArrayGroup[T]]:
    """The arrays among ``elements`` that were unrolled, in the order they first appear.

    An element with no origin (a lone element, or an array kept whole) forms no group.
    """
    members: dict[str, list[T]] = {}
    recipes: dict[str, Dim] = {}
    for element in elements:
        origin = element.origin
        if origin is not None:
            members.setdefault(origin.template, []).append(element)
            recipes.setdefault(origin.template, origin.dim)
    return [
        ArrayGroup(template, recipes[template], tuple(copies))
        for template, copies in members.items()
    ]


def compact(elements: Sequence[T]) -> list[T | ArrayGroup[T]]:
    """``elements`` as the vendor wrote them: each unrolled array is one group.

    The group stands where its first copy was. Everything else is passed through.
    """
    groups = {group.template: group for group in array_groups(elements)}
    placed: set[str] = set()
    result: list[T | ArrayGroup[T]] = []
    for element in elements:
        origin = element.origin
        if origin is None:
            result.append(element)
        elif origin.template not in placed:
            placed.add(origin.template)
            result.append(groups[origin.template])
    return result
