"""The rules of one declared alternate: which register a view may be another view of."""

from __future__ import annotations

from regforge.finding import Finding, Severity
from regforge.ir import Register
from regforge.resolution.base import Resolution

#: How SVD spells a copy template and an array template inside a name.
COPY = "%s"
ARRAY = "[%s]"


class AlternateSetResolution(Resolution):
    """One register's ``<alternateRegister>``, and whether the rules let it join that word."""

    def __init__(
        self, register: Register, wanted: str, candidates: list[Register], where: str
    ) -> None:
        self.register = register
        self.wanted = wanted
        self.candidates = candidates
        self.where = where
        self._judged: tuple[Register | None, list[Finding]] | None = None

    @staticmethod
    def same_shape(register: Register, other: Register) -> bool:
        """Whether both are single registers, or arrays of the same count and stride."""
        if register.dim is None or other.dim is None:
            return register.dim is None and other.dim is None
        return (register.dim.count, register.dim.increment) == (
            other.dim.count,
            other.dim.increment,
        )

    def target(self) -> Register | None:
        """The register the declaration names, or ``None`` when the rules refuse it."""
        return self._judge()[0]

    def findings(self) -> list[Finding]:
        """Everything the rules find wrong with the declaration."""
        return list(self._judge()[1])

    @property
    def label(self) -> str:
        """The dotted path that starts every message."""
        return f"{self.where}.{self.register.name}"

    def _judge(self) -> tuple[Register | None, list[Finding]]:
        if self._judged is None:
            self._judged = self._decide()
        return self._judged

    def _matched(self, findings: list[Finding]) -> tuple[Register | None, bool]:
        """The candidate the name points at, and whether the rules already refused it."""
        if ARRAY in self.wanted:
            wanted = self.wanted.replace(ARRAY, "")
            return next((c for c in self.candidates if c.name == wanted), None), False
        if COPY in self.wanted:
            return self._matched_copy(findings)
        return next((c for c in self.candidates if c.name == self.wanted), None), False

    def _matched_copy(self, findings: list[Finding]) -> tuple[Register | None, bool]:
        """The copy of the same index, when the name is a ``%s`` template."""
        copies = [c for c in self.candidates if c.expanded_from == self.wanted]
        if not copies:
            return None, False
        if self.register.expanded_from is None:
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{self.label}: alternateRegister names the template '{self.wanted}' -- "
                    f"resolved to its first copy, {copies[0].name}",
                )
            )
            return copies[0], False
        siblings = [c for c in self.candidates if c.expanded_from == self.register.expanded_from]
        if len(siblings) != len(copies):
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{self.label}: alternateRegister '{self.wanted}' expands to {len(copies)} "
                    f"copies, not {len(siblings)} -- left unrelated",
                )
            )
            return None, True
        return copies[siblings.index(self.register)], False

    def _decide(self) -> tuple[Register | None, list[Finding]]:
        """The target the rules allow, with everything they found wrong on the way."""
        findings: list[Finding] = []
        target, refused = self._matched(findings)
        if refused:
            return None, findings
        if target is None:
            findings.append(
                Finding(
                    Severity.ERROR,
                    f"{self.label}: alternateRegister '{self.wanted}' -- no register of that "
                    f"name in {self.where}; treated as an ordinary register",
                )
            )
            return None, findings
        if target is self.register:
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{self.label}: alternateRegister names itself -- ignored",
                )
            )
            return None, findings
        if not self.same_shape(self.register, target):
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{self.label}: alternateRegister '{target.name}' has a different <dim> "
                    "shape -- left unrelated",
                )
            )
            return None, findings
        if target.address_offset != self.register.address_offset:
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{self.label}: alternateRegister '{target.name}' is at offset "
                    f"0x{target.address_offset:X}, not 0x{self.register.address_offset:X} -- an "
                    "alternate view must share the offset; left unrelated",
                )
            )
            return None, findings
        return target, findings
