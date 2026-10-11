"""Which direction of access an enumerated set describes."""

from __future__ import annotations

from enum import Enum


class EnumUsage(Enum):
    """Whether an enumerated set names what a field reads, what it accepts, or both.

    Spelled as in SVD. Some hardware returns different meanings than it accepts, so
    one field can carry a read set and a write set.
    """

    READ = "read"
    WRITE = "write"
    READ_WRITE = "read-write"
