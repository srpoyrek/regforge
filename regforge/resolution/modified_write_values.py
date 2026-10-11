"""The rules of a write behaviour: what a write does, and the access it is written beside."""

from __future__ import annotations

from regforge.finding import Finding, Severity
from regforge.ir import Access, ModifiedWriteValues
from regforge.resolution.base import Resolution


class ModifiedWriteValuesResolution(Resolution):
    """What a write does to a register or field, as the rules see it.

    A write behaviour says what a write does, so it contradicts an access that forbids
    writing (``WARNING``): the file disagrees with itself, though the hardware could still be
    as it says. Every behaviour counts, ``modify`` too, though it is the schema's default: a
    file that spells it out beside a read-only access has described a write to something that
    cannot be written. The class knows only the behaviour and the access written beside it,
    not what carries them.

    Attributes:
        value: The write behaviour.
        access: The access of whatever carries it; ``None`` while unresolved, which counts
            as read-write.
        where: The dotted path of whatever carries it, which starts every message.
    """

    def __init__(self, value: ModifiedWriteValues, access: Access | None, where: str) -> None:
        self.value = value
        self.access = access
        self.where = where

    def findings(self) -> list[Finding]:
        """A write behaviour beside an access that cannot write."""
        access = self.access or Access.READ_WRITE
        if access.can_write:
            return []
        return [
            Finding(
                Severity.WARNING,
                f"{self.where}: modifiedWriteValues {self.value.value} describes a write, "
                f"but access is {access.value}",
            )
        ]
