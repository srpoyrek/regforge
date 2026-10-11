"""The rules of an enumerated set's usage: which direction it describes, and how it compares."""

from __future__ import annotations

from regforge.finding import Finding
from regforge.ir import EnumUsage
from regforge.resolution.collision import Collision, CollisionResolution


class EnumUsageResolution(CollisionResolution):
    """The direction an enumerated set describes, as the rules see it: reads, writes or both.

    A field returns one thing when read and accepts one thing when written, so two sets
    that describe the same direction contradict each other (``WARNING``). Position 0 is
    a read and position 1 a write; a read-write set occupies both.

    Attributes:
        usage: The direction the set describes.
        owner: The label of the set: its name, or ``the read set``.
        where: The field's dotted path, ``P.R.F``, which starts every message.
    """

    unit = "usage"

    def __init__(self, usage: EnumUsage, owner: str, where: str) -> None:
        super().__init__(owner, where)
        self.usage = usage

    def ranges(self) -> list[tuple[int, int]]:
        """The directions the set describes: 0 for reads, 1 for writes."""
        first = 0 if self.usage.covers_read else 1
        last = 1 if self.usage.covers_write else 0
        return [(first, last)]

    def findings(self) -> list[Finding]:
        """What is wrong with a usage alone: nothing; its rule compares it with another."""
        return []

    def report(self, collisions: list[Collision]) -> list[Finding]:
        """One finding per collision, naming the direction both sets describe."""
        findings = []
        for collision in collisions:
            if collision.first != collision.last:
                what = "reads and writes"
            else:
                what = "reads" if collision.first == 0 else "writes"
            a, b = collision.owners
            findings.append(
                Finding(self.severity, f"{self.where}: {a} and {b} both describe {what}")
            )
        return findings
