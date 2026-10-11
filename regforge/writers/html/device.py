"""The HTML block of the whole device: the document."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Device
from regforge.provenance import Provenance
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.cpu import CpuHtml
from regforge.writers.html.device_facts import DeviceFacts
from regforge.writers.html.facts import FactsHtml
from regforge.writers.html.license_notice import LicenseHtml
from regforge.writers.html.peripheral import PeripheralHtml
from regforge.writers.html.provenance import ProvenanceHtml


class DeviceHtml(ElementHtml):
    """Renders a :class:`~regforge.ir.Device` as a complete HTML page.

    The device asks its peripherals for their sections, each peripheral asks its
    registers, each register its fields, and so on down, so the page is the sum of
    the blocks the elements render for themselves.
    """

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._cpu = CpuHtml(context)
        self._facts = FactsHtml(context)
        self._license = LicenseHtml(context)
        self._peripheral = PeripheralHtml(context)
        self._provenance = ProvenanceHtml(context)

    def render(self, device: Device, provenance: Provenance | None = None) -> Markup:
        """The whole document."""
        device_facts = DeviceFacts.of(device)
        pairs = [
            ("Vendor", device.vendor),
            ("Series", device.series),
            ("Version", device.version),
            ("Address unit", f"{device.address_unit_bits} bits"),
            ("Bus width", f"{device.bus_width} bits"),
        ]
        return self._fill(
            "document.html.j2",
            name=device.name,
            description=device.description,
            facts=self._facts.render("Device", [(k, v) for k, v in pairs if v]),
            cpu=self._cpu.render(device.cpu) if device.cpu is not None else Markup(""),
            license=self._license.render(device.license_text),
            rows=[self._peripheral.row(p, device_facts) for p in device.peripherals],
            sections=[self._peripheral.render(p, device_facts) for p in device.peripherals],
            provenance=self._provenance.render(provenance),
        )
