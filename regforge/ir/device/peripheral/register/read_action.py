"""What reading a register or field does besides returning its value."""

from __future__ import annotations

from enum import Enum


class ReadAction(Enum):
    """The side effect of a read (SVD ``<readAction>``), spelled as in SVD.

    A register with a read action is not safe to read for inspection: reading a
    receive FIFO's data register pops the FIFO, so a debug loop that reads it eats
    the data. Without it a read has no effect.
    """

    CLEAR = "clear"
    SET = "set"
    MODIFY = "modify"
    MODIFY_EXTERNAL = "modifyExternal"

    @property
    def clears_value(self) -> bool:
        """Whether a read leaves the value cleared."""
        return self is ReadAction.CLEAR

    @property
    def sets_value(self) -> bool:
        """Whether a read leaves the value set to all ones."""
        return self is ReadAction.SET

    @property
    def is_external(self) -> bool:
        """Whether the change comes from outside, as a FIFO presenting its next element."""
        return self is ReadAction.MODIFY_EXTERNAL

    def value_after_read(self, width: int) -> int | None:
        """The value a ``width``-bit field holds after a read, or ``None`` if it is not fixed.

        A clear leaves 0 and a set leaves all ones; the modify kinds depend on the hardware.
        """
        if self is ReadAction.CLEAR:
            return 0
        if self is ReadAction.SET:
            return (1 << width) - 1
        return None
