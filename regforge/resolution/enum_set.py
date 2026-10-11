"""The rules of one enumerated set: its entries together, and how it compares with another set.

A set knows its own element and the level below it, the entries and the usage. It is given
the field's width as a number and the field's path, and knows nothing of the field itself.
Whoever holds several sets of one field decides which pairs to compare.
"""

from __future__ import annotations

from regforge.finding import Finding, Severity
from regforge.ir import EnumeratedValue, EnumSet
from regforge.resolution.base import Resolution
from regforge.resolution.enum_usage import EnumUsageResolution
from regforge.resolution.enumerated_value import EnumeratedValueResolution


class EnumSetResolution(Resolution):
    """One enumerated set of a field, as the rules see it.

    Besides each entry's own rule (see :class:`EnumeratedValueResolution`), the entries
    are judged together. Two entries naming one number, or a ``0b01xx`` pattern covering
    another entry's number, contradict each other (``WARNING``, the shared collision rule).
    A name given to two entries is a ``WARNING`` too, since the constants made from them
    would repeat; a placeholder name such as ``Reserved``, which vendors give to every
    unused number, may repeat. A set can have only one catch-all entry, which names the
    rest (``WARNING``). Numbers are bucketed so a large set is not compared pair by pair;
    only patterns are compared with every entry.

    Attributes:
        enum_set: The set.
        width: The field's width in bits, as a number.
        where: The field's dotted path, ``P.R.F``, which starts every message.
        label: What the set is called in a message: its name, or ``the read set``.
    """

    def __init__(self, enum_set: EnumSet, width: int, where: str) -> None:
        self.enum_set = enum_set
        self.width = width
        self.where = where
        self.label = enum_set.name or f"the {enum_set.usage.value} set"

    def _value(self, entry: EnumeratedValue) -> EnumeratedValueResolution:
        return EnumeratedValueResolution(entry, self.width, self.where)

    def usage(self) -> EnumUsageResolution:
        """The direction the set describes, to compare with another set's."""
        return EnumUsageResolution(self.enum_set.usage, self.label, self.where)

    def catch_alls(self) -> list[Finding]:
        """More than one entry naming the rest."""
        names = [entry.name for entry in self.enum_set.values if entry.is_default]
        if len(names) < 2:
            return []
        return [
            Finding(
                Severity.WARNING,
                f"{self.where}: {len(names)} catch-all entries ({', '.join(names)}); "
                "only one can name the rest",
            )
        ]

    def names(self) -> list[Finding]:
        """A name used by more than one entry, one finding per name; placeholders may repeat."""
        by_name: dict[str, list[EnumeratedValue]] = {}
        for entry in self.enum_set.values:
            if not self._value(entry).is_placeholder():
                by_name.setdefault(entry.name, []).append(entry)
        findings = []
        for name, entries in by_name.items():
            if len(entries) > 1:
                shown = ", ".join(entry.label(self.width) for entry in entries)
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{self.where}: the name {name} is used by {len(entries)} entries "
                        f"({shown})",
                    )
                )
        return findings

    def collisions(self) -> list[Finding]:
        """Entries that name one number, found in declaration order."""
        entries = [entry for entry in self.enum_set.values if entry.value is not None]
        buckets: dict[int, list[int]] = {}
        for index, entry in enumerate(entries):
            if entry.value is not None and not entry.dont_care:
                buckets.setdefault(entry.value, []).append(index)
        pairs: set[tuple[int, int]] = set()
        for indexes in buckets.values():
            pairs.update((a, b) for i, a in enumerate(indexes) for b in indexes[i + 1 :])
        for index, entry in enumerate(entries):
            if entry.dont_care:
                pairs.update(
                    (min(index, other), max(index, other))
                    for other in range(len(entries))
                    if other != index
                )
        findings: list[Finding] = []
        for first, second in sorted(pairs):
            findings += self._value(entries[first]).compare(self._value(entries[second]))
        return findings

    def findings(self) -> list[Finding]:
        """What is wrong with the set: its entries one by one, then together."""
        findings: list[Finding] = []
        for entry in self.enum_set.values:
            findings += self._value(entry).findings()
        return findings + self.catch_alls() + self.names() + self.collisions()

    def compare(self, other: EnumSetResolution) -> list[Finding]:
        """Cross-verify this set with another of the same field: the directions both describe."""
        return self.usage().compare(other.usage())
