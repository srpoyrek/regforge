"""The rules of the bits of one register: what is wrong with who claims each bit.

This class knows nothing above a bit. It is given the register's width and, for each bit
position, the labels of whoever claims it, and reports what is wrong with those claims.
What a claimant is, a field or anything else, is for whoever builds the data to know;
see :func:`regforge.resolution.collect`.
"""

from __future__ import annotations

from dataclasses import dataclass

from regforge.finding import Finding, Severity
from regforge.resolution.base import Resolution


@dataclass
class _Run:
    """Consecutive bit positions claimed by the same claimants."""

    first: int
    last: int
    owners: list[str]


class BitResolution(Resolution):
    """What is wrong with the claims on the bits of one register.

    A bit claimed by more than one claimant is a contradiction in the file, though the
    hardware could still be as the file says (``WARNING``): the bit map gives the bit to
    the first declared. There is one finding per run of consecutive bits with the same
    claimants. A position at or beyond ``width`` is not a bit of the register and is
    ignored.

    Attributes:
        width: How many bits the register has.
        claims: For each bit position, the labels of whoever claims it, in the order
            they were declared.
        where: The register's dotted path, ``P.CH.CTRL``, which starts every message.
    """

    def __init__(self, width: int, claims: dict[int, list[str]], where: str) -> None:
        self.width = width
        self.claims = claims
        self.where = where

    def collisions(self) -> list[Finding]:
        """Runs of bits that more than one claimant claims, one finding per run."""
        runs: list[_Run] = []
        for position, owners in sorted(self.claims.items()):
            if position >= self.width or len(owners) < 2:
                continue
            if runs and runs[-1].last == position - 1 and runs[-1].owners == owners:
                runs[-1].last = position
            else:
                runs.append(_Run(position, position, owners))
        findings = []
        for run in runs:
            names = " and ".join(run.owners)
            if run.first == run.last:
                span = f"bit {run.first} is"
            else:
                span = f"bits {run.first}..{run.last} are"
            findings.append(Finding(Severity.WARNING, f"{self.where}: {span} claimed by {names}"))
        return findings

    def findings(self) -> list[Finding]:
        """Every problem the bit rules find: today, the collisions."""
        return self.collisions()
