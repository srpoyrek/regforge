"""The values a register or field accepts when written."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WriteConstraint:
    """What may legally be written (SVD ``<writeConstraint>``).

    The SVD gives one of three constraints, so most attributes stay ``None``.

    Attributes:
        write_as_read: Only a value previously read may be written back.
        use_enumerated_values: Only values named in the field's enumerated set may
            be written.
        minimum: Smallest legal number, when the constraint is a range.
        maximum: Largest legal number, when the constraint is a range.
    """

    write_as_read: bool | None = None
    use_enumerated_values: bool | None = None
    minimum: int | None = None
    maximum: int | None = None

    @property
    def has_range(self) -> bool:
        """Whether the constraint is a numeric range."""
        return self.minimum is not None and self.maximum is not None

    def in_range(self, value: int) -> bool:
        """Whether ``value`` satisfies the range; ``True`` when there is no range to break."""
        if self.minimum is None or self.maximum is None:
            return True
        return self.minimum <= value <= self.maximum

    @property
    def is_unconstrained(self) -> bool:
        """Whether nothing is constrained: no flag set and no range."""
        return not self.write_as_read and not self.use_enumerated_values and not self.has_range
