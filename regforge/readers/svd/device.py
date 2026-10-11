"""Reads the root ``<device>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import DEFAULT_ADDRESS_UNIT_BITS, DEFAULT_BUS_WIDTH, Device
from regforge.readers.svd.access import AccessParser
from regforge.readers.svd.cpu import CpuParser
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.peripheral import PeripheralParser
from regforge.readers.svd.primitives import child_int, child_text
from regforge.readers.svd.protection import ProtectionParser


class DeviceParser(ElementParser):
    """Reads the ``<device>`` root as a :class:`~regforge.ir.Device`."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._access = AccessParser()
        self._cpu = CpuParser()
        self._peripheral = PeripheralParser(context)
        self._protection = ProtectionParser()

    def parse(self, root: ET.Element) -> Device:
        """The device ``root`` describes.

        Register-property defaults are stored raw at each level; run
        :func:`regforge.resolve.resolve_defaults` to fill them in.
        """
        cpu_element = root.find("cpu")
        vendor_ext = root.find("vendorExtensions")
        return Device(
            name=child_text(root, "name") or "device",
            description=child_text(root, "description"),
            vendor=child_text(root, "vendor"),
            series=child_text(root, "series"),
            version=child_text(root, "version"),
            license_text=child_text(root, "licenseText"),
            header_prefix=child_text(root, "headerDefinitionsPrefix"),
            # Preserve the vendor-extension subtree verbatim; never interpret it.
            vendor_extensions_xml=(
                ET.tostring(vendor_ext, encoding="unicode").strip()
                if vendor_ext is not None
                else None
            ),
            cpu=self._cpu.parse(cpu_element) if cpu_element is not None else None,
            address_unit_bits=child_int(root, "addressUnitBits", DEFAULT_ADDRESS_UNIT_BITS),
            bus_width=child_int(root, "width", DEFAULT_BUS_WIDTH),
            default_size=child_int(root, "size"),
            default_access=self._access.parse(root),
            default_reset_value=child_int(root, "resetValue"),
            default_reset_mask=child_int(root, "resetMask"),
            default_protection=self._protection.parse(root),
            peripherals=[
                self._peripheral.parse(p) for p in root.findall("./peripherals/peripheral")
            ],
        )
