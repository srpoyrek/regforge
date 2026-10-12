"""The rules of an access: what a field can do against what its register allows."""

from __future__ import annotations

from regforge.finding import Finding, Severity
from regforge.ir import Access
from regforge.resolution.base import Resolution


class AccessResolution(Resolution):
    """The access of a field, as the rules see it, beside the access of its register.

    A field can only be as accessible as the register that holds it. A field that can be
    written in a read-only register, or read in a write-only one, contradicts it
    (``WARNING``): the file disagrees with itself, though the hardware could still be as it
    says. An access that is still unresolved says nothing and contradicts nothing. The class
    knows only the two accesses, not what carries them.

    Attributes:
        access: The access of the field; ``None`` while unresolved.
        within: The access of the register that holds it; ``None`` while unresolved.
        where: The dotted path of the field, which starts every message.
    """

    def __init__(self, access: Access | None, within: Access | None, where: str) -> None:
        self.access = access
        self.within = within
        self.where = where

    def findings(self) -> list[Finding]:
        """An access that goes beyond the one it sits within."""
        access, within = self.access, self.within
        if access is None or within is None:
            return []
        if (access.can_write and not within.can_write) or (access.can_read and not within.can_read):
            return [
                Finding(
                    Severity.WARNING,
                    f"{self.where}: access is {access.value}, but its register is {within.value}",
                )
            ]
        return []
