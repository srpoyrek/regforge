"""The rules of one field of a register: where it sits, and how it compares with another field.

A field knows its own element and the level below it, the bits. It is given the register's
width as a number and the register's path, and knows nothing of the register: which pairs of
fields to compare is for the level above. Comparing two fields hands the bits they share to
the bit class, which judges them.
"""

from __future__ import annotations

from collections.abc import Sequence

from regforge.finding import Finding, Severity
from regforge.ir import Field
from regforge.resolution.bit import BitResolution
from regforge.resolution.collision import CollisionResolution


def _label(field: Field) -> str:
    """The field's name, with its count when it is an array: ``OD[4]``."""
    return f"{field.name}[{field.dim.length}]" if field.dim is not None else field.name


class FieldResolution(CollisionResolution):
    """One field of a register, as the rules see it.

    Two rules. A field that reaches past the register's width has no storage there
    (``ERROR``). Two different fields on one bit contradict each other, though the hardware
    could still be as the file says (``WARNING``): the bit map gives the bit to the first
    declared. Copies of one ``<dim>`` template overlapping each other are reported when the
    template is expanded, and a field array overlapping itself by ``check_address_math``,
    so neither is repeated here.

    Attributes:
        field: The field.
        width: The register's width in bits, as a number.
        where: The register's dotted path, ``P.CH.CTRL``, which starts every message.
    """

    unit = "bit"

    def __init__(self, field: Field, width: int, where: str) -> None:
        super().__init__(_label(field), where)
        self.field = field
        self.width = width

    def ranges(self) -> list[tuple[int, int]]:
        """The bits the field occupies in the register, each run cut off at the width."""
        return [
            (first, min(last, self.width - 1))
            for first, last in self.field.runs()
            if first < self.width
        ]

    def bits(self) -> list[BitResolution]:
        """The field's bits, one per position, each with the field as its claimant."""
        positions = {p for first, last in self.ranges() for p in range(first, last + 1)}
        return [BitResolution(position, self.owner, self.where) for position in sorted(positions)]

    def findings(self) -> list[Finding]:
        """What is wrong with the field alone: bits past the register's width.

        A copy of a ``<dim>`` template is left to :meth:`check_all`, which reports the
        copies that run past together.
        """
        if self.field.expanded_from is not None or self.field.fits_in(self.width):
            return []
        last = self.field.runs()[-1][1]
        return [
            Finding(
                Severity.ERROR,
                f"{self.where}.{self.owner}: bits {self.field.bit_offset}..{last} run past the "
                f"{self.width}-bit register",
            )
        ]

    @staticmethod
    def check_all(fields: Sequence[FieldResolution]) -> list[Finding]:
        """What is wrong with each of a register's fields.

        Copies of one ``<dim>`` template that run past the width are one finding, since the
        template is what needs fixing.
        """
        findings: list[Finding] = []
        past: dict[str, list[FieldResolution]] = {}
        total: dict[str, int] = {}
        for resolution in fields:
            template = resolution.field.expanded_from
            if template is None:
                findings += resolution.findings()
                continue
            total[template] = total.get(template, 0) + 1
            if not resolution.field.fits_in(resolution.width):
                past.setdefault(template, []).append(resolution)
        for template, copies in past.items():
            names = f"{copies[0].field.name}..{copies[-1].field.name}"
            findings.append(
                Finding(
                    Severity.ERROR,
                    f"{copies[0].where}.{template}: {names} ({len(copies)} of its "
                    f"{total[template]} copies) run past the {copies[0].width}-bit register",
                )
            )
        return findings

    def compare(self, other: CollisionResolution) -> list[Finding]:
        """Cross-verify this field with another: the bits they share, judged by the bit class.

        Two copies of one template are not compared with each other, and a pair with no
        bit in common is not looked at further.
        """
        if not isinstance(other, FieldResolution):
            raise TypeError("a field is compared with another field")
        template = self.field.expanded_from
        if template is not None and template == other.field.expanded_from:
            return []
        if not any(a <= d and c <= b for a, b in self.ranges() for c, d in other.ranges()):
            return []
        return BitResolution.compare_all(self.bits(), other.bits())
