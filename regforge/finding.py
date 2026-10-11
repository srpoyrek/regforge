"""A finding: one thing a rule found wrong, and how seriously to take it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """How seriously to treat a :class:`Finding`."""

    WARNING = "warning"
    ERROR = "error"


@dataclass
class Finding:
    """A single consistency issue discovered in a device.

    ``str(finding)`` reads ``warning: P.R: ...``: the severity, then the message.
    """

    severity: Severity
    message: str

    def __str__(self) -> str:
        return f"{self.severity.value}: {self.message}"
