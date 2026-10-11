"""What writing a register or field does to the bits written."""

from __future__ import annotations

from enum import Enum


class ModifiedWriteValues(Enum):
    """How a write changes the stored value (SVD ``<modifiedWriteValues>``).

    Spelled as in SVD. Without it a write simply stores the value written.
    """

    ONE_TO_CLEAR = "oneToClear"
    ONE_TO_SET = "oneToSet"
    ONE_TO_TOGGLE = "oneToToggle"
    ZERO_TO_CLEAR = "zeroToClear"
    ZERO_TO_SET = "zeroToSet"
    ZERO_TO_TOGGLE = "zeroToToggle"
    CLEAR = "clear"
    SET = "set"
    MODIFY = "modify"

    @property
    def acts_per_bit(self) -> bool:
        """Whether each written bit acts on its own bit (the ``oneTo`` and ``zeroTo`` kinds).

        Writing back a value just read then disturbs bits that were not meant to be
        touched: a ``oneToClear`` status register read as 0b11 and written back as
        0b11 clears both flags. Such a register needs a direct write, not a
        read-modify-write.
        """
        return self in (
            ModifiedWriteValues.ONE_TO_CLEAR,
            ModifiedWriteValues.ONE_TO_SET,
            ModifiedWriteValues.ONE_TO_TOGGLE,
            ModifiedWriteValues.ZERO_TO_CLEAR,
            ModifiedWriteValues.ZERO_TO_SET,
            ModifiedWriteValues.ZERO_TO_TOGGLE,
        )

    @property
    def acts_on_one(self) -> bool:
        """Whether writing a 1 is what acts (``oneToClear``, ``oneToSet``, ``oneToToggle``)."""
        return self in (
            ModifiedWriteValues.ONE_TO_CLEAR,
            ModifiedWriteValues.ONE_TO_SET,
            ModifiedWriteValues.ONE_TO_TOGGLE,
        )

    @property
    def acts_on_zero(self) -> bool:
        """Whether writing a 0 is what acts (``zeroToClear``, ``zeroToSet``, ``zeroToToggle``)."""
        return self in (
            ModifiedWriteValues.ZERO_TO_CLEAR,
            ModifiedWriteValues.ZERO_TO_SET,
            ModifiedWriteValues.ZERO_TO_TOGGLE,
        )

    def value_after_write(self, current: int, written: int, width: int) -> int | None:
        """The value a ``width``-bit field holds after ``written`` is written over ``current``.

        ``None`` for ``modify``, which the hardware decides. A test double uses this to
        mimic the field.
        """
        mask = (1 << width) - 1
        if self is ModifiedWriteValues.ONE_TO_CLEAR:
            return current & ~written & mask
        if self is ModifiedWriteValues.ONE_TO_SET:
            return (current | written) & mask
        if self is ModifiedWriteValues.ONE_TO_TOGGLE:
            return (current ^ written) & mask
        if self is ModifiedWriteValues.ZERO_TO_CLEAR:
            return current & written & mask
        if self is ModifiedWriteValues.ZERO_TO_SET:
            return (current | ~written) & mask
        if self is ModifiedWriteValues.ZERO_TO_TOGGLE:
            return (current ^ ~written) & mask
        if self is ModifiedWriteValues.CLEAR:
            return 0
        if self is ModifiedWriteValues.SET:
            return mask
        return None
