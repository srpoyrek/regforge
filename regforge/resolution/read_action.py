"""The rules of a read action: what a read does, and the access it is written beside."""

from __future__ import annotations

from regforge.finding import Finding, Severity
from regforge.ir import Access, ReadAction
from regforge.resolution.base import Resolution


class ReadActionResolution(Resolution):
    """What a read does to a register or field besides returning its value, as the rules see it.

    A read action says what a read does, so it contradicts an access that cannot be read
    (``WARNING``): ``write-only``, or ``writeOnce``, which cannot be read back. The file
    disagrees with itself, though the hardware could still be as it says. Every action
    counts, since a read action is never the schema's default. The class knows only the
    action and the access written beside it, not what carries them.

    Attributes:
        value: The read action.
        access: The access of whatever carries it; ``None`` while unresolved, which counts
            as read-write.
        where: The dotted path of whatever carries it, which starts every message.
    """

    def __init__(self, value: ReadAction, access: Access | None, where: str) -> None:
        self.value = value
        self.access = access
        self.where = where

    def findings(self) -> list[Finding]:
        """A read action beside an access that cannot read."""
        access = self.access or Access.READ_WRITE
        if access.can_read:
            return []
        return [
            Finding(
                Severity.WARNING,
                f"{self.where}: readAction {self.value.value} describes a read, "
                f"but access is {access.value}",
            )
        ]
