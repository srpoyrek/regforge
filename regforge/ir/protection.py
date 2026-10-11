"""Which bus accesses a register or block may be reached by."""

from __future__ import annotations

from enum import Enum


class Protection(Enum):
    """Permission an access needs (SVD ``<protection>``), spelled as in SVD.

    ``s``: secure permission is required. ``n``: non-secure permission is enough, and
    secure works too. ``p``: privileged permission is required.
    """

    SECURE = "s"
    NON_SECURE = "n"
    PRIVILEGED = "p"

    @property
    def requires_secure(self) -> bool:
        """Whether only a secure access may reach it."""
        return self is Protection.SECURE

    @property
    def allows_non_secure(self) -> bool:
        """Whether a non-secure access may reach it."""
        return self is Protection.NON_SECURE

    @property
    def requires_privilege(self) -> bool:
        """Whether only a privileged access may reach it."""
        return self is Protection.PRIVILEGED
