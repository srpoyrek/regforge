"""The HTML wording of what reading and writing a register or a field does."""

from __future__ import annotations

from regforge.ir import Field, Register
from regforge.writers.html.context import LeafHtml
from regforge.writers.html.device.peripheral.register.access import AccessHtml
from regforge.writers.html.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesHtml,
)
from regforge.writers.html.device.peripheral.register.read_action import ReadActionHtml
from regforge.writers.html.device.peripheral.register.write_constraint import WriteConstraintHtml


class SideEffectsHtml(LeafHtml):
    """Renders what reading and writing an element does, beyond storing and returning bits.

    A register and a field say it the same way, so both ask here; each setting is worded by
    the leaf of its own element, in the order a reader needs them.
    """

    def __init__(self) -> None:
        self._access = AccessHtml()
        self._constraint = WriteConstraintHtml()
        self._read = ReadActionHtml()
        self._write = ModifiedWriteValuesHtml()

    def notes(self, element: Register | Field) -> list[str]:
        """The write behaviour, the read action, a write-once access, then the constraint."""
        singles = (
            self._write.note(element.modified_write_values),
            self._read.note(element.read_action),
            self._access.note(element.access),
        )
        return [note for note in singles if note is not None] + self._constraint.notes(
            element.write_constraint
        )
