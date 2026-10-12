"""Access policy of a register or field."""

from __future__ import annotations

from enum import Enum


class Access(Enum):
    """Register/field access policy, spelled as in SVD."""

    READ_ONLY = "read-only"
    WRITE_ONLY = "write-only"
    READ_WRITE = "read-write"
    WRITE_ONCE = "writeOnce"
    READ_WRITE_ONCE = "read-writeOnce"

    @property
    def can_read(self) -> bool:
        """Whether software may read it. A write-once element cannot be read back."""
        return self not in (Access.WRITE_ONLY, Access.WRITE_ONCE)

    @property
    def can_write(self) -> bool:
        """Whether software may write it."""
        return self is not Access.READ_ONLY

    @property
    def can_read_and_write(self) -> bool:
        """Whether it may be both read and written."""
        return self.can_read and self.can_write

    @property
    def is_write_once(self) -> bool:
        """Whether it may be written only once after reset.

        True for ``writeOnce`` (write-only, one write) and ``read-writeOnce`` (read any
        time, one write). The SVD has no read-once access.
        """
        return self in (Access.WRITE_ONCE, Access.READ_WRITE_ONCE)

    @property
    def write_limit(self) -> int | None:
        """How many writes are allowed after reset.

        0 for read-only, 1 for the write-once kinds, ``None`` when there is no limit.
        """
        if self is Access.READ_ONLY:
            return 0
        if self.is_write_once:
            return 1
        return None
