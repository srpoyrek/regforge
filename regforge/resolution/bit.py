"""The rules of one bit of a register: who claims it, and how it compares with another bit.

This class knows nothing above a bit. It is given the bit's position, a label for whoever
claims it and the register's path, and says what is wrong with it alone (:meth:`findings`)
and with it set beside another bit (:meth:`compare`, from the shared collision rule in
:mod:`regforge.resolution.collision`). Which bits to compare, and what a claimant is, are
for the level above: a field compares its bits with another field's, a register decides
which pairs of fields to compare, and so on up.
"""

from __future__ import annotations

from collections.abc import Sequence

from regforge.finding import Finding
from regforge.resolution.collision import Collision, CollisionResolution, merge


class BitResolution(CollisionResolution):
    """One bit of a register, as the rules see it.

    Two claimants on one bit contradict each other, though the hardware could still be as
    the file says (``WARNING``): the bit map gives the bit to the first declared. The rule
    needs two bits to compare, so :meth:`findings`, which looks at one alone, has nothing
    to say yet.

    Attributes:
        position: The bit's index in the register, 0 the least significant.
        owner: The label of whoever claims the bit, or ``None`` if nobody does.
        where: The register's dotted path, ``P.CH.CTRL``, which starts every message.
    """

    unit = "bit"

    def __init__(self, position: int, owner: str | None, where: str) -> None:
        super().__init__(owner, where)
        self.position = position

    def ranges(self) -> list[tuple[int, int]]:
        """The one position the bit occupies."""
        return [(self.position, self.position)]

    def findings(self) -> list[Finding]:
        """What is wrong with this bit alone: nothing yet; its rules compare it with another."""
        return []

    @staticmethod
    def compare_all(left: Sequence[BitResolution], right: Sequence[BitResolution]) -> list[Finding]:
        """Compare two lists of bits, pairing the ones at one position.

        A run of consecutive bits claimed by the same two claimants is one finding.
        """
        by_position = {bit.position: bit for bit in right}
        collisions: list[Collision] = []
        for bit in left:
            other = by_position.get(bit.position)
            if other is not None:
                collisions += bit.collisions(other)
        return left[0].report(merge(collisions)) if collisions else []
