"""The HTML writer: a register reference you can open in a browser and print to PDF."""

from __future__ import annotations

from regforge.ir import Device
from regforge.provenance import Provenance
from regforge.writers.base import Writer
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device import DeviceHtml


class HtmlWriter(Writer):
    """Renders a device as one self-contained HTML register reference.

    Every peripheral, register and field the reader extracted is laid out: names,
    descriptions, addresses, reset values, access, bit maps, enumerated values and
    the notes that say what reading or writing does. There is no script and no
    external file, and the page prints one peripheral to a page, so a browser's
    "save as PDF" makes the PDF. The same input gives the same bytes.
    """

    target_name = "html"
    file_extension = ".html"

    def __init__(self) -> None:
        self._device = DeviceHtml(RenderContext.default())

    def render(self, device: Device, provenance: Provenance | None = None) -> str:
        """Render ``device`` as an HTML document."""
        return str(self._device.render(device, provenance))
