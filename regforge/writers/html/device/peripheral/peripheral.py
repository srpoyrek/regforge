"""The HTML block of one peripheral."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Peripheral
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.device.device_facts import DeviceFacts
from regforge.writers.html.device.peripheral.address_block import AddressBlockHtml
from regforge.writers.html.device.peripheral.dim import DimHtml
from regforge.writers.html.device.peripheral.interrupt import InterruptHtml
from regforge.writers.html.device.peripheral.placement import placed_registers
from regforge.writers.html.device.peripheral.register.register import RegisterHtml
from regforge.writers.html.wording import anchor, hex_, short


class PeripheralHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.Peripheral` and, by calls to its children, all it holds."""

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._block = AddressBlockHtml(context)
        self._dim = DimHtml()
        self._interrupt = InterruptHtml(context)
        self._register = RegisterHtml(context)

    def render(self, peripheral: Peripheral, facts: DeviceFacts) -> Markup:
        """The peripheral's section: facts, blocks, interrupts, register table and registers."""
        placed = placed_registers(peripheral)
        return self._fill(
            "peripheral.html.j2",
            anchor=anchor(peripheral.name),
            name=peripheral.name,
            base=hex_(peripheral.base_address, facts.address_digits),
            group=peripheral.group_name,
            derived_from=peripheral.derived_from,
            derived_anchor=anchor(peripheral.derived_from or ""),
            array_note=self._dim.note(peripheral, "units"),
            description=peripheral.description,
            blocks=[self._block.render(b, facts) for b in peripheral.address_blocks],
            interrupts=[self._interrupt.render(i) for i in peripheral.interrupts],
            summary=[self._register.row(peripheral, p, facts) for p in placed],
            registers=[self._register.render(peripheral, p, facts) for p in placed],
        )

    def row(self, peripheral: Peripheral, facts: DeviceFacts) -> Markup:
        """The peripheral's line in the device's table of contents."""
        return self._fill(
            "peripheral_row.html.j2",
            anchor=anchor(peripheral.name),
            name=peripheral.name,
            base=hex_(peripheral.base_address, facts.address_digits),
            interrupts=", ".join(i.name for i in peripheral.interrupts),
            summary=short(peripheral.description),
        )
