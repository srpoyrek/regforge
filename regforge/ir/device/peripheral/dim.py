"""A dim: an array of copies of a peripheral, cluster, register or field.

Spelled in SVD by ``<dim>``, ``<dimIncrement>`` and ``<dimIndex>``: the element is a
template, ``count`` copies of it exist ``increment`` apart, and each copy's name takes
the next label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from regforge.ir import EnumeratedValue


@dataclass
class Dim:
    """An array of copies (SVD ``<dim>``, ``<dimIncrement>``, ``<dimIndex>``).

    A peripheral, cluster, register or field carrying a ``Dim`` is a template:
    ``count`` copies of it exist, ``increment`` apart, and each copy's name is
    the template's name with ``%s`` replaced by one of :attr:`labels`. The
    reader stores it as parsed; :func:`regforge.resolve.expand_dim` turns a
    ``%s`` template into its copies, and keeps a ``[%s]`` template as one
    element with ``dim`` still set so a writer can emit it as an array.

    Attributes:
        count: Number of copies (``<dim>``); ``None`` for a derived element that
            leaves it to its base template, filled in before expansion.
        increment: Distance between the starts of two neighbouring copies
            (``<dimIncrement>``): address units for a peripheral, cluster or
            register, like every other offset in the IR; bits for a field.
            ``None`` when the source omits it: expansion reports that and
            keeps one instance, so no ``Dim`` that survives expansion lacks it.
        index: The labels that replace ``%s``, in order (``<dimIndex>``);
            ``None`` when the source omits it and the copies are numbered from 0.
        array: Whether expansion kept this as one real array element
            (``NAME[%s]``) instead of unrolling it into separately named copies
            (``NAME%s``). ``False`` on a fresh ``Dim`` means not yet decided, not
            "not an array": every ``Dim`` describes an array. Set by expansion; a
            ``Dim`` that survives expansion always carries it.
        name: A name for the element type the copies share (``<dimName>``);
            ranks below ``headerStructName`` and above ``groupName`` when a
            type is named. ``None`` when absent.
        array_index: Names for the indices of an array (``<dimArrayIndex>``),
            each an :class:`EnumeratedValue`; empty when absent. A writer may
            emit them as index constants beside the array.
    """

    count: int | None
    increment: int | None
    index: list[str] | None = None
    array: bool = False
    name: str | None = None
    array_index: list[EnumeratedValue] = field(default_factory=list)

    @property
    def labels(self) -> list[str]:
        """One label per copy: ``index`` as given, else ``"0"``, ``"1"``, ..."""
        if self.index is not None:
            return list(self.index)
        return [str(i) for i in range(self.length)]

    @property
    def stride(self) -> int:
        """``increment`` once expansion has vouched for it.

        A template without a ``<dimIncrement>`` is never expanded, so every
        ``Dim`` the layout, the checks and the writers see has one.
        """
        assert self.increment is not None
        return self.increment

    @property
    def length(self) -> int:
        """``count`` once it is known.

        A partial ``Dim`` (count left to a ``derivedFrom`` base) is filled in
        before expansion, so nothing after that sees ``None``.
        """
        assert self.count is not None
        return self.count

    @property
    def offsets(self) -> list[int]:
        """Each copy's distance from the first, in the template's units."""
        return [copy * self.stride for copy in range(self.length)]

    def _check_copy(self, copy: int) -> None:
        if not 0 <= copy < self.length:
            raise IndexError(f"copy {copy} is outside an array of {self.length}")

    def offset_of(self, copy: int) -> int:
        """The distance of copy number ``copy`` (from 0) from the first."""
        self._check_copy(copy)
        return copy * self.stride

    def label_of(self, copy: int) -> str:
        """The label copy number ``copy`` (from 0) takes in its name."""
        self._check_copy(copy)
        return self.labels[copy]

    def copy_of(self, label: str) -> int | None:
        """The number of the copy that takes ``label``, or ``None`` if none does."""
        labels = self.labels
        return labels.index(label) if label in labels else None

    def extent(self, element_size: int) -> int:
        """The span from the start of the first copy to the end of the last."""
        return (self.length - 1) * self.stride + element_size

    def copies_overlap(self, element_size: int) -> bool:
        """Whether neighbouring copies overlap: the stride is smaller than one element.

        A single copy has no neighbour, so it cannot overlap.
        """
        return self.length > 1 and self.stride < element_size
