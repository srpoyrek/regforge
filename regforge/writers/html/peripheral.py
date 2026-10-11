"""The HTML block of one peripheral."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Peripheral
from regforge.writers.html.address_block import AddressBlockHtml
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.interrupt import InterruptHtml
from regforge.writers.html.placement import placed_registers
from regforge.writers.html.register import RegisterHtml
from regforge.writers.html.wording import anchor, array_note, hex_, short


class PeripheralHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.Peripheral` and, by calls to its children, all it holds."""

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._block = AddressBlockHtml(context)
        self._interrupt = InterruptHtml(context)
        self._register = RegisterHtml(context)

    def render(self, peripheral: Peripheral) -> Markup:
        """The peripheral's section: facts, blocks, interrupts, register table and registers."""
        placed = placed_registers(peripheral)
        return self._fill(
            "peripheral.html.j2",
            anchor=anchor(peripheral.name),
            name=peripheral.name,
            base=hex_(peripheral.base_address, 8),
            group=peripheral.group_name,
            derived_from=peripheral.derived_from,
            derived_anchor=anchor(peripheral.derived_from or ""),
            array_note=array_note(peripheral, "units"),
            description=peripheral.description,
            blocks=[self._block.render(b) for b in peripheral.address_blocks],
            interrupts=[self._interrupt.render(i) for i in peripheral.interrupts],
            summary=[self._register.row(peripheral, p) for p in placed],
            registers=[self._register.render(peripheral, p) for p in placed],
        )

    def row(self, peripheral: Peripheral) -> Markup:
        """The peripheral's line in the device's table of contents."""
        return self._fill(
            "peripheral_row.html.j2",
            anchor=anchor(peripheral.name),
            name=peripheral.name,
            base=hex_(peripheral.base_address, 8),
            interrupts=", ".join(i.name for i in peripheral.interrupts),
            summary=short(peripheral.description),
        )
