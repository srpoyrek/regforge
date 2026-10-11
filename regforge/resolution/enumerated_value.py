"""The rules of one enumerated value: the numbers it names, and how it compares with another."""

from __future__ import annotations

from regforge.finding import Finding, Severity
from regforge.ir import EnumeratedValue
from regforge.ir.enum_set import MAX_LISTED_BITS
from regforge.resolution.collision import CollisionResolution


def _runs(numbers: list[int]) -> list[tuple[int, int]]:
    """The numbers as runs of consecutive ones, ``(first, last)`` each, in order."""
    runs: list[tuple[int, int]] = []
    for number in sorted(numbers):
        if runs and number == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], number)
        else:
            runs.append((number, number))
    return runs


def _matching(value: int, dont_care: int) -> list[int]:
    """Every number a ``0b01xx`` pattern matches: ``value`` with each subset of the x bits set."""
    numbers = []
    subset = dont_care
    while True:
        numbers.append(value | subset)
        if subset == 0:
            return numbers
        subset = (subset - 1) & dont_care


class EnumeratedValueResolution(CollisionResolution):
    """One enumerated value of a field, as the rules see it.

    An entry names a number, or every number a ``0b01xx`` pattern matches; a catch-all
    entry names the rest and so collides with nothing. Two entries naming one number
    contradict each other, though the hardware could still be as the file says
    (``WARNING``). An entry whose number the field cannot hold is impossible
    (``ERROR``). A pattern with more x bits than ``MAX_LISTED_BITS`` is not expanded, as
    the set's gaps are not listed beyond that width.

    Attributes:
        entry: The enumerated value.
        width: The field's width in bits, as a number.
        where: The field's dotted path, ``P.R.F``, which starts every message.
    """

    unit = "value"

    def __init__(self, entry: EnumeratedValue, width: int, where: str) -> None:
        super().__init__(entry.name, where)
        self.entry = entry
        self.width = width

    @staticmethod
    def write(position: int) -> str:
        """Numbers are written in hex, as the entries are."""
        return f"{position:#x}"

    def ranges(self) -> list[tuple[int, int]]:
        """The numbers the entry names, as runs; none for a catch-all."""
        entry = self.entry
        if entry.value is None:
            return []
        if not entry.dont_care:
            return [(entry.value, entry.value)]
        if bin(entry.dont_care).count("1") > MAX_LISTED_BITS:
            return []
        return _runs(_matching(entry.value, entry.dont_care))

    def findings(self) -> list[Finding]:
        """What is wrong with the entry alone: a number the field cannot hold."""
        if self.entry.fits_in(self.width):
            return []
        return [
            Finding(
                Severity.ERROR,
                f"{self.where}: {self.entry.name} = {self.entry.label(self.width)} does not fit "
                f"the {self.width}-bit field",
            )
        ]
