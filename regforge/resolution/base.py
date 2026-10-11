"""What every element's resolution class has in common."""

from __future__ import annotations

from abc import ABC, abstractmethod

from regforge.finding import Finding


class Resolution(ABC):
    """The rules of one element of the register map, and what is wrong with it.

    One subclass per element, one file each. A subclass is built from the element (and the
    dotted path that names it in messages) and answers :meth:`findings`. ``str()`` of it is
    the report, one finding per line, empty when nothing is wrong.
    """

    @abstractmethod
    def findings(self) -> list[Finding]:
        """Every problem the element's rules find, errors and warnings."""

    def __str__(self) -> str:
        return "\n".join(str(finding) for finding in self.findings())
