"""The rules of one field of a register: where it sits, and how it compares with another field.

A field knows its own element and the levels below it, the bits and the enumerated sets. It
is given the register's width and access as plain values and the register's path, and knows
nothing of the register: which pairs of fields to compare is for the level above. Comparing
two fields reports the name they share and hands the bits they share to the bit class,
which judges them; the field's sets are judged by the set class, one by one and in pairs,
its write behaviour and read action by theirs, and its access beside its register's by the
access class.
"""

from __future__ import annotations

from collections.abc import Sequence

from regforge.finding import Finding, Severity
from regforge.ir import Access, Field
from regforge.resolution.base import Resolution
from regforge.resolution.collision import CollisionResolution
from regforge.resolution.device.access import AccessResolution
from regforge.resolution.device.peripheral.register.bit import BitResolution
from regforge.resolution.device.peripheral.register.field.enum_set.enum_set import EnumSetResolution
from regforge.resolution.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesResolution,
)
from regforge.resolution.device.peripheral.register.read_action import ReadActionResolution
from regforge.resolution.placeholder import is_placeholder_name


def _label(field: Field) -> str:
    """The field's name, with its count when it is an array: ``OD[4]``."""
    return f"{field.name}[{field.dim.length}]" if field.dim is not None else field.name


class FieldResolution(CollisionResolution):
    """One field of a register, as the rules see it.

    Six rules. A field that reaches past the register's width has no storage there
    (``ERROR``). Two different fields on one bit contradict each other, though the hardware
    could still be as the file says (``WARNING``): the bit map gives the bit to the first
    declared. Two fields with one name contradict each other too (``WARNING``), since the
    constants made from them would repeat; a placeholder name such as ``Reserved``, which
    vendors give to every unused run of bits, is not a clash. And the field's enumerated sets
    must be sound, each alone and as a pair, which is the business of
    :class:`~regforge.resolution.EnumSetResolution`; the sets are judged against the field's
    own width. Its write behaviour and read action must agree with its own access, which is
    the business of :class:`~regforge.resolution.ModifiedWriteValuesResolution` and
    :class:`~regforge.resolution.ReadActionResolution`, and that access must not go beyond
    its register's, which is the business of :class:`~regforge.resolution.AccessResolution`.
    Copies of one ``<dim>`` template overlapping each other are reported when the
    template is expanded, and a field array overlapping itself by
    ``check_address_math``, so neither is repeated here.

    Attributes:
        field: The field.
        width: The register's width in bits, as a number.
        where: The register's dotted path, ``P.CH.CTRL``, which starts every message.
        register_access: The register's access, as a plain value; ``None`` while it is
            unresolved.
    """

    unit = "bit"

    def __init__(
        self, field: Field, width: int, where: str, register_access: Access | None = None
    ) -> None:
        super().__init__(_label(field), where)
        self.field = field
        self.width = width
        self.register_access = register_access

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

    def sets(self) -> list[EnumSetResolution]:
        """The field's enumerated sets, each judged against the field's own width."""
        where = f"{self.where}.{self.owner}"
        return [
            EnumSetResolution(enum_set, self.field.bit_width, where, self.field.access)
            for enum_set in self.field.enum_sets
        ]

    def enum_findings(self) -> list[Finding]:
        """What is wrong with the field's enumerated sets: each one alone, then each pair."""
        sets = self.sets()
        findings = [finding for enum_set in sets for finding in enum_set.findings()]
        for index, first in enumerate(sets):
            for second in sets[index + 1 :]:
                findings += first.compare(second)
        return findings

    def effects(self) -> list[Resolution]:
        """The field's write behaviour and read action, each judged against its own access."""
        where = f"{self.where}.{self.owner}"
        found: list[Resolution] = []
        if self.field.modified_write_values is not None:
            found.append(
                ModifiedWriteValuesResolution(
                    self.field.modified_write_values, self.field.access, where
                )
            )
        if self.field.read_action is not None:
            found.append(ReadActionResolution(self.field.read_action, self.field.access, where))
        return found

    def effect_findings(self) -> list[Finding]:
        """What is wrong with the field's write behaviour and read action."""
        return [finding for effect in self.effects() for finding in effect.findings()]

    def access_findings(self) -> list[Finding]:
        """The field's access, where it goes beyond the access of its register."""
        where = f"{self.where}.{self.owner}"
        return AccessResolution(self.field.access, self.register_access, where).findings()

    def content_findings(self) -> list[Finding]:
        """What is wrong inside the field, whatever its width.

        Its access beside its register's, its enumerated sets, and what a write or a
        read does. :meth:`check_all` asks for this for every field, a copy of a
        template included.
        """
        return self.access_findings() + self.enum_findings() + self.effect_findings()

    def _past_width(self) -> list[Finding]:
        """Bits past the register's width, for a field that is not a copy of a template."""
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

    def findings(self) -> list[Finding]:
        """What is wrong with the field alone: its width, then its content.

        A copy of a ``<dim>`` template is left to :meth:`check_all` for the width, which
        reports the copies that run past together.
        """
        return self._past_width() + self.content_findings()

    @staticmethod
    def check_all(fields: Sequence[FieldResolution]) -> list[Finding]:
        """What is wrong with each of a register's fields.

        Copies of one ``<dim>`` template that run past the width are one finding, since the
        template is what needs fixing. Each copy's content (its access, its enumerated sets,
        its write behaviour and read action) is still judged, as the copies are separate
        fields.
        """
        findings: list[Finding] = []
        past: dict[str, list[FieldResolution]] = {}
        total: dict[str, int] = {}
        for resolution in fields:
            template = resolution.field.expanded_from
            if template is None:
                findings += resolution.findings()
                continue
            findings += resolution.content_findings()
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

    def is_placeholder(self) -> bool:
        """Whether the field's name only marks unused bits, as ``Reserved`` does."""
        return is_placeholder_name(self.field.name)

    def _extent(self) -> str:
        """Where the field sits, as a message says it: ``bit 5`` or ``bits 0..3``.

        An array is placed from its first bit to the last bit of its last copy.
        """
        first = self.field.bit_offset
        last = max((end for _, end in self.field.runs()), default=self.field.msb)
        return f"bit {first}" if first == last else f"bits {first}..{last}"

    def same_name(self, other: FieldResolution) -> list[Finding]:
        """The name this field shares with ``other``, which would make one constant twice.

        A placeholder name is not a clash, however often a register repeats it.
        """
        if self.field.name != other.field.name or self.is_placeholder():
            return []
        return [
            Finding(
                Severity.WARNING,
                f"{self.where}: the name {self.field.name} is used by two fields "
                f"({self._extent()} and {other._extent()})",
            )
        ]

    def _shared_bits(self, other: FieldResolution) -> list[Finding]:
        """The bits this field shares with ``other``, judged by the bit class."""
        if not any(a <= d and c <= b for a, b in self.ranges() for c, d in other.ranges()):
            return []
        return BitResolution.compare_all(self.bits(), other.bits())

    def compare(self, other: CollisionResolution) -> list[Finding]:
        """Cross-verify this field with another: the name they share, then the bits.

        Two copies of one template are not compared with each other, and a pair with no
        bit in common is not looked at further for bits.
        """
        if not isinstance(other, FieldResolution):
            raise TypeError("a field is compared with another field")
        template = self.field.expanded_from
        if template is not None and template == other.field.expanded_from:
            return []
        return self.same_name(other) + self._shared_bits(other)
