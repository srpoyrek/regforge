"""Where an unrolled copy came from: its template, the array's recipe and its place in it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import Dim


@dataclass(frozen=True)
class DimOrigin:
    """The array declaration an unrolled copy was made from.

    Expanding a ``DATA%s`` template whose ``<dim>`` is 4 leaves four ordinary elements,
    ``DATA0`` to ``DATA3``, with no ``Dim`` on them. Each one keeps a ``DimOrigin``, so
    the count, step and labels of the original declaration are not lost and the compact
    reading can be rebuilt (see :func:`~regforge.ir.device.peripheral.array_group.compact`).

    Attributes:
        template: The template's name as written, ``"DATA%s"``.
        dim: The array's recipe: how many copies, how far apart, which labels. Every
            copy of one template shares it.
        index: This copy's number, from 0.
        label: The label this copy took in its name.
    """

    template: str
    dim: Dim
    index: int
    label: str

    @property
    def count(self) -> int:
        """How many copies the declaration made."""
        return self.dim.length

    @property
    def offset(self) -> int:
        """This copy's distance from the first, in the template's units."""
        return self.index * self.dim.stride

    @property
    def is_first(self) -> bool:
        """Whether this is the first copy."""
        return self.index == 0

    @property
    def is_last(self) -> bool:
        """Whether this is the last copy."""
        return self.index == self.count - 1
