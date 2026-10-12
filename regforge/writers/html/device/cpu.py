"""The HTML block of the processor core."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Cpu
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.device.facts import FactsHtml
from regforge.writers.html.wording import yes_no


class CpuHtml(ElementHtml):
    """Renders the :class:`~regforge.ir.Cpu` facts that the file states."""

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._facts = FactsHtml(context)

    def render(self, cpu: Cpu) -> Markup:
        """The core's facts; one the file leaves out is left out here too."""
        pairs: list[tuple[str, str | None]] = [
            ("Core", cpu.name),
            ("Revision", cpu.revision),
            ("Endianness", cpu.endian),
            ("MPU", None if cpu.mpu_present is None else yes_no(cpu.mpu_present)),
            ("FPU", None if cpu.fpu_present is None else yes_no(cpu.fpu_present)),
            ("VTOR", None if cpu.vtor_present is None else yes_no(cpu.vtor_present)),
            ("NVIC priority bits", None if cpu.nvic_prio_bits is None else str(cpu.nvic_prio_bits)),
            ("Interrupts", None if cpu.num_interrupts is None else str(cpu.num_interrupts)),
        ]
        stated = [(label, value) for label, value in pairs if value is not None]
        return self._facts.render("Processor", stated)
