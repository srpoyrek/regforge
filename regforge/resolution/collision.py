"""What every collision rule has in common: two claimants on the same part of a space.

A bit is claimed by a field, an address by a register, a number by an enumerated value, a
vector by an interrupt. The space and the claimants differ but the rule is one: two
different claimants on one position contradict each other. A resolution class whose
elements can collide with their own kind derives from :class:`CollisionResolution`, says
which positions it occupies and what the space is called, and gets the comparison, the
joining of a run of positions into one finding and the message from here.

Nothing in this module knows an element: positions are integers, claimants are labels.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from regforge.finding import Finding, Severity
from regforge.resolution.base import Resolution


@dataclass
class Collision:
    """A run of positions that two claimants both occupy; ``first`` and ``last`` are included."""

    first: int
    last: int
    owners: tuple[str, str]


def merge(collisions: list[Collision]) -> list[Collision]:
    """Join the collisions of the same two claimants that touch or overlap into one run."""
    runs: list[Collision] = []
    for collision in sorted(collisions, key=lambda item: item.first):
        previous = runs[-1] if runs else None
        if (
            previous is not None
            and previous.owners == collision.owners
            and collision.first <= previous.last + 1
        ):
            previous.last = max(previous.last, collision.last)
        else:
            runs.append(Collision(collision.first, collision.last, collision.owners))
    return runs


class CollisionResolution(Resolution):
    """A resolution class whose elements can collide with another of their own kind.

    A subclass says which positions the element occupies (:meth:`ranges`), what the space
    is called (``unit``), how serious a collision there is (``severity``) and how a
    position is written (:meth:`write`). :meth:`compare` then reports where this element
    and another occupy the same positions, one finding per run. Whoever compares two
    elements is responsible for them being different claimants: two that share a label
    are still two.

    Attributes:
        owner: The label of the claimant, or ``None`` for an element nobody claims, which
            collides with nothing.
        where: The dotted path of what holds the element, which starts every message.
    """

    #: The word for one position in the space: ``bit``, ``offset``, ``value``, ``vector``.
    unit: ClassVar[str] = "position"
    #: How serious two claimants on one position are in this space.
    severity: ClassVar[Severity] = Severity.WARNING

    def __init__(self, owner: str | None, where: str) -> None:
        self.owner = owner
        self.where = where

    @abstractmethod
    def ranges(self) -> list[tuple[int, int]]:
        """The runs of positions the element occupies, each as ``(first, last)``, both included."""

    @staticmethod
    def write(position: int) -> str:
        """How a position is written in a message; decimal unless the space says otherwise."""
        return str(position)

    def collisions(self, other: CollisionResolution) -> list[Collision]:
        """Where this element and ``other`` occupy the same positions, joined into runs."""
        if self.owner is None or other.owner is None:
            return []
        found = []
        for first, last in self.ranges():
            for other_first, other_last in other.ranges():
                low, high = max(first, other_first), min(last, other_last)
                if low <= high:
                    found.append(Collision(low, high, (self.owner, other.owner)))
        return merge(found)

    def compare(self, other: CollisionResolution) -> list[Finding]:
        """Cross-verify this element with another: the same positions claimed by both."""
        return self.report(self.collisions(other))

    def report(self, collisions: list[Collision]) -> list[Finding]:
        """One finding for each collision, in the words of this space."""
        findings = []
        for collision in collisions:
            first, last = self.write(collision.first), self.write(collision.last)
            span = (
                f"{self.unit} {first} is"
                if collision.first == collision.last
                else f"{self.unit}s {first}..{last} are"
            )
            a, b = collision.owners
            findings.append(Finding(self.severity, f"{self.where}: {span} claimed by {a} and {b}"))
        return findings
